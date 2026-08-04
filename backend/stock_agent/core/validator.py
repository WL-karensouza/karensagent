"""投研报告语义校验器 — E0 质量层基建

将 tests/e1_field_completeness.py 的字段完整度检查下沉为生产级硬规则校验。
validate_report() 返回违规清单（空列表 = 通过），每条违规是可读中文句子，
可直接回传给 LLM 做定点修正（见 analyze.analyze_with_validation）。

规则来源：prompts/output_schema.py 的 8 条注意 + 9 模块 Schema 硬性要求。
"""

# ═══════════════════════════════════════════
# 规则常量
# ═══════════════════════════════════════════

# 顶层必需字段 → 期望类型（迁移自 e1_field_completeness.FIELDS）
REQUIRED_FIELDS: dict[str, type | tuple] = {
    "score": (int, float),
    "decision": str,
    "module_1_核心结论": dict,
    "module_2_公司画像": dict,
    "module_3_财务健康": dict,
    "module_4_股价走势": dict,
    "module_5_北向资金": dict,
    "module_6_股东筹码": dict,
    "module_7_催化舆情": dict,
    "module_8_风险ESG": dict,
    "module_9_操作指南": dict,
    "signal_attribution": list,
}

# 各模块关键子字段（缺失 / null / 空字符串 均计违规；迁移自 e1_field_completeness.MODULE_CHECKS）
MODULE_SUB_FIELDS: dict[str, list[str]] = {
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

VALID_DECISIONS = ("看多", "震荡", "看空")
WEIGHT_SUM_TOLERANCE = 0.05      # signal_attribution 权重和容差（浮点误差）
MIN_KEY_INDICATORS = 4           # module_3 核心财务指标最少 4 项（schema 注意 7）
MIN_POSITIVE_NEGATIVE = 1        # module_7 利好/利空各至少 1 条（schema 注意 8）
MIN_RISKS = 2                    # module_8 风险点至少 2 个（core_rules 第 6 条）
BULLISH_SCORE_FLOOR = 60         # score ≥ 60 应偏乐观（schema 注意 4）
BEARISH_SCORE_CEIL = 40          # score ≤ 40 应偏悲观

# 9 大模块至少在场数个，低于即判坍塌（截断残片）
MIN_PRESENT_MODULES = 6
_MODULE_KEYS = tuple(k for k in REQUIRED_FIELDS if k.startswith("module_"))


class StructuralCollapseError(RuntimeError):
    """LLM 输出结构坍塌（思考吃满输出上限、正文截断成残片）

    与"小违规"区分：坍塌必须抛错触发上游整体重试，
    不得进入"违规不阻塞"流程被静默存库（2026-08-04 偶发空报告事故根因）。
    """

    def __init__(self, message: str, usage: dict | None = None):
        super().__init__(message)
        self.usage = usage or {}  # 携带当次调用成本，供上游重试累积保持可观测


def is_collapsed_report(report) -> bool:
    """结构坍塌判定：思考过程吃满输出预算、正文被截断时，容错解析可能把
    思考文字里的草稿残片救成合法 dict（如单个风险点对象），此类残片必须
    按生成失败处理。

    判定（满足任一）：非 dict / 缺 score / 缺 decision / 9 大模块在场少于 6 个。
    """
    if not isinstance(report, dict):
        return True
    if "score" not in report or "decision" not in report:
        return True
    present = sum(1 for k in _MODULE_KEYS if k in report)
    return present < MIN_PRESENT_MODULES


# ═══════════════════════════════════════════
# 校验主入口
# ═══════════════════════════════════════════

# 历史对比 changed_aspects 合法取值集合
VALID_CHANGED_ASPECTS = {"财务面", "股价面", "操作建议"}


def validate_report(report: dict, has_history: bool = False) -> list[str]:
    """语义校验报告 JSON，返回违规清单（空列表 = 全部通过）

    校验维度：
      1. 顶层必需字段齐全且类型正确
      2. score 范围 [0, 100]
      3. decision ∈ {看多, 震荡, 看空}
      4. 9 模块关键子字段非缺失 / 非空
      5. module_3 核心指标 ≥ 4 项
      6. module_7 利好/利空各 ≥ 1 条
      7. module_8 风险点 ≥ 2 个
      8. signal_attribution 权重非负且总和 = 1.0 ± 容差
      9. score 与 decision 方向一致性
     10. has_history=True 时：历史对比 4 字段强制校验（E1 v2）
    """
    if not isinstance(report, dict):
        return ["报告不是 JSON 对象，无法校验"]

    issues: list[str] = []
    _check_required_fields(report, issues)
    _check_score_and_decision(report, issues)
    _check_module_sub_fields(report, issues)
    _check_module_counts(report, issues)
    _check_signal_attribution(report, issues)
    _check_consistency(report, issues)
    if has_history:
        _check_history_fields(report, issues)
    return issues


# ═══════════════════════════════════════════
# 分项校验（内部函数）
# ═══════════════════════════════════════════

def _check_required_fields(report: dict, issues: list[str]) -> None:
    """顶层必需字段：缺失 / null / 类型错误 / 空值"""
    for field, expected in REQUIRED_FIELDS.items():
        if field not in report:
            issues.append(f"缺少顶层必需字段 {field}")
            continue
        val = report[field]
        if val is None:
            issues.append(f"顶层字段 {field} 为 null")
            continue
        if not isinstance(val, expected):
            issues.append(f"顶层字段 {field} 类型错误（应为 {expected}，实际 {type(val).__name__}）")
            continue
        # 空字符串 / 空集合视为违规（score 是数值不在此列）
        if isinstance(val, str) and not val.strip():
            issues.append(f"顶层字段 {field} 为空字符串")
        elif isinstance(val, (list, dict)) and len(val) == 0:
            issues.append(f"顶层字段 {field} 为空集合")


def _check_score_and_decision(report: dict, issues: list[str]) -> None:
    """score 范围与 decision 枚举"""
    score = report.get("score")
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        if not 0 <= score <= 100:
            issues.append(f"score={score} 超出 [0, 100] 范围")

    decision = report.get("decision")
    if isinstance(decision, str) and decision.strip() and decision not in VALID_DECISIONS:
        issues.append(f"decision='{decision}' 不在枚举 {VALID_DECISIONS} 内")


def _check_module_sub_fields(report: dict, issues: list[str]) -> None:
    """9 模块关键子字段：缺失 / null / 空字符串计违规（空集合不在此列，由计数规则专管）"""
    for module_key, sub_fields in MODULE_SUB_FIELDS.items():
        module = report.get(module_key)
        if not isinstance(module, dict):
            continue  # 顶层字段检查已报过缺失/类型问题，此处不重复
        for sf in sub_fields:
            if sf not in module or module[sf] is None:
                issues.append(f"{module_key} 缺少子字段 {sf}")
            elif isinstance(module[sf], str) and not module[sf].strip():
                issues.append(f"{module_key}.{sf} 为空字符串")


def _check_module_counts(report: dict, issues: list[str]) -> None:
    """模块内集合型字段的数量下限"""
    m3 = report.get("module_3_财务健康")
    if isinstance(m3, dict):
        indicators = m3.get("key_indicators")
        if isinstance(indicators, list) and len(indicators) < MIN_KEY_INDICATORS:
            issues.append(f"module_3 核心财务指标仅 {len(indicators)} 项，少于 {MIN_KEY_INDICATORS} 项（毛利率/ROE/资产负债率/现金流）")

    m7 = report.get("module_7_催化舆情")
    if isinstance(m7, dict):
        for side, label in (("positive", "利好"), ("negative", "利空")):
            val = m7.get(side)
            if isinstance(val, list) and len(val) < MIN_POSITIVE_NEGATIVE:
                issues.append(f"module_7 {label}事件为空，至少需 {MIN_POSITIVE_NEGATIVE} 条（数据不足也应写明'暂无明显{label}事件'）")

    m8 = report.get("module_8_风险ESG")
    if isinstance(m8, dict):
        risks = m8.get("risks")
        if isinstance(risks, list) and len(risks) < MIN_RISKS:
            issues.append(f"module_8 风险点仅 {len(risks)} 个，少于 {MIN_RISKS} 个（core_rules 第 6 条硬性要求）")


def _check_signal_attribution(report: dict, issues: list[str]) -> None:
    """信号归因：权重非负且总和 = 1.0 ± 容差"""
    sa = report.get("signal_attribution")
    if not isinstance(sa, list) or len(sa) == 0:
        return  # 缺失/空集合已在顶层字段检查报过

    total = 0.0
    for i, item in enumerate(sa):
        if not isinstance(item, dict):
            issues.append(f"signal_attribution[{i}] 不是对象")
            continue
        weight = item.get("weight")
        if not isinstance(weight, (int, float)) or isinstance(weight, bool):
            issues.append(f"signal_attribution[{i}]（{item.get('source', '?')}）weight 缺失或非数值")
            continue
        if weight < 0:
            issues.append(f"signal_attribution[{i}]（{item.get('source', '?')}）weight={weight} 为负数")
        total += weight

    if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
        issues.append(f"signal_attribution 权重和={total:.2f}，与 1.0 偏差超过容差 {WEIGHT_SUM_TOLERANCE}")


def _check_consistency(report: dict, issues: list[str]) -> None:
    """score 与 decision 方向一致性（schema 注意 4：≥60 偏乐观，≤40 偏悲观）"""
    score = report.get("score")
    decision = report.get("decision")
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return
    if not isinstance(decision, str):
        return

    if score >= BULLISH_SCORE_FLOOR and decision == "看空":
        issues.append(f"一致性矛盾：score={score}（≥{BULLISH_SCORE_FLOOR} 偏乐观）但 decision=看空")
    elif score <= BEARISH_SCORE_CEIL and decision == "看多":
        issues.append(f"一致性矛盾：score={score}（≤{BEARISH_SCORE_CEIL} 偏悲观）但 decision=看多")


def _check_history_fields(report: dict, issues: list[str]) -> None:
    """E1 v2 历史对比强制校验：has_history=True 时检查 module_9 的 4 个历史字段

    规则（按简报）：
      1. history_compared 必须为 true，缺失或非 true → 违规
      2. history_anchor 非空且为 YYYY-MM-DD 形态 → 否则违规
      3. changed_aspects 必须为 list 且取值 ⊆ {财务面, 股价面, 操作建议} → 否则违规
      4. changed_aspects 非空 ⇔ history_changes 非空 → 不一致违规
    """
    import re as _re

    m9 = report.get("module_9_操作指南")
    if not isinstance(m9, dict):
        issues.append("历史对比校验失败：module_9_操作指南 缺失或非对象")
        return

    # 规则 1：history_compared 必须为 true
    hc = m9.get("history_compared")
    if hc is not True:
        issues.append("历史对比校验失败：history_compared 必须为 true（当前为 {}）".format(repr(hc)))

    # 规则 2：history_anchor 非空且为 YYYY-MM-DD 形态
    anchor = m9.get("history_anchor")
    if not anchor or not isinstance(anchor, str) or not anchor.strip():
        issues.append("历史对比校验失败：history_anchor 缺失或为空")
    elif not _re.match(r"^\d{4}-\d{2}-\d{2}$", anchor.strip()):
        issues.append(f"历史对比校验失败：history_anchor='{anchor}' 不是 YYYY-MM-DD 形态")

    # 规则 3：changed_aspects 必须为 list 且取值 ⊆ 合法集合
    aspects = m9.get("changed_aspects")
    if not isinstance(aspects, list):
        issues.append(f"历史对比校验失败：changed_aspects 必须为 list（当前为 {type(aspects).__name__}）")
    else:
        for i, a in enumerate(aspects):
            if a not in VALID_CHANGED_ASPECTS:
                issues.append(f"历史对比校验失败：changed_aspects[{i}]='{a}' 不在合法取值 {VALID_CHANGED_ASPECTS} 内")

    # 规则 4：changed_aspects 非空 ⇔ history_changes 非空
    changes = m9.get("history_changes")
    aspects_non_empty = isinstance(aspects, list) and len(aspects) > 0
    changes_non_empty = isinstance(changes, list) and len(changes) > 0
    if aspects_non_empty != changes_non_empty:
        issues.append(
            f"历史对比校验失败：changed_aspects 与 history_changes 不一致"
            f"（aspects={len(aspects) if isinstance(aspects, list) else '非list'}条，"
            f"changes={len(changes) if isinstance(changes, list) else '非list'}条）"
        )
