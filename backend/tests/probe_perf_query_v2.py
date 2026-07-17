"""
Round 2: get_stock_performance 复合 query 探查
验证点：
  A) 日频+区间+年化+融资融券 能否一次查询全部返回
  B) 多关键词组合时字段会不会丢失
  C) 对比 600519(主板) vs 688981(科创板) 字段一致性
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


def extract_answer(result):
    try:
        content = result.get("data", {}).get("result", {}).get("content", [])
        for c in content:
            text = c.get("text", "")
            if text:
                inner = json.loads(text)
                return inner.get("data", {}).get("answer", "") or inner.get("data", {}).get("result", "")
    except Exception:
        pass
    return ""


def parse_table(raw_text):
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


# ====== 复合 query 矩阵 ======
STOCKS = ["600519", "688981"]
QUERIES = [
    # A: 行情+区间+相对收益 全组合
    ("行情+区间+相对", lambda s: f"{s} 收盘价 涨跌幅 近一年涨跌幅 今年以来涨跌幅 近一月涨跌幅 相对大盘涨跌幅 年化收益率 年化波动率"),
    # B: A + 融资融券
    ("行情+区间+相对+融资", lambda s: f"{s} 收盘价 涨跌幅 近一年涨跌幅 今年以来涨跌幅 近一月涨跌幅 相对大盘涨跌幅 年化收益率 年化波动率 融资余额 融券余额"),
    # C: 最精简版（用最少关键词触发最多字段）
    ("精简版", lambda s: f"{s} 收盘价 涨跌幅 近一年涨跌幅 今年以来涨跌幅 近一月涨跌幅"),
    # D: 极简（看能否"自动"带上所有字段）
    ("极简", lambda s: f"{s} 收盘价 涨跌幅"),
    # E: 区间涨跌幅全系列
    ("区间全系列", lambda s: f"{s} 近一周涨跌幅 近一月涨跌幅 近一季度涨跌幅 近半年涨跌幅 近一年涨跌幅 今年以来涨跌幅"),
    # F: 年化指标探测更多参数
    ("年化探测", lambda s: f"{s} 年化收益率 年化波动率 年化夏普比率 最大回撤 相对大盘涨跌幅"),
]


def probe(stock, label, query):
    print(f"\n{'='*60}")
    print(f"[{label}] stock={stock}")
    print(f"query: {query}")

    result = call("stock", "get_stock_performance", {"query": query})
    if not result["ok"]:
        print(f"  [FAIL] API error: {result.get('error', 'unknown')}")
        return {"ok": False, "error": result.get("error")}

    raw = extract_answer(result)
    if not raw:
        print("  [EMPTY] no answer")
        return {"ok": True, "records": [], "headers": []}

    headers, records = parse_table(raw)
    print(f"  [OK] {len(records)} rows, {len(headers)} cols:")
    for h in headers:
        print(f"    - {h}")
    if records:
        print(f"  row[0]:")
        for k, v in records[0].items():
            print(f"    {k} = {v}")
    if len(records) > 1:
        print(f"  row[-1]:")
        for k, v in records[-1].items():
            print(f"    {k} = {v}")

    return {"ok": True, "headers": headers, "record_count": len(records),
            "records": records[:2] + records[-2:] if len(records) > 4 else records}


def main():
    print("=" * 60)
    print(f"Round 2: get_stock_performance composite query")
    print(f"stocks: {STOCKS}")
    print(f"time: {datetime.now().isoformat()}")
    print("=" * 60)

    all_results = {}
    for stock in STOCKS:
        all_results[stock] = {}
        print(f"\n{'#'*60}")
        print(f"## STOCK: {stock}")
        print(f"{'#'*60}")
        for label, query_fn in QUERIES:
            query = query_fn(stock)
            r = probe(stock, label, query)
            all_results[stock][label] = r

    # ====== 汇总 ======
    print("\n\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for stock in STOCKS:
        print(f"\n--- {stock} ---")
        for label in all_results[stock]:
            r = all_results[stock][label]
            if r.get("ok") and r.get("record_count", 0) > 0:
                h = [x.replace('\n','') for x in r.get("headers", [])]
                print(f"  [OK] {label}: {r['record_count']} rows, cols={h}")
            elif r.get("ok"):
                print(f"  [EMPTY] {label}")
            else:
                print(f"  [FAIL] {label}")

    # 保存
    import glob as gl
    output_dir = Path(__file__).parent / "probe_results"
    output_dir.mkdir(exist_ok=True)
    out = output_dir / f"perf_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[SAVED] {out}")


if __name__ == "__main__":
    main()
