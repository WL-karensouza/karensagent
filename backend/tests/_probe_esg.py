"""探查 get_esg_data — 关键字 vs prompt 对比"""
import os, sys, json
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

from stock_agent.ifind_client import IfindClient

client = IfindClient()
STOCK_CODE = "601127"
STOCK_NAME = "赛力斯"

# ============================================================
# Round 1: 关键字 vs prompt（call_and_parse）
# ============================================================
print("=" * 70)
print("Round 1: get_esg_data — 关键字 vs prompt (call_and_parse)")
print("=" * 70)

QUERIES = {
    "keyword": STOCK_CODE,
    "prompt": f"请返回{STOCK_NAME}({STOCK_CODE})的ESG评级数据，包括ESG综合评级、环境(E)、社会(S)、治理(G)各维度评分",
}

for label, query in QUERIES.items():
    try:
        result = client.call_and_parse("stock", "get_esg_data", {"query": query})
        ok = "OK" if result["ok"] else "EMPTY"
        fields = result.get("field_names", [])
        print(f"\n[{ok}] {label}: records={result['record_count']} | fields={len(fields)} {fields}")
        for i, rec in enumerate(result.get("records", [])):
            print(f"  [{i}] {json.dumps(rec, ensure_ascii=False)}")
    except Exception as e:
        print(f"\n[FAIL] {label}: {type(e).__name__}: {e}")

# ============================================================
# Round 2: 原始文本探查
# ============================================================
print("\n" + "=" * 70)
print("Round 2: get_esg_data — 原始文本探查")
print("=" * 70)

for label, query in QUERIES.items():
    try:
        raw = client.call_raw_text("stock", "get_esg_data", {"query": query})
        print(f"\n[{label}] raw_text 长度: {len(raw)} 字符")
        print(f"  前 800 字符:")
        print(raw[:800])
        # 尝试解析 JSON
        json_start = raw.find("```json")
        json_end = raw.find("```", json_start + 7) if json_start > -1 else -1
        if json_start > -1 and json_end > -1:
            try:
                meta = json.loads(raw[json_start + 7 : json_end])
                print(f"  JSON 元数据 keys: {list(meta.keys())}")
            except Exception:
                pass
    except Exception as e:
        print(f"\n[FAIL] {label}: {type(e).__name__}: {e}")

print("\n" + "=" * 70)
print("探测完成")
print("=" * 70)
