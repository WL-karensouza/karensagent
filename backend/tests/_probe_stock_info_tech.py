"""
临时探针：测试 get_stock_info 多周期技术指标返回
目标：搞清楚 MA5/10/20/30/60、多周期涨跌幅、BOLL上中下能否在一次 query 中全部返回
"""
import os
import sys
import json
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env_path = BACKEND_DIR / ".env"
with open(env_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

from stock_agent.ifind_client import IfindClient, extract_raw_text

client = IfindClient()

# ── 测试1：当前 query，换 688221 ──
QUERY_1 = (
    "688221 最新收盘价、涨跌幅、5日涨跌幅、10日涨跌幅、20日涨跌幅、"
    "换手率、成交额、量比、MACD、RSI、MA5、MA10、MA20、MA60、"
    "KDJ、BOLL上轨、BOLL中轨、BOLL下轨"
)

# ── 测试2：尝试用中文"5日均线、10日均线、20日均线" ──
QUERY_2 = (
    "688221 最新收盘价、涨跌幅、5日涨跌幅、10日涨跌幅、20日涨跌幅、"
    "5日均线、10日均线、20日均线、60日均线、MACD、RSI、KDJ、换手率、成交额"
)


def run_probe(label, query):
    print("=" * 70)
    print(f"📌 {label}")
    print("=" * 70)
    print(f"\nQuery: {query}\n")

    result = client.call_and_parse("stock", "get_stock_info", {"query": query})
    print(f"ok: {result['ok']} | format: {result['format']} | records: {result['record_count']}")
    print(f"field_names ({len(result['field_names'])}): {result['field_names']}")

    for i, r in enumerate(result["records"]):
        print(f"\n[{i}]")
        for k, v in r.items():
            print(f"  {k}: {v}")

    print()


# 跑两个测试
run_probe("测试1: 688221 + 当前 query（简写 MA5/MA10/MA20/MA60）", QUERY_1)
run_probe("测试2: 688221 + 中文全称（5日均线/10日均线/20日均线/60日均线）", QUERY_2)

# ── 额外：看看 get_stock_info 工具的参数描述 ──
print("=" * 70)
print("📌 测试3: 获取 stock server 工具列表，看 get_stock_info 参数说明")
print("=" * 70)
from ifind_call import list_tools
tools_result = list_tools("stock")
if tools_result["ok"]:
    tools = tools_result["data"].get("result", {}).get("tools", [])
    for t in tools:
        if t["name"] == "get_stock_info":
            print(json.dumps(t, ensure_ascii=False, indent=2))
