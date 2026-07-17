"""
探查：get_stock_performance 不写/极简 query 的默认行为
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

STOCKS = ["600519", "688981"]

TESTS = [
    # 空 query —— 会不会返回默认全套？
    ("空query", lambda s: ""),
    # 只写代码
    ("仅代码", lambda s: s),
    # 当前 query（待对比）
    ("当前query", lambda s: f"{s} 近一年涨跌幅 今年以来涨跌幅 相对大盘超额收益 年化收益率"),
    # 极简收盘价 —— 看默认行为
    ("仅收盘价", lambda s: f"{s} 收盘价"),
]


def extract_answer(result):
    try:
        content = result.get("data", {}).get("result", {}).get("content", [])
        for c in content:
            text = c.get("text", "")
            if not text:
                continue
            inner = json.loads(text)
            # 检查是否有多段 answer（多表）
            answers = []
            data_obj = inner.get("data", {})
            ans = data_obj.get("answer", "")
            if ans:
                answers.append(ans)
            # 也检查 result 字段
            res = data_obj.get("result", "")
            if res and res != ans:
                answers.append(res)
            return answers if answers else [ans]
    except Exception:
        pass
    return []


def parse_one_table(raw_text):
    headers, records = [], []
    for line in raw_text.strip().split("\n"):
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
    return headers, records


for stock in STOCKS:
    print(f"\n{'#'*60}")
    print(f"# STOCK: {stock}")
    print(f"{'#'*60}")

    for label, fn in TESTS:
        query = fn(stock)
        print(f"\n{'='*60}")
        print(f"[{label}] query={repr(query)}")
        print(f"{'='*60}")

        result = call("stock", "get_stock_performance", {"query": query})
        if not result["ok"]:
            print(f"  [FAIL] {result.get('error', 'unknown')}")
            continue

        answers = extract_answer(result)
        print(f"  answer 段数: {len(answers)}")

        for ai, raw in enumerate(answers):
            headers, records = parse_one_table(raw)
            print(f"\n  --- 第{ai+1}段 --- {len(records)} rows, {len(headers)} cols")
            print(f"  headers: {headers}")
            if records:
                print(f"  row[0]:")
                for k, v in records[0].items():
                    print(f"      {k}: {v}")
                if len(records) > 1:
                    print(f"  row[-1]:")
                    for k, v in records[-1].items():
                        print(f"      {k}: {v}")

print("\n[DONE]")
