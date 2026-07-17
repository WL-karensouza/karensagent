"""
实验 7：iFind 双格式兼容性验证 (H8.2)

测试统一解析器能否同时正确处理:
- stock server 返回的 data.answer (markdown 表格)
- news server 返回的 data.data (JSON 数组字符串)

方法：针对 stock 和 news 工具分别请求，
用统一解析器提取结构化数据，验证两者都不丢字段。
"""
import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Any

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

env_path = BACKEND_DIR / ".env"
if env_path.exists():
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            if key and value:
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))

from ifind_call import call

STOCK = {"code": "688981.SH", "name": "中芯国际"}

OUTPUT_DIR = Path(__file__).parent / "probe_results"
OUTPUT_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════
# 统一解析器 v1 — 自动识别格式并提取结构化数据
# ═══════════════════════════════════════════

def extract_raw_text(mcp_result: dict) -> dict:
    """
    从 MCP 返回中提取原始文本，同时标注数据格式类型。

    返回: {"type": "markdown"|"json_array"|"json_object"|"empty", "text": str}
    """
    try:
        content = mcp_result.get("data", {}).get("result", {}).get("content", [])
        for c in content:
            text = c.get("text", "")
            if not text:
                continue
            inner = json.loads(text)
            data_obj = inner.get("data", {})

            # 路径 1: data.data (news server 格式 — JSON 数组字符串)
            raw = data_obj.get("data", "")
            if raw:
                return {"type": "json_array", "text": raw}

            # 路径 2: data.answer (stock server 格式 — markdown 表格)
            raw = data_obj.get("answer", "")
            if raw:
                return {"type": "markdown", "text": raw}

            # 路径 3: data.result (部分工具返回)
            raw = data_obj.get("result", "")
            if raw:
                return {"type": "markdown", "text": raw}
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        pass
    return {"type": "empty", "text": ""}


def parse_markdown_to_records(answer_text: str) -> list[dict]:
    """
    将 markdown 表格解析为 dict 列表。
    输入:
        | 指标 | 数值 | 单位 |
        |------|------|------|
        | PE   | 25.3 | 倍   |
    输出:
        [{"指标": "PE", "数值": "25.3", "单位": "倍"}, ...]
    """
    if not answer_text:
        return []

    lines = answer_text.strip().split("\n")
    headers = []
    records = []

    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue

        parts = [p.strip() for p in line.split("|")[1:-1]]

        # 跳过分隔行
        if all(p.replace("-", "").replace(":", "").strip() == "" for p in parts):
            continue

        if not headers:
            headers = [p for p in parts]
        else:
            record = {}
            for i, val in enumerate(parts):
                if i < len(headers):
                    record[headers[i]] = val
            if record:
                records.append(record)

    return records


def parse_json_array_to_records(text: str) -> list[dict]:
    """将 JSON 数组字符串解析为 dict 列表"""
    if not text:
        return []
    try:
        items = json.loads(text)
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        elif isinstance(items, dict):
            return [items]
    except json.JSONDecodeError:
        pass
    return []


def unified_parse(mcp_result: dict) -> dict:
    """
    统一解析器：自动识别 iFind 返回格式 → 提取结构化记录。

    返回:
        {
            "ok": bool,
            "format": "markdown" | "json_array" | "json_object" | "empty",
            "record_count": int,
            "records": list[dict],
            "field_names": list[str],  # 去重后的字段名
        }
    """
    raw = extract_raw_text(mcp_result)

    if raw["type"] == "empty":
        return {"ok": False, "format": "empty", "record_count": 0, "records": [], "field_names": []}

    if raw["type"] == "json_array":
        records = parse_json_array_to_records(raw["text"])
    else:  # markdown
        records = parse_markdown_to_records(raw["text"])

    field_names = []
    seen = set()
    for r in records:
        for k in r:
            if k not in seen:
                seen.add(k)
                field_names.append(k)

    return {
        "ok": len(records) > 0,
        "format": raw["type"],
        "record_count": len(records),
        "records": records,
        "field_names": field_names,
    }


# ═══════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════

TEST_CASES = [
    # Stock server — 应返回 markdown 格式
    {
        "id": "stock_market",
        "server": "stock",
        "tool": "get_stock_info",
        "params": {"query": f"{STOCK['code']} 收盘价 涨跌幅 PE 换手率 MACD"},
        "expected_format": "markdown",
    },
    {
        "id": "stock_financials",
        "server": "stock",
        "tool": "get_stock_financials",
        "params": {"query": f"{STOCK['code']} ROE ROA 净利润增速 营收增速"},
        "expected_format": "markdown",
    },
    {
        "id": "stock_risk",
        "server": "stock",
        "tool": "get_risk_indicators",
        "params": {"query": f"{STOCK['code']} 贝塔 波动率 夏普比率 最大回撤"},
        "expected_format": "markdown",
    },
    {
        "id": "stock_esg",
        "server": "stock",
        "tool": "get_esg_data",
        "params": {"query": f"{STOCK['code']} ESG评级"},
        "expected_format": "markdown",
    },
    {
        "id": "stock_events",
        "server": "stock",
        "tool": "get_stock_events",
        "params": {"query": f"{STOCK['code']} 近期重大事件"},
        "expected_format": "markdown",
    },
    # News server — 应返回 json_array 格式
    {
        "id": "news_search",
        "server": "news",
        "tool": "search_news",
        "params": {"query": f"{STOCK['name']} 半导体芯片", "time_start": "2026-06-01", "time_end": "2026-07-10", "size": 5},
        "expected_format": "json_array",
    },
    {
        "id": "news_notice",
        "server": "news",
        "tool": "search_notice",
        "params": {"query": f"{STOCK['code']} 公告", "time_start": "2026-04-01", "time_end": "2026-07-10", "size": 5},
        "expected_format": "json_array",
    },
]


def main():
    print("=" * 60)
    print("实验 7：iFind 双格式兼容性验证")
    print(f"时间: {datetime.now().isoformat()}")
    print(f"目标: {STOCK['name']} ({STOCK['code']})")
    print(f"用例: {len(TEST_CASES)} 个")
    print("=" * 60)

    results = []
    passed = 0
    failed = 0

    for tc in TEST_CASES:
        print(f"\n  [{tc['id']}] {tc['server']}/{tc['tool']}...", end=" ")

        try:
            mcp_result = call(tc["server"], tc["tool"], tc["params"])
        except Exception as e:
            print(f"❌ 调用异常: {e}")
            failed += 1
            results.append({**tc, "ok": False, "error": str(e)})
            continue

        if not mcp_result["ok"]:
            print(f"❌ API 错误: {mcp_result.get('error', 'unknown')}")
            failed += 1
            results.append({**tc, "ok": False, "error": mcp_result.get("error")})
            continue

        parsed = unified_parse(mcp_result)

        # 验证
        format_ok = parsed["format"] == tc["expected_format"]
        has_records = parsed["record_count"] > 0

        if format_ok and has_records:
            print(f"✅ format={parsed['format']}, {parsed['record_count']} 条记录, {len(parsed['field_names'])} 个字段")
            print(f"     字段: {parsed['field_names'][:12]}{'...' if len(parsed['field_names']) > 12 else ''}")
            passed += 1
            results.append({**tc, "ok": True, **{k: v for k, v in parsed.items() if k != "records"}})
        elif not has_records:
            print(f"⚠️ format={parsed['format']}, 但无有效记录")
            failed += 1
            results.append({**tc, "ok": False, "reason": "no_records", **parsed})
        else:
            print(f"❌ 格式不匹配: 期望={tc['expected_format']}, 实际={parsed['format']}")
            failed += 1
            results.append({**tc, "ok": False, "reason": "format_mismatch", **parsed})

    # ── 汇总 ──
    print("\n" + "=" * 60)
    print("📋 汇总")
    print("=" * 60)

    total = passed + failed
    stock_tests = [r for r in results if r["server"] == "stock"]
    news_tests = [r for r in results if r["server"] == "news"]

    stock_ok = sum(1 for r in stock_tests if r["ok"])
    news_ok = sum(1 for r in news_tests if r["ok"])

    print(f"  Stock (markdown): {stock_ok}/{len(stock_tests)} 通过")
    print(f"  News (json_array): {news_ok}/{len(news_tests)} 通过")
    print(f"  总通过: {passed}/{total}")

    # ── 保存 ──
    output_path = OUTPUT_DIR / f"format_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    # 去掉 records（太大）
    save_results = []
    for r in results:
        r_copy = {k: v for k, v in r.items() if k != "records"}
        save_results.append(r_copy)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(save_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 结果已保存: {output_path}")

    # ── 判定 ──
    if passed == total:
        print("\n✅ 实验 7 通过！统一解析器兼容 stock(data.answer) + news(data.data) 两种格式")
        return 0
    else:
        print(f"\n❌ 实验 7 失败：{failed} 个用例未通过")
        return 1


if __name__ == "__main__":
    sys.exit(main())
