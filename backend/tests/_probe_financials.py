"""验证 get_stock_financials merge + to_prompt_context 效果"""
import os, sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env_path = BACKEND_DIR / ".env"
with open(env_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("#") or "=" not in line: continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

from stock_agent.ifind_client import IfindClient
from stock_agent.fetchers.financials.fetcher import fetch_financials, _merge_records

client = IfindClient()

for code in ["600398", "688221"]:
    print(f"\n{'='*70}")
    print(f"📌 {code}")
    print(f"{'='*70}")

    # 原始返回
    result = client.call_and_parse("stock", "get_stock_financials", {
        "query": ("{code} 净资产收益率ROE(TTM)、总资产净利率ROA(TTM)、"
                  "销售毛利率(TTM)、销售净利率(TTM)、"
                  "归属母公司股东的净利润同比增长率、营业总收入同比增长率、"
                  "资产负债率、流动比率、速动比率、"
                  "经营活动产生的现金流量净额(TTM)、每股企业自由现金流量、"
                  "基本每股收益、每股净资产、股息率").format(code=code)
    })
    print(f"原始记录数: {result['record_count']}")

    # merge
    merged = _merge_records(result["records"])
    print(f"merge 后记录数: {len(merged)}")
    r = merged[0]
    filled = {k: v for k, v in r.items()
              if v and v.strip() and k not in ("证券代码","证券简称","日期")}
    print(f"merge 后有效字段: {len(filled)}")
    for k, v in filled.items():
        print(f"  ✅ {k}: {v}")

    # fetch_financials 完整流程
    data = fetch_financials(client, code)
    print(f"\nfetch_financials → records={data.record_count} shareholders={data.shareholder_count}")
    print("\nto_prompt_context:")
    print(data.to_prompt_context()[:1200])
