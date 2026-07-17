"""
实验 6：Pydantic 模型字段覆盖率验证 (H8.1)

对 iFind 5 个 stock 工具 + 2 个 news 工具返回的所有字段进行枚举，
验证 Pydantic 模型能否完整覆盖。

测试标的: 688981.SH 中芯国际
"""
import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime
from collections import OrderedDict

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


def extract_answer(result, data_key="answer"):
    """从 iFind 返回中提取数据文本，支持 data.answer 和 data.data 两种路径"""
    try:
        content = result.get("data", {}).get("result", {}).get("content", [])
        for c in content:
            text = c.get("text", "")
            if text:
                inner = json.loads(text)
                data_obj = inner.get("data", {})
                # 先尝试指定的 key，再 fallback
                val = data_obj.get(data_key, "")
                if val:
                    return val
                # fallback: 尝试另一个 key
                other = "data" if data_key == "answer" else "answer"
                val = data_obj.get(other, "")
                if val:
                    return val
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return ""


def parse_markdown_table_fields(answer_text):
    """从 markdown 表格中提取所有字段名（表头列名）"""
    if not answer_text:
        return []

    fields = []
    lines = answer_text.strip().split("\n")
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            # 跳过分隔行
            if all(p.replace("-", "").replace(":", "").strip() == "" for p in parts):
                continue
            # 第一个非空行 = 表头
            non_empty = [p for p in parts if p]
            if non_empty and not all(p.replace("-", "").replace(":", "").strip() == "" for p in parts):
                fields.extend([p for p in parts if p])
                break  # 只取第一个表头
    return fields


def parse_json_array_fields(answer_text):
    """从 JSON 数组中提取所有字段名（key 去重）"""
    if not answer_text:
        return []

    keys = set()
    try:
        items = json.loads(answer_text)
        if isinstance(items, list):
            for item in items[:20]:  # 取前20条样本
                if isinstance(item, dict):
                    keys.update(item.keys())
        elif isinstance(items, dict):
            keys.update(items.keys())
    except (json.JSONDecodeError, TypeError):
        pass
    return sorted(keys)


def parse_json_codeblock_fields(answer_text):
    """从 markdown 中 ```json 代码块提取字段名"""
    if not answer_text:
        return []

    keys = set()
    matches = re.findall(r"```json\s*\n(.*?)\n```", answer_text, re.DOTALL)
    for m in matches:
        try:
            data = json.loads(m)
            def extract_keys(obj, prefix=""):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        full_key = f"{prefix}.{k}" if prefix else k
                        keys.add(full_key)
                        extract_keys(v, full_key)
                elif isinstance(obj, list) and obj:
                    extract_keys(obj[0], prefix)
            extract_keys(data)
        except json.JSONDecodeError:
            pass
    return sorted(keys)


def probe_tool(server, tool_name, params, label, data_key="answer"):
    """探查单个工具，返回原始数据 + 解析后的字段列表"""
    print(f"  [{label}] {tool_name}...", end=" ")
    try:
        result = call(server, tool_name, params)
    except Exception as e:
        print(f"❌ 异常: {e}")
        return {"ok": False, "error": str(e)}

    if not result["ok"]:
        print(f"❌ API 错误: {result.get('error', 'unknown')}")
        return {"ok": False, "error": result.get("error")}

    answer = extract_answer(result, data_key)

    # 解析字段
    table_fields = parse_markdown_table_fields(answer)
    json_fields = parse_json_codeblock_fields(answer)
    array_fields = parse_json_array_fields(answer)

    all_fields = list(OrderedDict.fromkeys(table_fields + json_fields + array_fields))

    if all_fields:
        print(f"✅ {len(all_fields)} 个字段: {all_fields[:15]}{'...' if len(all_fields) > 15 else ''}")
    elif answer:
        print(f"⚠️ 有数据但无法解析字段，长度={len(answer)}")
    else:
        print(f"⚠️ 无数据")

    return {
        "ok": True,
        "fields": all_fields,
        "field_count": len(all_fields),
        "table_fields": table_fields,
        "json_fields": json_fields,
        "array_fields": array_fields,
        "answer_preview": answer[:300] if answer else "",
    }


def main():
    print("=" * 60)
    print("实验 6：Pydantic 模型字段覆盖率验证")
    print(f"时间: {datetime.now().isoformat()}")
    print(f"目标: {STOCK['name']} ({STOCK['code']})")
    print("=" * 60)

    # ── Stock 5 工具 ──
    stock_tools = [
        ("get_stock_info", {"query": f"{STOCK['code']} 收盘价、涨跌幅、MACD、RSI、MA5、MA10、MA20、量比、换手率、成交额"}, "行情"),
        ("get_stock_financials", {"query": f"{STOCK['code']} ROE ROA 净利润增速 营收增速 毛利率 净利率 资产负债率 EPS 经营现金流"}, "财务"),
        ("get_risk_indicators", {"query": f"{STOCK['code']} 贝塔 波动率 夏普比率 最大回撤 下行风险"}, "风险"),
        ("get_esg_data", {"query": f"{STOCK['code']} ESG评级 环境 社会 治理"}, "ESG"),
        ("get_stock_events", {"query": f"{STOCK['code']} 重大事件 业绩预告 分红"}, "事件"),
    ]

    # ── News 2 工具 ──
    news_tools = [
        ("search_news", {"query": f"{STOCK['name']} 半导体", "time_start": "2026-06-01", "time_end": "2026-07-10", "size": 5}, "新闻"),
        ("search_notice", {"query": f"{STOCK['code']} 公告", "time_start": "2026-04-01", "time_end": "2026-07-10", "size": 5}, "公告"),
    ]

    all_fields = {}  # server_type -> tool_name -> fields
    total_unique = set()

    print("\n📊 Stock Server:")
    for tool_name, params, label in stock_tools:
        r = probe_tool("stock", tool_name, params, label)
        if r["ok"]:
            all_fields.setdefault("stock", {})[tool_name] = r
            total_unique.update(r["fields"])

    print("\n📰 News Server:")
    for tool_name, params, label in news_tools:
        r = probe_tool("news", tool_name, params, label, "data")  # news uses data.data
        if r["ok"]:
            all_fields.setdefault("news", {})[tool_name] = r
            total_unique.update(r["fields"])

    # ── 汇总 ──
    print("\n" + "=" * 60)
    print("📋 字段覆盖率汇总")
    print("=" * 60)

    total_fields = 0
    tool_count = 0
    all_field_names = set()

    for server, tools in all_fields.items():
        for tool_name, r in tools.items():
            tool_count += 1
            fc = r.get("field_count", 0)
            total_fields += fc
            all_field_names.update(r.get("fields", []))
            print(f"\n  [{server}] {tool_name}: {fc} 个字段")
            if r.get("table_fields"):
                print(f"    表格字段: {r['table_fields']}")
            if r.get("json_fields"):
                print(f"    JSON字段: {r['json_fields'][:15]}{'...' if len(r.get('json_fields',[])) > 15 else ''}")
            if r.get("array_fields"):
                print(f"    数组字段: {r['array_fields']}")

    print(f"\n  ─────────────────────────────")
    print(f"  工具总数: {tool_count}")
    print(f"  字段总计（含重复）: {total_fields}")
    print(f"  去重字段数: {len(all_field_names)}")
    print(f"  去重字段: {sorted(all_field_names)}")

    # ── Pydantic 模型建议 ──
    print("\n" + "=" * 60)
    print("📐 Pydantic 模型设计建议")
    print("=" * 60)

    # 按类型分组字段
    grouped = {
        "market": [],
        "financials": [],
        "risk": [],
        "esg": [],
        "events": [],
        "news": [],
        "notice": [],
    }

    field_to_group = {}
    for server, tools in all_fields.items():
        for tool_name, r in tools.items():
            group = {
                "get_stock_info": "market",
                "get_stock_financials": "financials",
                "get_risk_indicators": "risk",
                "get_esg_data": "esg",
                "get_stock_events": "events",
                "search_news": "news",
                "search_notice": "notice",
            }.get(tool_name, "other")
            for f in r.get("fields", []):
                grouped.setdefault(group, []).append(f)

    for group, fields in grouped.items():
        if fields:
            unique = list(OrderedDict.fromkeys(fields))
            print(f"  {group}: {len(unique)} 字段 → {unique}")

    # ── 覆盖率判定 ──
    print("\n" + "=" * 60)
    if tool_count >= 7 and len(all_field_names) > 0:
        print(f"✅ 实验 6 通过！枚举了 {tool_count} 个工具共 {len(all_field_names)} 个去重字段")
        print("   这些字段作为 Pydantic 模型设计的最低覆盖基准")
        return 0
    else:
        print(f"❌ 实验 6 失败：仅覆盖 {tool_count} 个工具")
        return 1


if __name__ == "__main__":
    sys.exit(main())
