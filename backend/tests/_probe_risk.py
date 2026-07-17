"""探查 get_risk_indicators — 能否一次调用同时拿到 Beta + Sharpe"""
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
S = "600519"

QUERIES = {
    "beta_sharpe_kw": f"{S} 贝塔 夏普比率 波动率 最大回撤",
    "prompt_all": (
        f"请返回贵州茅台({S})的完整风险指标，需要同时包含："
        "贝塔系数(Beta)、夏普比率(Sharpe)、波动率、最大回撤、Alpha、年化收益率"
    ),
    "prompt_beta_first": (
        f"请返回贵州茅台({S})的贝塔系数最近7个交易日数据，"
        "以及夏普比率、波动率、最大回撤"
    ),
    "prompt_short": f"请返回贵州茅台({S})的风险评级数据，含贝塔和夏普比率",
}

print("=" * 70)
print("get_risk_indicators: 能否同时拿到 Beta + Sharpe?")
print("=" * 70)

for label, query in QUERIES.items():
    raw = client.call_raw_text("stock", "get_risk_indicators", {"query": query})
    lines = raw.split("\n")

    header = ""
    for line in lines:
        if line.startswith("|证券代码|"):
            header = line
            break

    json_start = raw.find("```json")
    json_end = raw.find("```", json_start + 7) if json_start > -1 else -1
    indicators = []
    if json_start > -1 and json_end > -1:
        try:
            meta = json.loads(raw[json_start + 7 : json_end])
            indicators = list(meta.keys())
        except Exception:
            pass

    data_rows = [
        line
        for line in lines
        if line.startswith("|")
        and "---" not in line
        and "证券代码" not in line
        and "指标名称" not in line
        and "均值" not in line
    ]

    print(f"\n[{label}]")
    print(f"  表头: {header}")
    print(f"  JSON指标: {indicators}")
    print(f"  数据行数: {len(data_rows)}")
    for r in data_rows[:4]:
        print(f"  {r[:130]}")
