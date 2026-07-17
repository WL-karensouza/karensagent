"""Diagnostic probe: test 688221 analysis pipeline"""
import sys
import io
import json
from pathlib import Path

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stock_agent.ifind_client import IfindClient
from stock_agent.fetchers import fetch_stock_data

print("=" * 60)
print("[PROBE] 688221 Data Collection Diagnostic")
print("=" * 60)

client = IfindClient()

# Step 1: Collect data
print("\n[Step 1] Collecting data...")
try:
    data = fetch_stock_data(client, "688221")
    print("[OK] Collection succeeded")
    print(f"  stock_code: {data['stock_code']}")
    print(f"  stock_name: {data['stock_name']}")

    # Check each dimension
    for key in ["market", "financials", "shareholders", "news_events", "risk", "market_env"]:
        model = data.get(key)
        if model is None:
            print(f"  [FAIL] {key}: None")
        elif hasattr(model, "record_count"):
            status = "[OK]" if model.record_count > 0 else "[WARN]"
            print(f"  {status} {key}: {model.record_count} records")
        elif hasattr(model, "news_count"):
            has_data = model.news_count > 0 or model.notice_count > 0
            print(f"  {'[OK]' if has_data else '[WARN]'} {key}: {model.news_count} news, {model.notice_count} notices")
        elif hasattr(model, "risk_count"):
            has_data = model.risk_count > 0 or model.esg_count > 0
            print(f"  {'[OK]' if has_data else '[WARN]'} {key}: {model.risk_count} risk, {model.esg_count} esg")
        else:
            print(f"  [???] {key}: unknown type")

    if data.get("warnings"):
        print(f"\n  [WARN] Warnings ({len(data['warnings'])}):")
        for w in data["warnings"]:
            print(f"    - {w['dimension']}: {w['reason']}")

except Exception as e:
    print(f"[FAIL] Collection failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Check prompt building
print("\n[Step 2] Building user prompt...")
from stock_agent.analyze import build_user_prompt
user_prompt = build_user_prompt(data)
print(f"  Prompt length: {len(user_prompt)} chars")
print(f"  First 200 chars: {user_prompt[:200]}...")

# Step 3: Check valid_sections
print("\n[Step 3] Checking data availability...")
valid_count = sum(
    1 for key in ["market", "financials", "shareholders", "news_events", "risk", "market_env"]
    if data.get(key) is not None
)
print(f"  Valid sections: {valid_count}/6")
if valid_count == 0:
    print("  [FAIL] No valid data, analyze() would raise DataIncompleteError")

print("\n[OK] Probe complete")
