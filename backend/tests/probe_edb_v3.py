"""
Round 3: 两次独立调用验证 — 核心宏观 + 行业专项分开查
"""
import json, os, sys
from pathlib import Path
from datetime import datetime

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

# 两次独立调用方案
SCENARIOS = [
    # (场景名, 调用1（核心宏观）, 调用2（行业专项，None=不调）)
    ("默认(无行业)",  "中国PMI M2增速 CPI",             None),
    ("半导体行业",    "中国PMI M2增速 CPI",             "半导体行业景气度"),
    ("白酒行业",      "中国PMI M2增速 CPI",             "白酒行业景气度"),
    # 对比：直接合并（验证分离的必要性）
    ("对比-半导体合并", "半导体行业景气度 中国PMI M2增速", None),
    ("对比-白酒合并",   "白酒行业景气度 中国PMI M2增速",   None),
]


def probe(query):
    result = call("edb", "get_edb_data", {"query": query})
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
        return {"ok": True, "record_count": 0, "headers": [], "rows": 0, "note": "empty"}

    lines = raw_text.strip().split("\n")
    headers, rows = [], []
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
                rows.append(rec)

    # 空值检测
    empty_cols = []
    for h in headers:
        if any(not r.get(h) for r in rows):
            empty_cols.append(h)

    return {
        "ok": True, "headers": headers, "row_count": len(rows),
        "first": rows[0] if rows else None, "last": rows[-1] if rows else None,
        "empty_cols": empty_cols,
    }


def main():
    print("Round 3: 两次独立调用验证")
    print("=" * 60)

    for label, query1, query2 in SCENARIOS:
        print(f"\n{'─'*50}")
        print(f"  场景: {label}")

        # 调用1
        r1 = probe(query1)
        if r1["ok"]:
            empty_flag = f" (空值列:{r1['empty_cols']})" if r1["empty_cols"] else ""
            print(f"  [调用1] '{query1}'")
            print(f"    → {r1['row_count']}行, cols={r1['headers']}{empty_flag}")
            if r1["first"]:
                print(f"    首: {json.dumps(r1['first'], ensure_ascii=False)}")
                print(f"    尾: {json.dumps(r1['last'], ensure_ascii=False)}")
        else:
            print(f"  [调用1] FAIL: {r1.get('error')}")

        # 调用2
        if query2:
            r2 = probe(query2)
            if r2["ok"]:
                empty_flag = f" (空值列:{r2['empty_cols']})" if r2["empty_cols"] else ""
                print(f"  [调用2] '{query2}'")
                print(f"    → {r2['row_count']}行, cols={r2['headers']}{empty_flag}")
                if r2["first"]:
                    print(f"    首: {json.dumps(r2['first'], ensure_ascii=False)}")
                    print(f"    尾: {json.dumps(r2['last'], ensure_ascii=False)}")
            else:
                print(f"  [调用2] FAIL: {r2.get('error')}")
        else:
            print(f"  [调用2] (跳过)")

    print(f"\n{'='*60}")
    print("[DONE]")


if __name__ == "__main__":
    main()
