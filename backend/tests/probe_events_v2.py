"""
Round 2: get_stock_events 组合关键词验证 — 测试多关键词行为模式
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

STOCK = "600519"  # 贵州茅台，事件最全

# 组合测试方案
COMBOS = {
    # 1. 当前基线（6个原关键词）
    "baseline_6": "分红 增发 回购 股权激励 重大资产重组 业绩预告",
    # 2. 仅数据丰富型（13个，每个都>=3行）
    "rich_only": "分红 回购 股权激励 业绩快报 股东减持 股东增持 限售解禁 股权质押 违规处罚 重大诉讼 关联交易 送转 现金分红",
    # 3. 全量组合（所有非错配关键词，~20个）
    "all_valid": "分红 增发 回购 股权激励 重大资产重组 业绩预告 业绩快报 配股 可转债 股东减持 股东增持 限售解禁 股权质押 大宗交易 违规处罚 监管函 重大诉讼 关联交易 停牌 投资者调研 送转 现金分红",
    # 4. 小组合 2个 — 同一类别（分红+送转+现金分红）
    "dividend_group": "分红 送转 现金分红",
    # 5. 小组合 2个 — 跨类别（回购+股权激励）
    "buyback_incentive": "回购 股权激励",
    # 6. 小组合 2个 — 跨类别（违规处罚+重大诉讼+监管函）
    "regulatory_group": "违规处罚 重大诉讼 监管函",
    # 7. 小组合 — 丰富+稀疏混合（增发+回购）
    "mixed_rich_sparse": "增发 回购",
}


def probe(query_label, query_str):
    full_query = f"{STOCK} {query_str}"
    result = call("stock", "get_stock_events", {"query": full_query})

    if not result["ok"]:
        return {
            "label": query_label,
            "query": query_str,
            "ok": False,
            "error": str(result.get("error", ""))[:200],
        }

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
        return {
            "label": query_label,
            "query": query_str,
            "ok": True,
            "record_count": 0,
            "headers": [],
            "raw": "",
            "note": "empty",
        }

    # 解析 markdown 表格
    lines = raw_text.strip().split("\n")
    all_headers = []
    all_records = []
    current_headers = []

    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if all(p.replace("-", "").replace(":", "").strip() == "" for p in parts):
            continue
        if not current_headers:
            current_headers = list(parts)
            all_headers.append(current_headers)
        else:
            rec = {}
            for i, v in enumerate(parts):
                if i < len(current_headers):
                    rec[current_headers[i]] = v
            if rec:
                all_records.append(rec)

    # 检测是否有多张表（通过寻找重复的表头模式）
    table_count = 1
    if len(all_headers) > 1:
        table_count = len(all_headers)

    return {
        "label": query_label,
        "query": query_str,
        "ok": True,
        "record_count": len(all_records),
        "table_count": table_count,
        "headers_sets": all_headers,
        "headers": all_headers[0] if all_headers else [],
        "records": all_records[:5],
        "keyword_count": len(query_str.split()),
    }


def main():
    print("Round 2: get_stock_events 组合关键词验证")
    print("=" * 60)
    print(f"测试股票: {STOCK}")
    print(f"测试组合: {len(COMBOS)} 个\n")

    results = {}
    for label, query_str in COMBOS.items():
        r = probe(label, query_str)
        results[label] = r
        kw_count = len(query_str.split())
        if r["ok"] and r["record_count"] > 0:
            print(f"[{label}] kw={kw_count} rows={r['record_count']} "
                  f"tables={r['table_count']} headers={r['headers'][:8]}")
        elif r["ok"]:
            print(f"[{label}] kw={kw_count} EMPTY")
        else:
            print(f"[{label}] kw={kw_count} FAIL: {r.get('error','')[:80]}")

    # ── 汇总分析 ──
    print(f"\n{'='*60}")
    print("汇总分析")
    print("=" * 60)

    baseline = results.get("baseline_6", {})
    baseline_headers = set(baseline.get("headers", []))
    baseline_rows = baseline.get("record_count", 0)

    print(f"\nBaseline (6kw): {baseline_rows}行, headers={baseline.get('headers', [])}")

    for label in COMBOS:
        if label == "baseline_6":
            continue
        r = results.get(label, {})
        r_headers = set(r.get("headers", []))
        new_in_r = r_headers - baseline_headers
        lost_from_baseline = baseline_headers - r_headers
        print(f"\n[{label}] ({r.get('keyword_count',0)}kw): "
              f"{r.get('record_count',0)}行, {r.get('table_count',0)}表")
        print(f"  headers={r.get('headers', [])}")
        if new_in_r:
            print(f"  NEW vs baseline: {new_in_r}")
        if lost_from_baseline:
            print(f"  LOST vs baseline: {lost_from_baseline}")

    # 保存
    out_dir = Path(__file__).parent / "probe_results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"events_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[SAVED] {out}")


if __name__ == "__main__":
    main()
