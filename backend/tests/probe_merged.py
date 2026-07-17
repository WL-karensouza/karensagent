"""验证：5字段合并一次查询是否窜行"""
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

STOCKS = ["600519", "688981", "002371", "600905", "300369"]
QUERY_FN = lambda s: f"{s} 收盘价 涨跌幅 成交额 成交量 近一年涨跌幅"


def probe(stock):
    query = QUERY_FN(stock)
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
        return {"ok": True, "records": [], "headers": []}

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

    # 窜行检测
    issues = []
    if len(records) > 1:
        last = records[-1]
        for h in headers:
            val = last.get(h, "")
            if not val:
                continue
            is_probably_date = val.isdigit() or (len(val) == 8 and val[:4].isdigit())
            has_numeric_chars = any(c in val for c in ".-%")
            if has_numeric_chars and len(val) < 15:
                prev_vals = [r.get(h, "") for r in records[:-1]]
                if all(pv and (pv.isdigit() or "-" in pv) for pv in prev_vals if pv):
                    pass  # might be fine if all rows are numeric
                # 检查日期列是否被污染
                dates_in_col = [r.get(h, "") for r in records[:-1]]
                if all(d and d.isdigit() and len(d) == 8 for d in dates_in_col):
                    issues.append(f"日期列[{h}]末行={val}(疑似数字错位)")

    # 检查是否有非预期空值
    empty_cols = []
    for h in headers:
        vals = [r.get(h, "") for r in records]
        if any(v == "" or v is None for v in vals):
            empty_cols.append(h)

    return {"ok": True, "record_count": len(records), "headers": headers,
            "records": records, "issues": issues, "has_empty_cols": empty_cols}


for stock in STOCKS:
    r = probe(stock)
    print(f"\n{'='*6} {stock} {'='*6}")
    print(f"query: {QUERY_FN(stock)}")
    if not r.get("ok"):
        print(f"  [FAIL] {r.get('error')}")
        continue
    if r["record_count"] == 0:
        print("  [EMPTY]")
        continue

    issues = r["issues"]
    flag = f"  <<< 窜行: {issues}" if issues else "  [OK] 无窜行"
    empty_flag = f"  有空列: {r['has_empty_cols']}" if r["has_empty_cols"] else ""
    print(f"  {r['record_count']}行 x {len(r['headers'])}列{flag}{empty_flag}")
    for i, rec in enumerate(r["records"]):
        print(f"  [{i}] {json.dumps(rec, ensure_ascii=False)}")

print("\n[DONE]")
