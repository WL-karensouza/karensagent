"""
Round 3: 两次独立调用的稳定性验证
Call 1: 日频序列模式 (多行)
Call 2: 区间汇总模式 (1行)
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

STOCKS = ["600519", "688981", "002371"]

# 待验证的 4 组候选 query
CANDIDATES = {
    # === 调用 1：日频序列（多行）===
    "日频-收盘+涨跌+融资": lambda s: f"{s} 收盘价 涨跌幅 融资余额 融券余额",
    "日频-收盘+涨跌": lambda s: f"{s} 收盘价 涨跌幅",
    "日频-收盘+涨跌+成交额": lambda s: f"{s} 收盘价 涨跌幅 成交额 成交量",
    "日频-收盘+涨跌+融资+成交": lambda s: f"{s} 收盘价 涨跌幅 融资余额 融券余额 成交额",
    # === 调用 2：区间汇总（1行）===
    "区间-年+今年+月": lambda s: f"{s} 近一年涨跌幅 今年以来涨跌幅 近一月涨跌幅",
    "区间-年+今年+月+大盘": lambda s: f"{s} 近一年涨跌幅 今年以来涨跌幅 近一月涨跌幅 相对大盘涨跌幅",
    "区间-全+年化": lambda s: f"{s} 近一年涨跌幅 今年以来涨跌幅 近一月涨跌幅 相对大盘涨跌幅 年化收益率 年化波动率",
    "区间-极简": lambda s: f"{s} 近一年涨跌幅 今年以来涨跌幅",
}


def probe(stock, label, query, call_type):
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
        return {"ok": True, "record_count": 0, "headers": [], "issue": "empty"}

    # 解析
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

    # 错位检测
    issues = []
    # 检查"日期"列是否出现非日期值
    if len(records) > 1:
        last = records[-1]
        for h in headers:
            if h in last:
                val = last[h]
                # 数字或百分号 value 出现在不该出现的位置
                if val and any(c in val for c in ".-%") and len(val) < 15:
                    # 看看其他行这一列是否都是日期
                    dates_in_col = [r.get(h, "") for r in records[:-1]]
                    if all(d and (d.isdigit() or "-" in d) for d in dates_in_col):
                        issues.append(f"col_shift: 末行 {h}={val}")

    return {
        "ok": True, "record_count": len(records), "headers": headers,
        "records": records, "issues": issues,
    }


def main():
    print("Round 3: 两次独立调用 query 验证")
    print("=" * 60)

    all_results = {}
    for stock in STOCKS:
        all_results[stock] = {}
        print(f"\n{'#'*60}")
        print(f"# {stock}")
        print(f"{'#'*60}")
        for label, fn in CANDIDATES.items():
            query = fn(stock)
            call_type = "日频" if "日频" in label else "区间"
            r = probe(stock, label, query, call_type)
            all_results[stock][label] = r

            if r.get("ok") and r.get("record_count", 0) > 0:
                issues_str = f" [WARN: {','.join(r['issues'])}]" if r.get("issues") else ""
                print(f"  [{label}]{issues_str} {r['record_count']}行 {len(r['headers'])}列")
            elif r.get("ok"):
                print(f"  [{label}] EMPTY")
            else:
                print(f"  [{label}] FAIL: {r.get('error')}")

    # 汇总：找出所有无错位的 query
    print(f"\n{'='*60}")
    print("汇总：无错位 query")
    print(f"{'='*60}")
    for stock in STOCKS:
        print(f"\n{stock}:")
        for label, r in all_results[stock].items():
            if r.get("ok") and r.get("record_count", 0) > 0:
                if not r.get("issues"):
                    print(f"  [CLEAN] {label}: {r['record_count']}行, cols={r['headers']}")

    # 保存
    out_dir = Path(__file__).parent / "probe_results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"perf_v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[SAVED] {out}")


if __name__ == "__main__":
    main()
