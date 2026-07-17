"""Diagnostic probe: full backend analysis flow for 688221"""
import sys
import io
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))
import config  # noqa: F401

from stock_agent.ifind_client import IfindClient
from stock_agent.fetchers import fetch_stock_data
from stock_agent.analyze import analyze, build_user_prompt

print("=" * 60)
print("[PROBE] 688221 Full Analysis Pipeline")
print("=" * 60)

# Step 1: Collect
print("\n[1] Collecting data...")
client = IfindClient()
data = fetch_stock_data(client, "688221")
print(f"    stock_name: {data.get('stock_name', '?')}")
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

# Step 2: Check valid_sections
print("\n[2] Checking valid_sections...")
valid_count = sum(
    1 for key in ["market", "financials", "shareholders", "news_events", "risk", "market_env"]
    if data.get(key) is not None
)
print(f"    valid_sections: {valid_count}/6")

# Step 3: Build user prompt (don't show full content, just stats)
print("\n[3] Building user prompt...")
user_prompt = build_user_prompt(data)
print(f"    prompt length: {len(user_prompt)} chars")

# Step 4: Call analyze (LLM)
print("\n[4] Calling analyze() — LLM invocation...")
try:
    report, usage = analyze(data)
    print(f"    [OK] score={report.get('score')}, decision={report.get('decision')}")
    print(f"    token usage: {usage}")

    # CRITICAL: Check sections
    sections = report.get("sections", {})
    print(f"\n[5] Sections returned by LLM ({len(sections)} total):")
    for section_name, section_data in sections.items():
        signal = section_data.get("signal") or section_data.get("sentiment") or section_data.get("level") or section_data.get("style_match") or "?"
        insight_len = len(section_data.get("insight", ""))
        print(f"    [{section_name}] signal={signal}, insight_len={insight_len}")

    # Map to frontend sectionMap keys
    print(f"\n[6] Frontend sectionMap compatibility check:")
    section_map = {
        "market": "技术面",
        "finance": "基本面及财务分析",
        "news": "消息面",
        "risk": "风险面",
        "env": "市场环境"
    }
    for frontend_key, llm_key in section_map.items():
        exists = llm_key in sections
        print(f"    {frontend_key} -> '{llm_key}': {'[OK]' if exists else '[MISSING]'} ")

    # Check if analyzeResult structure matches what frontend expects
    print(f"\n[7] Simulated frontend data flow:")
    # Backend returns: { code: 0, data: { status, report_id, report, usage, message } }
    simulated_result_data = {
        "status": "done",
        "report_id": 999,
        "report": report,
        "usage": usage,
        "message": "analysis done",
    }
    # Frontend does: store.analyzeResult = result.data
    # Then accesses: store.analyzeResult.report.sections
    frontend_report = simulated_result_data.get("report", {})
    frontend_sections = frontend_report.get("sections", {})
    print(f"    analyzeResult.report exists: {bool(frontend_report)}")
    print(f"    analyzeResult.report.sections exists: {bool(frontend_sections)}")
    print(f"    hasAnalyzed (analyzeResult !== null): true")
    for key, llm_key in section_map.items():
        has_data = llm_key in frontend_sections
        print(f"    hasDimData('{key}'): {has_data}")

except Exception as e:
    print(f"    [FAIL] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n[OK] Probe complete")
