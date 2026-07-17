"""探查 search_stocks — 关键字 vs prompt（加延迟 + 手动解析响应格式）"""
import os, sys, json, time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env_path = BACKEND_DIR / ".env"
with open(env_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

from ifind_call import call


def _manual_parse(raw: dict) -> str | None:
    """手动解析 search_stocks 的特有响应格式：data.data 是 JSON 字符串套 answer"""
    try:
        content = raw.get("data", {}).get("result", {}).get("content", [])
        for c in content:
            text = c.get("text", "")
            if not text:
                continue
            # 检查是否是限流错误
            if "429" in text or "请求过于频繁" in text or "请稍后重试" in text:
                return None
            # 检查是否是 call failed
            if text.startswith("call failed"):
                return None
            inner = json.loads(text)
            # search_stocks 特有结构：inner.data 是字符串 "{\"answer\": \"...\"}"
            raw_data = inner.get("data", "")
            if isinstance(raw_data, str) and raw_data.strip():
                data_inner = json.loads(raw_data)
                answer = data_inner.get("answer", "")
                if answer:
                    return answer
            # 回退：inner.data 可能是 dict
            if isinstance(raw_data, dict):
                return raw_data.get("answer", "") or raw_data.get("data", "")
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return None


def _parse_md_table(md_text: str) -> list[dict]:
    """简易 markdown 表格解析"""
    if not md_text:
        return []
    lines = md_text.strip().split("\n")
    headers = []
    records = []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if all(p.replace("-", "").replace(":", "").strip() == "" for p in parts):
            continue
        if not headers:
            headers = [p for p in parts]
        else:
            rec = {}
            for i, val in enumerate(parts):
                if i < len(headers):
                    rec[headers[i]] = val
            if rec:
                records.append(rec)
    return records


def probe_one(label: str, query: str) -> dict | None:
    """单次探测，返回解析后的结果，含限流处理"""
    try:
        raw = call("stock", "search_stocks", {"query": query})
        answer = _manual_parse(raw)
        if answer is not None:
            records = _parse_md_table(answer)
            return {"label": label, "query": query, "records": records,
                    "answer_preview": answer[:300]}
        else:
            # 可能是限流，等一会重试
            time.sleep(3)
            raw = call("stock", "search_stocks", {"query": query})
            answer = _manual_parse(raw)
            if answer:
                records = _parse_md_table(answer)
                return {"label": label, "query": query, "records": records,
                        "answer_preview": answer[:300]}
            return {"label": label, "query": query, "records": [], "answer_preview": str(raw)[:200]}
    except Exception as e:
        return {"label": label, "query": query, "records": [], "error": str(e)}


# ============================================================
# Round 1: 关键字 vs prompt — 半导体设备
# ============================================================
print("=" * 70)
print("Round 1: 关键字 vs prompt — 半导体设备")
print("=" * 70)

r_kw = probe_one("keyword", "半导体设备")
time.sleep(2)
r_pm = probe_one("prompt", "请筛选出A股市场中半导体设备行业的上市公司，包括刻蚀、薄膜沉积、清洗、检测等设备厂商")

for r in [r_kw, r_pm]:
    if r is None:
        continue
    recs = r["records"]
    fields = list(recs[0].keys()) if recs else []
    print(f"\n[{r['label']}] records={len(recs)} | fields={len(fields)} {fields}")
    for i, rec in enumerate(recs[:5]):
        print(f"  [{i}] {json.dumps(rec, ensure_ascii=False)[:250]}")
    if len(recs) > 5:
        print(f"  ... (共 {len(recs)} 条)")
    if r.get("error"):
        print(f"  error: {r['error']}")

# ============================================================
# Round 2: 关键字 vs prompt — 白酒
# ============================================================
print("\n" + "=" * 70)
print("Round 2: 关键字 vs prompt — 白酒行业")
print("=" * 70)

r_kw2 = probe_one("keyword", "白酒")
time.sleep(2)
r_pm2 = probe_one("prompt", "请筛选出A股市场中白酒行业的上市公司，包括高端白酒、次高端白酒、区域名酒等")

for r in [r_kw2, r_pm2]:
    if r is None:
        continue
    recs = r["records"]
    fields = list(recs[0].keys()) if recs else []
    print(f"\n[{r['label']}] records={len(recs)} | fields={len(fields)} {fields}")
    for i, rec in enumerate(recs[:5]):
        print(f"  [{i}] {json.dumps(rec, ensure_ascii=False)[:250]}")
    if len(recs) > 5:
        print(f"  ... (共 {len(recs)} 条)")
    if r.get("error"):
        print(f"  error: {r['error']}")

# ============================================================
# Round 3: 简短关键词 vs 详细 prompt — 同主题对比
# ============================================================
print("\n" + "=" * 70)
print("Round 3: 同主题 keyword vs prompt 字段覆盖对比")
print("=" * 70)

COMPARISONS = [
    {
        "label": "半导体-简单关键词",
        "query": "芯片",
    },
    {
        "label": "半导体-多关键词",
        "query": "集成电路 芯片设计 晶圆代工 封装测试",
    },
    {
        "label": "半导体-简短prompt",
        "query": "请筛选出A股市场中的半导体芯片上市公司",
    },
    {
        "label": "半导体-详细prompt",
        "query": "请筛选出A股市场中半导体芯片行业的上市公司，需要包含：IC设计、晶圆代工、封装测试、半导体设备、半导体材料等环节",
    },
]

results = []
for comp in COMPARISONS:
    r = probe_one(comp["label"], comp["query"])
    results.append(r)
    recs = r["records"] if r else []
    fields = list(recs[0].keys()) if recs else []
    print(f"\n[{comp['label']}] records={len(recs)} | fields={len(fields)} {fields}")
    for i, rec in enumerate(recs[:3]):
        print(f"  [{i}] {json.dumps(rec, ensure_ascii=False)[:300]}")
    if len(recs) > 3:
        print(f"  ... (共 {len(recs)} 条)")
    time.sleep(2)

print("\n" + "=" * 70)
print("探测完成")
print("=" * 70)
