"""E1 实验：JSON 字段完整度抽样（适配 2026-07-16 9 模块 Schema）

对 3 只不同类型股票走完整管道，统计 report_json 字段完整度。
"""
import asyncio
import json
import sys
import os

# 确保工作树后端在 sys.path 最前面
WORKTREE = r"d:\karensAgent\.claude\worktrees\ifind-refactor\backend"
for p in list(sys.path):
    if "karensAgent" in p and "worktrees" not in p:
        sys.path.remove(p)
if WORKTREE not in sys.path:
    sys.path.insert(0, WORKTREE)

os.chdir(WORKTREE)

STOCKS = [
    ("600519", "茅台/沪市蓝筹"),
    ("300750", "宁德/创业板"),
    ("688221", "前沿生物/科创板"),
]

# 需要检查的字段及期望（9 模块新 Schema）
FIELDS = {
    "score": {"required": True, "type": (int, float)},
    "decision": {"required": True, "type": str},
    "module_1_核心结论": {"required": True, "type": dict},
    "module_2_公司画像": {"required": True, "type": dict},
    "module_3_财务健康": {"required": True, "type": dict},
    "module_4_股价走势": {"required": True, "type": dict},
    "module_5_北向资金": {"required": True, "type": dict},
    "module_6_股东筹码": {"required": True, "type": dict},
    "module_7_催化舆情": {"required": True, "type": dict},
    "module_8_风险ESG": {"required": True, "type": dict},
    "module_9_操作指南": {"required": True, "type": dict},
    "signal_attribution": {"required": True, "type": list},
}

# 各模块关键子字段检查
MODULE_CHECKS = {
    "module_1_核心结论": ["rating_sentence", "core_logic", "reference_prices"],
    "module_2_公司画像": ["business", "valuation"],
    "module_3_财务健康": ["profitability", "key_indicators", "risk_alerts"],
    "module_4_股价走势": ["trend", "capital_flow"],
    "module_5_北向资金": ["available", "trend", "interpretation"],
    "module_6_股东筹码": ["major_moves", "chip_analysis"],
    "module_7_催化舆情": ["positive", "negative", "sentiment"],
    "module_8_风险ESG": ["risk_level", "risks", "esg"],
    "module_9_操作指南": ["buy_strategy", "stop_loss", "take_profit", "holding_period"],
}


def check_field(report: dict, field: str, spec: dict) -> str:
    """检查单个字段，返回状态：✅ / ⚠️ / ❌"""
    if field not in report:
        return "❌ 缺失" if spec["required"] else "⚠️ 缺失(非必需)"
    val = report[field]
    if val is None:
        return "❌ null" if spec["required"] else "⚠️ null(非必需)"
    if not isinstance(val, spec["type"]):
        return f"⚠️ 类型错误(期望{spec['type'].__name__}, 实际{type(val).__name__})"
    if isinstance(val, str) and not val.strip():
        return "❌ 空字符串" if spec["required"] else "⚠️ 空字符串"
    if isinstance(val, (list, dict)) and len(val) == 0:
        return "⚠️ 空集合" if spec["required"] else "⚠️ 空集合"
    return "✅"


def check_module(report: dict, module_key: str, sub_fields: list) -> dict:
    """检查模块内部子字段完整度"""
    module = report.get(module_key, {})
    result = {}
    if not isinstance(module, dict):
        return {module_key: "❌ 非dict"}

    for sf in sub_fields:
        if sf not in module or module[sf] is None:
            result[sf] = "⚠️ 缺失"
        elif isinstance(module[sf], str) and not module[sf].strip():
            result[sf] = "⚠️ 空字符串"
        elif isinstance(module[sf], (list, dict)) and len(module[sf]) == 0:
            result[sf] = "⚠️ 空集合"
        else:
            result[sf] = "✅"
    return result


async def run_one(stock_code: str, label: str) -> dict:
    """对一只股票走完整 invest_gen 管道"""
    from stock_agent.skill.report import generate_report_stream
    from stock_agent.analyze import analyze

    print(f"\n{'='*60}")
    print(f"📊 测试: {stock_code} ({label})")
    print(f"{'='*60}")

    # Phase 1: 数据采集
    print("  Phase 1: iFinD SKILL 数据采集...")
    report_md = ""
    dim_ok = 0
    dim_fail = 0
    async for sse_msg in generate_report_stream(stock_code):
        if '"type": "complete"' in sse_msg:
            try:
                data_str = sse_msg.replace("data: ", "").strip()
                payload = json.loads(data_str)
                report_md = payload.get("report", "")
            except Exception:
                pass
            continue
        if '"type": "progress"' in sse_msg and '"status": "done"' in sse_msg:
            dim_ok += 1
        if '"type": "progress"' in sse_msg and '"status": "error"' in sse_msg:
            dim_fail += 1

    print(f"  数据采集完成: {dim_ok} 成功, {dim_fail} 失败, report_md {len(report_md)} 字符")

    if not report_md:
        print("  ❌ 数据采集失败，跳过")
        return {"stock": stock_code, "label": label, "error": "数据采集失败", "dim_ok": dim_ok, "dim_fail": dim_fail}

    # Phase 2: DeepSeek 分析
    print("  Phase 2: DeepSeek 分析...")
    loop = asyncio.get_running_loop()
    report_json, usage = await loop.run_in_executor(None, analyze, report_md)
    print(f"  Token: {usage.get('total', '?')}, score={report_json.get('score')}, decision={report_json.get('decision')}")

    # 顶层字段检查
    print(f"\n  📋 顶层字段完整度:")
    field_results = {}
    for field, spec in FIELDS.items():
        status = check_field(report_json, field, spec)
        field_results[field] = status
        print(f"    {status}  {field}")

    # 各模块子字段检查
    print(f"\n  📋 模块子字段完整度:")
    all_module_results = {}
    for module_key, sub_fields in MODULE_CHECKS.items():
        mr = check_module(report_json, module_key, sub_fields)
        all_module_results[module_key] = mr
        ok_count = sum(1 for v in mr.values() if "✅" in v)
        print(f"    {module_key}: {ok_count}/{len(sub_fields)} 子字段完整")

    # 提取 rating_sentence 作为摘要
    m1 = report_json.get("module_1_核心结论", {})
    rating = m1.get("rating_sentence", "")[:80]

    # signal_attribution 权重检查
    sa = report_json.get("signal_attribution", [])
    sa_weight_sum = sum(item.get("weight", 0) for item in sa) if sa else 0

    return {
        "stock": stock_code,
        "label": label,
        "dim_ok": dim_ok,
        "dim_fail": dim_fail,
        "report_md_len": len(report_md),
        "score": report_json.get("score"),
        "decision": report_json.get("decision"),
        "rating_sentence": rating + ("..." if len(rating) == 80 else ""),
        "usage": usage,
        "field_results": field_results,
        "module_results": all_module_results,
        "sa_weight_sum": sa_weight_sum,
    }


async def main():
    results = []
    for code, label in STOCKS:
        try:
            r = await run_one(code, label)
            results.append(r)
        except Exception as e:
            import traceback
            print(f"\n❌ {code} 异常: {e}")
            traceback.print_exc()
            results.append({"stock": code, "label": label, "error": str(e)})

    # 汇总
    print(f"\n\n{'='*60}")
    print(f"📊 E1 实验汇总 (v2 9模块)")
    print(f"{'='*60}")

    all_ok = True
    for r in results:
        if "error" in r:
            print(f"  ❌ {r['stock']} ({r['label']}): {r['error']}")
            all_ok = False
            continue

        fr = r["field_results"]
        score_ok = "✅" in fr.get("score", "")
        decision_ok = "✅" in fr.get("decision", "")
        modules_ok = sum(1 for f in fr if f.startswith("module_") and "✅" in fr[f])
        sa_ok = "✅" in fr.get("signal_attribution", "")

        print(f"  {r['stock']} ({r['label']}): "
              f"score={'✅' if score_ok else '❌'} "
              f"decision={'✅' if decision_ok else '❌'} "
              f"modules={modules_ok}/9 "
              f"signal_attr={'✅' if sa_ok else '❌'} "
              f"dim={r['dim_ok']}/{r['dim_ok']+r['dim_fail']} "
              f"sa_weight_sum={r.get('sa_weight_sum', '?'):.2f}")

    # 结论
    n = len([r for r in results if "error" not in r])
    if n == 0:
        print("\n❌ 无有效结果")
        return results

    score_rate = sum(1 for r in results if "error" not in r and "✅" in r.get("field_results", {}).get("score", ""))
    decision_rate = sum(1 for r in results if "error" not in r and "✅" in r.get("field_results", {}).get("decision", ""))
    modules_ok_count = sum(1 for r in results if "error" not in r
                           and sum(1 for f in r.get("field_results", {}) if f.startswith("module_") and "✅" in r["field_results"][f]) == 9)

    print(f"\n📊 结论:")
    print(f"  score 出现率: {score_rate}/{n}")
    print(f"  decision 出现率: {decision_rate}/{n}")
    print(f"  9模块全完整: {modules_ok_count}/{n}")

    if n > 0 and score_rate == n and decision_rate == n:
        print(f"\n✅ P0 假设通过！score + decision 100% 出现")
    else:
        print(f"\n❌ P0 假设失败！需要加固后端 Prompt/JSON Schema")

    return results


if __name__ == "__main__":
    asyncio.run(main())
