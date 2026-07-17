"""临时探针：测试优化后的 get_stock_summary query"""
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

from stock_agent.ifind_client import IfindClient, extract_raw_text

client = IfindClient()

Q = "{stock_code} 公司全称、主营业务、所属行业、总市值、流通市值、PE、PB、PS、PCF、首发价格、上市首日涨跌幅"

for code in ["600398", "688221"]:
    query = Q.format(stock_code=code)
    print("=" * 70)
    print(f"📌 {code}: {query}")
    print("=" * 70)
    raw = client._call_raw("stock", "get_stock_summary", {"query": query})
    info = extract_raw_text(raw)
    print(info["text"] + "\n")
