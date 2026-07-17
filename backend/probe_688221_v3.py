"""Diagnostic probe v3: with .env loading, deep-dive into 688221"""
import sys
import io
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# IMPORTANT: Load config first to populate env vars from .env
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))
import config  # noqa: F401 — loads .env into os.environ

from stock_agent.ifind_client import IfindClient
from stock_agent.fetchers.market_data.fetcher import fetch_market_data

print("=" * 60)
print("[PROBE v3] 688221 market_data with .env loaded")
print("=" * 60)

# Verify auth token
import os
token = os.getenv("IFIND_AUTH_TOKEN", "")
print(f"  IFIND_AUTH_TOKEN: {'SET (' + token[:20] + '...)' if token else 'NOT SET!'}")

client = IfindClient()

# Test 688221
print("\n[Step 1] fetch_market_data for 688221...")
try:
    market = fetch_market_data(client, "688221")
    print(f"  record_count: {market.record_count}")
    if market.record_count > 0:
        for r in market._records[:3]:
            print(f"    - {r}")
except Exception as e:
    print(f"  [FAIL] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Test full fetch_stock_data for 688221
print("\n[Step 2] fetch_stock_data for 688221...")
from stock_agent.fetchers import fetch_stock_data
try:
    data = fetch_stock_data(client, "688221")
    print(f"  [OK] stock_name: {data.get('stock_name', '?')}")
    for key in ["market", "financials", "shareholders", "news_events", "risk", "market_env"]:
        model = data.get(key)
        if model is None:
            print(f"    {key}: None")
        elif hasattr(model, "record_count"):
            print(f"    {key}: {model.record_count} records")
        elif hasattr(model, "news_count"):
            print(f"    {key}: {model.news_count} news, {model.notice_count} notices")
        elif hasattr(model, "risk_count"):
            print(f"    {key}: {model.risk_count} risk, {model.esg_count} esg")
    if data.get("warnings"):
        for w in data["warnings"]:
            print(f"    [WARN] {w['dimension']}: {w['reason']}")
except Exception as e:
    print(f"  [FAIL] {type(e).__name__}: {e}")

# Test comparison: 600519
print("\n[Step 3] fetch_market_data for 600519 (comparison)...")
try:
    market = fetch_market_data(client, "600519")
    print(f"  record_count: {market.record_count}")
except Exception as e:
    print(f"  [FAIL] {type(e).__name__}: {e}")

print("\n[OK] Probe v3 complete")
