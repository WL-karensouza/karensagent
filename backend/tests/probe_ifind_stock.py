"""
实验 1：iFind Stock 数据完整性探查 (H1.1)

验证 5 个 stock server 工具能否返回有实际内容的数据。
测试标的：688981 中芯国际 + 002371 北方华创（半导体行业）
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# 确保 backend 目录在 sys.path 中
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# 加载 .env（在 import ifind_call 之前）
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

# ── 配置 ──
STOCKS = [
    {"code": "688981.SH", "name": "中芯国际"},
    {"code": "002371.SZ", "name": "北方华创"},
]

TOOLS = [
    {
        "name": "get_stock_info",
        "desc": "行情+技术指标",
        "query_tpl": "{code} 收盘价、涨跌幅、换手率、MACD、RSI、MA5、MA10、量比",
    },
    {
        "name": "get_stock_financials",
        "desc": "财务数据",
        "query_tpl": "{code} 最新财报的ROE、ROA、净利润增速、营收增速、毛利率、净利率、资产负债率、EPS",
    },
    {
        "name": "get_risk_indicators",
        "desc": "风险定量指标",
        "query_tpl": "{code} 近一年夏普比率、最大回撤、波动率、贝塔",
    },
    {
        "name": "get_esg_data",
        "desc": "ESG评级",
        "query_tpl": "{code} ESG评级",
    },
    {
        "name": "get_stock_events",
        "desc": "重大事件",
        "query_tpl": "{code} 近期重大事件",
    },
]

OUTPUT_DIR = Path(__file__).parent / "probe_results"
OUTPUT_DIR.mkdir(exist_ok=True)


def extract_answer(result):
    """从 iFind 返回的嵌套 JSON 中提取 answer 文本"""
    try:
        content = result.get("data", {}).get("result", {}).get("content", [])
        for c in content:
            text = c.get("text", "")
            if text:
                inner = json.loads(text)
                answer = inner.get("data", {}).get("answer", "")
                if answer:
                    return answer
                # search_stocks 等工具的 data.result 是字符串
                result_str = inner.get("data", {}).get("result", "")
                if result_str:
                    return result_str
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return ""


def count_table_fields(answer_text):
    """统计 markdown 表格中的有效数据单元数（行数 × 列数）"""
    lines = answer_text.strip().split("\n")
    table_rows = 0
    col_count = 0
    in_table = False

    for line in lines:
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if all(p.replace("-", "").replace(":", "").strip() == "" for p in parts):
                # 分隔行，跳过
                continue
            table_rows += 1
            if col_count == 0:
                col_count = len(parts)
            if not in_table:
                in_table = True
        else:
            if in_table:
                break  # 表格结束

    return table_rows * col_count if table_rows > 0 and col_count > 0 else 0


def count_json_fields(answer_text):
    """统计 answer 中 JSON 代码块的有效字段（指标参数）"""
    import re
    matches = re.findall(r"```json\s*\n(.*?)\n```", answer_text, re.DOTALL)
    total = 0
    for m in matches:
        try:
            data = json.loads(m)
            # 统计所有 key 的数量（递归）
            def _count_keys(obj):
                if isinstance(obj, dict):
                    return len(obj) + sum(_count_keys(v) for v in obj.values())
                elif isinstance(obj, list):
                    return sum(_count_keys(v) for v in obj)
                return 0
            total += _count_keys(data)
        except json.JSONDecodeError:
            pass
    return total


def count_total_fields(answer_text):
    """综合统计：表格单元 + JSON 参数字段"""
    if not answer_text:
        return 0
    table_fields = count_table_fields(answer_text)
    json_fields = count_json_fields(answer_text)
    return table_fields + json_fields


def probe_stock(stock, tool):
    """探查单只股票 + 单个工具"""
    query = tool["query_tpl"].format(name=stock["name"], code=stock["code"])
    print(f"  [{tool['desc']}] query: {query[:80]}...")

    try:
        result = call("stock", tool["name"], {"query": query})
    except Exception as e:
        print(f"    ❌ 异常: {e}")
        return {"ok": False, "error": str(e), "query": query}

    if not result["ok"]:
        print(f"    ❌ API 错误: {result.get('error', 'unknown')}")
        return {"ok": False, "error": result.get("error"), "query": query}

    answer = extract_answer(result)
    fields = count_total_fields(answer)

    if fields > 0:
        print(f"    ✅ 返回数据，有效字段数: {fields} (表格+指标参数)")
        # 打印前200字符预览
        preview = answer[:200].replace("\n", "\\n")
        print(f"    预览: {preview}...")
    else:
        print(f"    ⚠️ answer 为空或无表格数据")

    return {"ok": True, "fields": fields, "answer": answer, "query": query}


def main():
    print("=" * 60)
    print("实验 1：iFind Stock 数据完整性探查")
    print(f"时间: {datetime.now().isoformat()}")
    print(f"目标: {len(STOCKS)} 只股票 × {len(TOOLS)} 个工具")
    print("=" * 60)

    all_results = {}
    passed = 0
    failed = 0

    for stock in STOCKS:
        print(f"\n📊 {stock['name']} ({stock['code']})")
        stock_results = {}

        for tool in TOOLS:
            r = probe_stock(stock, tool)
            stock_results[tool["name"]] = r

            if r["ok"] and r["fields"] >= 5:
                passed += 1
            else:
                failed += 1

        all_results[stock["code"]] = stock_results

    # ── 汇总 ──
    total = passed + failed
    print("\n" + "=" * 60)
    print(f"📋 汇总: {passed}/{total} 通过")
    print("=" * 60)

    for code, stock_results in all_results.items():
        name = next(s["name"] for s in STOCKS if s["code"] == code)
        print(f"\n  {name} ({code}):")
        for tool_name, r in stock_results.items():
            tool_desc = next(t["desc"] for t in TOOLS if t["name"] == tool_name)
            if r["ok"] and r["fields"] >= 5:
                print(f"    ✅ {tool_desc}: {r['fields']} 有效字段")
            elif r["ok"]:
                print(f"    ⚠️ {tool_desc}: 仅 {r['fields']} 有效字段（不足 5）")
            else:
                print(f"    ❌ {tool_desc}: {r.get('error', 'unknown')}")

    # ── 保存完整结果 ──
    output_path = OUTPUT_DIR / f"stock_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 完整结果已保存: {output_path}")

    # ── 判定 ──
    required_tools = {t["name"] for t in TOOLS}
    for stock in STOCKS:
        stock_required = required_tools.copy()
        stock_results = all_results[stock["code"]]
        for tool_name in stock_required:
            r = stock_results.get(tool_name, {})
            if not r.get("ok") or r.get("fields", 0) < 5:
                print(f"\n❌ 实验 1 失败: {stock['name']} ({stock['code']}) {tool_name} 不满足成功标准")
                return 1

    print("\n✅ 实验 1 通过！5 个工具全部返回有效数据")
    return 0


if __name__ == "__main__":
    sys.exit(main())
