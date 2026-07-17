"""Diagnostic probe v2: deep-dive into 688221 market_data failure"""
import sys
import io
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).resolve().parent))

from stock_agent.ifind_client import IfindClient
from stock_agent.fetchers.market_data.fetcher import fetch_market_data

print("=" * 60)
print("[PROBE v2] Deep-dive: 688221 market_data fetcher")
print("=" * 60)

client = IfindClient()

# Try market_data directly
print("\n[Step 1] Calling fetch_market_data directly...")
try:
    market = fetch_market_data(client, "688221")
    print(f"  Result type: {type(market).__name__}")
    if hasattr(market, "record_count"):
        print(f"  record_count: {market.record_count}")
    print(f"  Result: {market}")
    if market.record_count == 0:
        print("  -> Empty result (treated as failure by fetch_stock_data)")
except Exception as e:
    print(f"  [FAIL] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Also test with a known working stock for comparison
print("\n[Step 2] Comparison: fetch_market_data for 600519 (Kweichow Moutai)...")
try:
    market = fetch_market_data(client, "600519")
    print(f"  record_count: {market.record_count}")
except Exception as e:
    print(f"  [FAIL] {type(e).__name__}: {e}")

# Check if IfindClient has any special handling for different exchanges
print("\n[Step 3] Checking iFind market data query...")
print("  The market_data fetcher queries iFind for technical indicators.")
print("  Question: Does iFind have data for 688221 (STAR Market stock)?")

print("\n[OK] Probe v2 complete")
