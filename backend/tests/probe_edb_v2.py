"""
Round 2: 复合查询稳定性验证 — 多关键词合并是否会窜行/丢字段
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

# 复合 query 组合
COMPOSITE_QUERIES = [
    # 双指标
    ("中国PMI + 社会融资规模", "中国PMI 社会融资规模"),
    ("中国PMI + M2增速", "中国PMI M2增速"),
    ("社会融资规模 + M2增速", "社会融资规模 M2增速"),
    # 三指标（当前默认 query）
    ("三指标(当前默认)", "中国PMI 社会融资规模 M2增速"),
    # 行业+宏观（当前行业 query）
    ("半导体行业+PMI", "半导体行业景气度 中国PMI"),
    ("白酒行业+PMI", "白酒行业景气度 中国PMI"),
    # 混合压测
    ("中国PMI + M2 + 社融 + CPI", "中国PMI M2增速 社会融资规模 CPI"),
    ("中国PMI + M2 + 社融 + GDP", "中国PMI M2增速 社会融资规模 GDP增速"),
]


def probe(label, query):
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
        return {"ok": True, "record_count": 0, "headers": [], "records": [], "note": "empty"}

    # 解析所有表格（可能有多个独立表格块）
    lines = raw_text.strip().split("\n")
    tables = []  # [{headers, rows}]
    current_headers, current_rows = [], []
    in_table = False

    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            if in_table and current_headers:
                tables.append({"headers": list(current_headers), "rows": list(current_rows)})
            in_table = False
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if all(p.replace("-","").replace(":","").strip()=="" for p in parts):
            continue
        if not in_table:
            current_headers = list(parts)
            current_rows = []
            in_table = True
        else:
            rec = {}
            for i, v in enumerate(parts):
                if i < len(current_headers):
                    rec[current_headers[i]] = v
            if rec:
                current_rows.append(rec)
    if in_table and current_headers:
        tables.append({"headers": list(current_headers), "rows": list(current_rows)})

    total_rows = sum(len(t["rows"]) for t in tables)
    all_headers = [h for t in tables for h in t["headers"]]

    # 窜行检测：是否是多个独立表格拼接
    is_multi_table = len(tables) > 1
    issues = []

    if is_multi_table:
        # 多表格是正常的（不同指标不同频率），检查每个表结构是否完整
        for ti, t in enumerate(tables):
            if "日期" not in t["headers"]:
                issues.append(f"table[{ti}] 缺少日期列: {t['headers']}")
            # 检查每行是否都有日期
            for ri, row in enumerate(t["rows"]):
                date_val = row.get("日期", "")
                if not date_val:
                    issues.append(f"table[{ti}] row[{ri}] 日期为空")

    return {
        "ok": True, "table_count": len(tables), "total_rows": total_rows,
        "headers": all_headers, "tables": [
            {"headers": t["headers"], "row_count": len(t["rows"]), "first_row": t["rows"][0] if t["rows"] else None}
            for t in tables
        ],
        "issues": issues,
        "is_multi_table": is_multi_table,
    }


def main():
    print("Round 2: EDB 复合查询稳定性验证")
    print("=" * 60)

    results = {}
    for label, query in COMPOSITE_QUERIES:
        print(f"\n  [{label}] query='{query}'")
        r = probe(label, query)
        results[label] = r

        if not r["ok"]:
            print(f"    [FAIL] {r.get('error')}")
            continue
        if r["total_rows"] == 0:
            print(f"    [EMPTY]")
            continue

        flag = ""
        if r["issues"]:
            flag = f" <<< ISSUES: {r['issues']}"
        elif r["is_multi_table"]:
            flag = f" (独立表×{r['table_count']})"

        print(f"    {r['table_count']}表 {r['total_rows']}行, cols={r['headers']}{flag}")
        for ti, t in enumerate(r["tables"]):
            print(f"     表{ti}: {t['row_count']}行, {t['headers']}")
            if t["first_row"]:
                print(f"      首行: {json.dumps(t['first_row'], ensure_ascii=False)}")

    # 汇总
    print(f"\n{'='*60}")
    print("汇总")
    for label, r in results.items():
        if r["ok"] and r["total_rows"] > 0:
            status = "CLEAN" if not r["issues"] else f"ISSUES:{len(r['issues'])}"
            print(f"  [{status}] {label}: {r['table_count']}表 {r['total_rows']}行")

    # 保存
    out_dir = Path(__file__).parent / "probe_results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"edb_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[SAVED] {out}")


if __name__ == "__main__":
    main()
