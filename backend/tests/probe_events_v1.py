"""
Round 1: get_stock_events 单关键词验证 — 确认每个事件关键词能否返回数据
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

# 3只大盘蓝筹股，事件覆盖率高
STOCKS = ["600519", "000858", "601318"]

# 候选事件关键词（16类 + 2个细粒度变体 = 22个）
KEYWORDS = [
    # ── 已在用（6个）──
    "分红",
    "增发",
    "回购",
    "股权激励",
    "重大资产重组",
    "业绩预告",
    # ── 再融资 ──
    "配股",
    "可转债",
    # ── 业绩披露 ──
    "业绩快报",
    # ── 股东行为 ──
    "股东减持",
    "股东增持",
    "限售解禁",
    # ── 融资/质押 ──
    "股权质押",
    # ── 交易 ──
    "大宗交易",
    # ── 监管 ──
    "违规处罚",
    "监管函",
    # ── 法律 ──
    "重大诉讼",
    # ── 经营 ──
    "重大合同",
    "对外担保",
    "关联交易",
    # ── 停复牌 ──
    "停牌",
    # ── 投资者关系 ──
    "投资者调研",
    # ── 细粒度变体 ──
    "送转",
    "现金分红",
]


def probe(stock_code, keyword):
    query = f"{stock_code} {keyword}"
    result = call("stock", "get_stock_events", {"query": query})

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
        if all(p.replace("-", "").replace(":", "").strip() == "" for p in parts):
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
        "ok": True,
        "record_count": len(records),
        "headers": headers,
        "records": records[:3],
    }


def main():
    print("Round 1: get_stock_events 单关键词验证")
    print("=" * 60)
    print(f"测试股票: {STOCKS}")
    print(f"测试关键词: {len(KEYWORDS)} 个\n")

    all_results = {}
    keyword_validity = {}

    for kw in KEYWORDS:
        keyword_validity[kw] = {}
        print(f"--- {kw} ---")
        for stock in STOCKS:
            r = probe(stock, kw)
            all_results[f"{kw}_{stock}"] = r
            if r["ok"] and r["record_count"] > 0:
                keyword_validity[kw][stock] = f"{r['record_count']}行 cols={r['headers'][:5]}"
                print(f"  [{stock}] OK {r['record_count']}行, headers={r['headers']}")
            elif r["ok"]:
                keyword_validity[kw][stock] = "空"
                print(f"  [{stock}] EMPTY")
            else:
                keyword_validity[kw][stock] = f"失败: {r.get('error','')[:60]}"
                print(f"  [{stock}] FAIL {r.get('error','')[:80]}")

    # ── 汇总 ──
    print(f"\n{'='*60}")
    print("汇总")
    print("=" * 60)

    always_works = []
    sometimes = []
    never = []

    for kw, stocks in keyword_validity.items():
        counts = [v for v in stocks.values() if "行" in str(v)]
        if len(counts) == len(STOCKS):
            always_works.append(kw)
        elif len(counts) > 0:
            sometimes.append(kw)
        else:
            never.append(kw)

    print(f"\n[ALL] 全有效 ({len(always_works)}): {always_works}")
    print(f"[SOME] 部分有效 ({len(sometimes)}): {sometimes}")
    print(f"[NONE] 全无效 ({len(never)}): {never}")

    print(f"\n详细:")
    for kw, stocks in keyword_validity.items():
        print(f"  {kw}: {stocks}")

    # 保存
    out_dir = Path(__file__).parent / "probe_results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"events_v1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(
            {"all": all_results, "summary": keyword_validity},
            f, ensure_ascii=False, indent=2, default=str,
        )
    print(f"\n[SAVED] {out}")


if __name__ == "__main__":
    main()
