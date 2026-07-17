"""
验证：最优 query 对 600905 和 300369 的表现
- 调用 1: 收盘价 涨跌幅 成交额 成交量
- 调用 2: 近一年涨跌幅 今年以来涨跌幅
"""
import json, os, sys
from pathlib import Path

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

STOCKS = ["600905", "300369"]

CALLS = [
    ("日频序列", lambda s: f"{s} 收盘价 涨跌幅 成交额 成交量"),
    ("区间汇总", lambda s: f"{s} 近一年涨跌幅 今年以来涨跌幅"),
]


def probe(stock, label, query):
    result = call("stock", "get_stock_performance", {"query": query})
    if not result["ok"]:
        return {"ok": False, "error": str(result.get("error", ""))[:200]}

    raw_text = ""
    try:
        content = result.get("data", {}).get("result", {}).get("content", [])
        for c in content:
            text = c.get("text", "")
            if text:
                inner = json.loads(text)
                raw_text = inner.get("data", {}).get("answer", "")
                break
    except Exception:
        pass

    if not raw_text:
        return {"ok": True, "record_count": 0, "headers": [], "records": []}

    lines = raw_text.strip().split("\n")
    headers, records = [], []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if all(p.replace("-","").replace(":","").strip()=="" for p in parts):
            continue
        if not headers:
            headers = list(parts)
        else:
            rec = {}
            for i, v in enumerate(parts):
                if i < len(headers):
                    rec[headers[i]] = v
            if rec:
                records.append(rec)

    # 检查末行错位
    issues = []
    if len(records) > 1:
        for h in headers:
            if h not in records[-1]:
                continue
            val = records[-1][h]
            has_digit_char = val and any(c in val for c in ".-%") if val else False
            if has_digit_char and len(val) < 15:
                dates = [r.get(h, "") for r in records[:-1]]
                if all(d and (d.isdigit() or "-" in d) for d in dates):
                    issues.append(f"col_shift:{h}={val}")

    return {"ok": True, "record_count": len(records), "headers": headers,
            "records": records, "issues": issues}


for stock in STOCKS:
    print(f"\n{'#'*50}")
    print(f"# {stock}")
    print(f"{'#'*50}")
    for label, fn in CALLS:
        query = fn(stock)
        r = probe(stock, label, query)
        print(f"\n  [{label}] query={query}")
        if not r.get("ok"):
            print(f"  [FAIL] {r.get('error')}")
            continue
        if r["record_count"] == 0:
            print("  [EMPTY]")
            continue
        flag = " <<<SHIFT!" if r["issues"] else ""
        print(f"  {r['record_count']}行 x {len(r['headers'])}列{flag}")
        for rec in r["records"]:
            print(f"  {json.dumps(rec, ensure_ascii=False)}")

print("\n[DONE]")
