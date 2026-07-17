"""
Round 1: 单关键词验证 — 确认每个 EDB 关键词能否独立返回数据
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

# 候选关键词列表（覆盖三类：中国宏观、行业、全球）
KEYWORDS = [
    # 中国宏观 — 已在用
    "中国PMI",
    "M2增速",
    "社会融资规模",
    # 中国宏观 — 未用过但常见
    "CPI",
    "GDP增速",
    "工业增加值",
    # 行业相关
    "半导体行业景气度",
    "白酒行业景气度",
    "行业景气度",
    # 全球宏观
    "美国GDP",
    "美联储利率",
]


def probe(keyword):
    result = call("edb", "get_edb_data", {"query": keyword})
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

    # 解析 markdown 表格
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

    return {
        "ok": True, "record_count": len(records), "headers": headers,
        "records": records[:3],  # 只保留前3行预览
    }


def main():
    print("Round 1: EDB 单关键词验证")
    print("=" * 60)

    results = {}
    for kw in KEYWORDS:
        r = probe(kw)
        results[kw] = r
        if r["ok"] and r["record_count"] > 0:
            print(f"  [OK] '{kw}' → {r['record_count']}行, cols={r['headers']}")
        elif r["ok"]:
            print(f"  [EMPTY] '{kw}'")
        else:
            print(f"  [FAIL] '{kw}': {r.get('error')}")

    # 汇总
    working = [kw for kw, r in results.items() if r["ok"] and r["record_count"] > 0]
    empty = [kw for kw, r in results.items() if r["ok"] and r["record_count"] == 0]
    failed = [kw for kw, r in results.items() if not r["ok"]]

    print(f"\n{'='*60}")
    print(f"汇总: {len(working)} 有效 / {len(empty)} 空 / {len(failed)} 失败")
    print(f"有效: {working}")
    print(f"空: {empty}")
    print(f"失败: {failed}")

    # 保存
    out_dir = Path(__file__).parent / "probe_results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"edb_v1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[SAVED] {out}")


if __name__ == "__main__":
    main()
