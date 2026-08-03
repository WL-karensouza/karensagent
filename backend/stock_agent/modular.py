"""E3 实验原型：Plan&Solve 模块化生成（不接入生产管线，仅供 e3 实验调用）

流程：Planner 规划结论骨架（score/decision/signal_attribution/核心逻辑）
→ 9 个模块各携带"数据报告 + 骨架"独立生成（串行，测出耗时再议并行）
→ 拼装完整报告 → E0 validator 校验

每个模块有独立 prompt（MODULE_PROMPTS），输出该模块子 schema 的纯 JSON。
"""
import json
import os
import sys
import time

from openai import OpenAI

from stock_agent.validator import validate_report

# ═══════════════════════════════════════════
# Prompt 定义（Planner + 9 模块独立 prompt）
# ═══════════════════════════════════════════

PLANNER_PROMPT = """你是投研分析的规划负责人。基于股票数据报告，先规划报告总骨架——只规划骨架，不写模块正文。

输出严格纯 JSON：
{
  "score": 0-100的整数,
  "decision": "看多/震荡/看空",
  "stance": "一句话总判断（必须包含趋势判断 + 风险提示）",
  "core_points": ["全局核心逻辑1", "核心逻辑2", "核心逻辑3"],
  "main_risks": ["风险点1", "风险点2"],
  "main_catalysts": ["利好催化1", "催化2"],
  "signal_attribution": [
    {"source": "估值面", "weight": 0.20, "direction": "偏多/偏空/中性", "note": "一句依据"},
    {"source": "财务面", "weight": 0.25, "direction": "...", "note": "..."},
    {"source": "资金面", "weight": 0.15, "direction": "...", "note": "..."},
    {"source": "情绪面", "weight": 0.15, "direction": "...", "note": "..."},
    {"source": "风险面", "weight": 0.10, "direction": "...", "note": "..."},
    {"source": "筹码面", "weight": 0.15, "direction": "...", "note": "..."}
  ]
}
规划纪律：score≥60 应对应看多、≤40 对应看空；signal_attribution 权重和必须为 1.0；
结论必须有数据支撑不编造，数据不足的方向标注"数据不足"并给保守权重。只输出纯 JSON。"""

# 各模块共用纪律（拼接在每个模块 prompt 尾部）
_COMMON = """通用纪律：严格遵循「数据事实化 → 逻辑推演化 → 散民口语化」三步思考链；不编造数据，缺失数据标注"数据不可用"；
禁止术语堆砌（必须使用专业术语时括号内加白话解释）；区分"数据显示"（事实）与"分析认为"（推断）；
只输出纯 JSON，不要 markdown 包裹、不要解释文字。"""

MODULE_PROMPTS = {
    "module_1_核心结论": f"""你是首席分析师，负责核心结论模块。基于数据报告与总体骨架产出：
{{
  "rating_sentence": "一句话评级（趋势判断 + 风险提示 + 建议方向，如'短期趋势向好但估值偏高，建议观望'）",
  "core_logic": ["核心要点1（数据事实 + 逻辑判断）", "核心要点2", "核心要点3"],
  "reference_prices": {{
    "support": "支撑位及依据（如'5.0元附近，60日均线+前期低点'），数据不足标注'数据不足无法判断'",
    "resistance": "压力位及依据，数据不足同上标注"
  }}
}}
要求：core_logic 应呼应骨架 core_points 并加以具体化；支撑/压力位必须有技术依据。
{_COMMON}""",

    "module_2_公司画像": f"""你是基本面分析师，负责公司画像与估值模块。产出：
{{
  "business": "大白话主营业务（剥离枯燥经营范围文本，说清公司靠什么赚钱）",
  "valuation": {{
    "pe_level": "偏低/合理/偏高/极度偏高",
    "pb_level": "偏低/合理/偏高/极度偏高",
    "analysis": "PE/PB 与历史水平及行业对比，2-3 句话说清估值水位，散户现在进场是捡便宜还是接盘"
  }}
}}
{_COMMON}""",

    "module_3_财务健康": f"""你是财务分析师，负责财务健康模块。产出：
{{
  "profitability": "一句话概括赚钱能力（必须包含营收和净利润的同比/环比变化方向）",
  "key_indicators": [
    {{"name": "毛利率", "value": "XX%", "trend": "连续上升/下滑/稳定", "verdict": "说明产品竞争力"}},
    {{"name": "ROE", "value": "XX%", "trend": "...", "verdict": "说明股东回报"}},
    {{"name": "资产负债率", "value": "XX%", "trend": "...", "verdict": "说明财务稳健度"}},
    {{"name": "经营现金流/净利润", "value": "X.X", "trend": "...", "verdict": "大于1是真金白银，小于1是纸面富贵"}}
  ],
  "risk_alerts": ["异常财务信号白话解读（如'应收账款增速远超营收——利润可能是纸面富贵'），无异常写'暂无明显财务风险信号'"]
}}
要求：key_indicators 至少 4 项；必须覆盖盈利能力/成长趋势/偿债安全/现金流质量四个维度。
{_COMMON}""",

    "module_4_股价走势": f"""你是技术分析师，负责股价走势与资金模块。产出：
{{
  "trend": "近期走势特征总结（如'放量突破前期平台'/'缩量回调至60日均线'），2-3 句话说清当前形态",
  "capital_flow": {{
    "margin_trading": "融资融券分析（如'融资余额持续上升，杠杆资金加仓'），数据不足标注'数据不可用'",
    "main_force": "主力资金动向（如'近5日主力净流入XX万'），数据不足同上"
  }}
}}
{_COMMON}""",

    "module_5_北向资金": f"""你是资金面分析师，负责北向资金模块。产出：
{{
  "available": true或false,
  "trend": "北向资金/沪深港通动向（如'连续3日净买入，累计净流入X亿'）；无数据时 available=false 且此字段写'北向资金数据暂不可用'",
  "interpretation": "散户听得懂的解读（如'外资逢低捡便宜，说明机构认可这个价位'）；无数据时写'北向资金数据暂不可用'"
}}
{_COMMON}""",

    "module_6_股东筹码": f"""你是筹码分析师，负责股东结构与筹码模块。产出：
{{
  "major_moves": [
    {{"entity": "高管/股东名称", "action": "增减持动作", "date": "日期", "signal": "偏多/偏空/中性", "reason": "白话解读"}}
  ],
  "chip_analysis": "筹码集中度判断（如'股东户数连续减少+户均持股上升→筹码集中，主力可能在吸筹'），数据不足说清缺什么"
}}
要求：确实无增减持事件时 major_moves 可为空数组，但 chip_analysis 必须给出判断。
{_COMMON}""",

    "module_7_催化舆情": f"""你是舆情分析师，负责催化剂与舆情模块。产出：
{{
  "positive": ["利好事件 + 对股价的潜在影响（至少1条，数据不足写'暂无明显利好事件'）"],
  "negative": ["利空事件 + 对股价的潜在影响（至少1条，数据不足写'暂无明显利空事件'）"],
  "sentiment": "偏乐观/偏谨慎/中性",
  "sentiment_reason": "一句话总结媒体和研报的整体态度及原因"
}}
{_COMMON}""",

    "module_8_风险ESG": f"""你是风控分析师，负责风险与 ESG 模块。产出：
{{
  "risk_level": "低/中/高",
  "risks": [
    {{"type": "市场风险/退市风险/商誉减值风险/流动性风险/政策风险/其他", "level": "高/中/低", "desc": "白话描述风险及对散户的实际影响"}}
  ],
  "esg": "ESG 通俗解读（说清三件事：环保有无政策打压风险、社会责任有无舆论隐患、大股东是否靠谱），数据不足标注具体缺项"
}}
要求：risks 至少 2 个（核心硬性要求，结合骨架 main_risks 展开）。
{_COMMON}""",

    "module_9_操作指南": f"""你是投资顾问，负责散户实战操作指南模块。产出：
{{
  "buy_strategy": "分批建仓观察建议（如'建议分2-3批在5.0-5.3元区间关注，不要一次性满仓'）——只能是观察建议，不能是买卖指令",
  "stop_loss": "止损参考及理由（如'跌破4.8元需警惕，中期趋势可能转弱'）",
  "take_profit": "止盈参考及理由（如'5.8-6.0元附近遇阻可考虑分批止盈'）",
  "holding_period": {{
    "type": "短线博弈/中短线波段/中长线持有",
    "reason": "一句话理由"
  }}
}}
红线：不输出"买入/卖出/加仓/减仓"等直接交易指令，只给观察方向。
{_COMMON}""",
}

# 模块生成顺序（module_1 最后生成：它需要呼应骨架，放最后可携带其他模块的既成事实——v1 暂不传模块间上下文，顺序仅为拼装顺序）
MODULE_KEYS = list(MODULE_PROMPTS.keys())


# ═══════════════════════════════════════════
# LLM 调用与主流程
# ═══════════════════════════════════════════

def _call_llm(system: str, user: str, max_tokens: int = 8192) -> tuple[dict, dict]:
    """单次调用 + 纯 JSON 解析（复用 _parse_json 全部容错策略），返回 (dict, usage)"""
    from stock_agent.analyze import _parse_json

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        extra_body={"thinking": {"type": "enabled"}},
        reasoning_effort="high",
        max_tokens=max_tokens,
    )
    content = resp.choices[0].message.content or ""
    reasoning = getattr(resp.choices[0].message, "reasoning_content", None)
    if not content.strip() and reasoning:
        content = reasoning
    usage = {
        "prompt": resp.usage.prompt_tokens,
        "completion": resp.usage.completion_tokens,
        "total": resp.usage.total_tokens,
        "finish_reason": resp.choices[0].finish_reason,
    }
    # 剥离 markdown 包裹后走统一容错解析
    raw = content.strip()
    if "```json" in raw:
        raw = raw.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in raw:
        raw = raw.split("```", 1)[1].split("```", 1)[0]
    return _parse_json(raw.strip()), usage


def _accumulate(acc: dict, usage: dict) -> None:
    for k in ("prompt", "completion", "total"):
        acc[k] = acc.get(k, 0) + usage.get(k, 0)


def modular_analyze(markdown_report: str, history_context: str = "") -> tuple[dict, dict, dict]:
    """E3 实验入口：plan → 逐模块 solve → 拼装 → 校验

    Returns:
        (report, usage, stats)
        stats = {calls, truncations, module_fails[], issues[], elapsed}
    """
    t0 = time.time()
    usage_acc = {"prompt": 0, "completion": 0, "total": 0}
    stats = {"calls": 0, "truncations": 0, "module_fails": [], "issues": []}

    # Step 1: Plan（历史上下文只在此阶段注入，避免模块阶段重复携带）
    user = f"## 数据报告\n{markdown_report}"
    if history_context:
        user += f"\n\n{history_context}"
    plan, plan_usage = _call_llm(PLANNER_PROMPT, user)
    _accumulate(usage_acc, plan_usage)
    stats["calls"] += 1
    if plan_usage.get("finish_reason") == "length":
        stats["truncations"] += 1
    print(f"[modular] Plan 完成: score={plan.get('score')} decision={plan.get('decision')}", file=sys.stderr)

    skeleton_text = json.dumps(
        {k: plan.get(k) for k in ("stance", "core_points", "main_risks", "main_catalysts")},
        ensure_ascii=False,
    )

    # Step 2: 逐模块独立生成（串行）
    report = {
        "score": plan.get("score"),
        "decision": plan.get("decision"),
        "signal_attribution": plan.get("signal_attribution", []),
    }
    for key in MODULE_KEYS:
        m_usage = {}
        try:
            module_json, m_usage = _call_llm(
                MODULE_PROMPTS[key],
                f"## 总体骨架（规划阶段结论，本模块须与之保持一致）\n{skeleton_text}\n\n## 数据报告\n{markdown_report}",
            )
            report[key] = module_json
            if m_usage.get("finish_reason") == "length":
                stats["truncations"] += 1
        except Exception as e:
            stats["module_fails"].append(key)
            report[key] = {}  # 占位，validator 会报出具体缺失
            print(f"[modular] ⚠️ {key} 生成失败: {e}", file=sys.stderr)
        _accumulate(usage_acc, m_usage)
        stats["calls"] += 1

    # Step 3: E0 校验
    stats["issues"] = validate_report(report)
    stats["elapsed"] = round(time.time() - t0, 1)
    print(f"[modular] 完成: {stats['calls']} 次调用, 截断 {stats['truncations']}, "
          f"失败模块 {stats['module_fails']}, 违规 {len(stats['issues'])}, 耗时 {stats['elapsed']}s", file=sys.stderr)
    return report, usage_acc, stats
