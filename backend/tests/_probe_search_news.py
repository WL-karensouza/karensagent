"""探查 search_news 接口 — query 最佳写法 + size 上限 + 返回字段"""
import os, sys, json
from pathlib import Path
from datetime import datetime, timedelta

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 加载 .env
env_path = BACKEND_DIR / ".env"
with open(env_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

from stock_agent.ifind_client import IfindClient, extract_raw_text

client = IfindClient()
STOCK_CODE = "600519"
STOCK_NAME = "贵州茅台"
TODAY = datetime.now().strftime("%Y-%m-%d")

# ============================================================
# Round 1: Query 格式对比（固定 size=20, 30 天）
# ============================================================
print("=" * 70)
print("Round 1: Query 格式对比 (size=20, 30天)")
print("=" * 70)

QUERY_FORMATS = {
    "code_only": STOCK_CODE,
    "name_only": STOCK_NAME,
    "code_name": f"{STOCK_CODE} {STOCK_NAME}",
    "code_plus": f"{STOCK_CODE} 财报 分红 回购 业绩",
    "nl_prompt": f"请返回{STOCK_NAME}({STOCK_CODE})近30天的重要财经新闻，包括财报、分红、回购、业绩预告、重大合同、高管变动等方面",
}

month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

for label, query in QUERY_FORMATS.items():
    try:
        result = client.call_and_parse("news", "search_news", {
            "query": query,
            "time_start": month_ago,
            "time_end": TODAY,
            "size": 20,
        })
        ok = "OK" if result["ok"] else "EMPTY"
        fields = result.get("field_names", [])
        print(f"\n[{ok}] query={label:12s} | records={result['record_count']:>3} | fields={len(fields):>2} {fields[:8]}")
        if result["record_count"] > 0:
            # 打印第一条做样本
            first = result["records"][0]
            for k, v in first.items():
                val = str(v)[:80]
                print(f"    {k}: {val}")
    except Exception as e:
        print(f"\n[FAIL] query={label:12s} | {type(e).__name__}: {e}")

# ============================================================
# Round 2: Size 上限探测（固定最佳 query, 30 天）
# ============================================================
print("\n" + "=" * 70)
print("Round 2: Size 上限探测 (query=code_name, 30天)")
print("=" * 70)

for size in [20, 50, 100, 200]:
    try:
        result = client.call_and_parse("news", "search_news", {
            "query": f"{STOCK_CODE} {STOCK_NAME}",
            "time_start": month_ago,
            "time_end": TODAY,
            "size": size,
        })
        ok = "OK" if result["ok"] else "EMPTY"
        print(f"  size={size:>4} -> records={result['record_count']:>3} [{ok}]")
    except Exception as e:
        print(f"  size={size:>4} -> {type(e).__name__}: {e}")

# ============================================================
# Round 3: 时间范围探测（固定最佳 query, size=50）
# ============================================================
print("\n" + "=" * 70)
print("Round 3: 时间范围探测 (query=code_name, size=50)")
print("=" * 70)

for days in [7, 30, 90, 180, 365]:
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        result = client.call_and_parse("news", "search_news", {
            "query": f"{STOCK_CODE} {STOCK_NAME}",
            "time_start": start,
            "time_end": TODAY,
            "size": 50,
        })
        ok = "OK" if result["ok"] else "EMPTY"
        print(f"  {days:>3}天范围 -> records={result['record_count']:>3} [{ok}]")
    except Exception as e:
        print(f"  {days:>3}天范围 -> {type(e).__name__}: {e}")

# ============================================================
# Round 4: 原始文本探查（看原始 JSON 结构）
# ============================================================
print("\n" + "=" * 70)
print("Round 4: 原始文本探查")
print("=" * 70)

try:
    raw_text = client.call_raw_text("news", "search_news", {
        "query": f"{STOCK_CODE} {STOCK_NAME}",
        "time_start": month_ago,
        "time_end": TODAY,
        "size": 3,
    })
    print(f"  raw_text 长度: {len(raw_text)} 字符")
    print(f"  raw_text 前 500 字符:")
    print(raw_text[:500])
    print(f"\n  raw_text 类型: {type(raw_text).__name__}")
    # 尝试解析为 JSON
    try:
        parsed = json.loads(raw_text)
        print(f"  JSON 顶层类型: {type(parsed).__name__}")
        if isinstance(parsed, list):
            print(f"  JSON 数组长度: {len(parsed)}")
            if parsed:
                print(f"  第一条的 keys: {list(parsed[0].keys()) if isinstance(parsed[0], dict) else 'NOT_DICT'}")
                print(f"  第一条内容: {json.dumps(parsed[0], ensure_ascii=False, indent=2)[:300]}")
    except json.JSONDecodeError:
        print("  (非 JSON 格式)")
except Exception as e:
    print(f"  [FAIL] {type(e).__name__}: {e}")

# ============================================================
# Round 5: 多股票对比（看不同股票新闻量差异）
# ============================================================
print("\n" + "=" * 70)
print("Round 5: 多股票对比 (query=code+name, size=50, 30天)")
print("=" * 70)

STOCKS = [
    ("600519", "贵州茅台"),
    ("000858", "五粮液"),
    ("688981", "中芯国际"),
    ("300750", "宁德时代"),
    ("002371", "北方华创"),
]

for code, name in STOCKS:
    try:
        result = client.call_and_parse("news", "search_news", {
            "query": f"{code} {name}",
            "time_start": month_ago,
            "time_end": TODAY,
            "size": 50,
        })
        ok = "OK" if result["ok"] else "EMPTY"
        has_fields = result.get("field_names", [])
        # 打印时间范围看覆盖度
        dates = set()
        for r in result.get("records", []):
            for k in ("time", "date", "publish_time", "新闻时间"):
                if r.get(k):
                    dates.add(r[k][:10])
        print(f"  {code} {name:6s} -> records={result['record_count']:>3} [{ok}] "
              f"fields={len(has_fields)} dates_span={min(dates) if dates else 'N/A'}~{max(dates) if dates else 'N/A'}")
    except Exception as e:
        print(f"  {code} {name:6s} -> {type(e).__name__}: {e}")

print("\n" + "=" * 70)
print("探测完成")
print("=" * 70)
