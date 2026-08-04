"""E0 质量层：validator.py 语义校验测试

每条硬规则一个违规用例 + 合规基线，确保 validate_report() 的违规清单精准：
不误报（合规报告零违规）、不漏报（每类违规都被抓住）。
"""
import copy
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from stock_agent.core.validator import validate_report, is_collapsed_report


def make_valid_report() -> dict:
    """构造一份完全合规的 9 模块报告基线（权重和恰为 1.0）"""
    return {
        "score": 72,
        "decision": "看多",
        "module_1_核心结论": {
            "rating_sentence": "短期趋势向好但估值偏高，建议观望",
            "core_logic": ["要点1", "要点2", "要点3"],
            "reference_prices": {"support": "5.0元", "resistance": "6.0元"},
        },
        "module_2_公司画像": {
            "business": "靠广告推广和增值服务赚钱",
            "valuation": {"pe_level": "合理", "pb_level": "合理", "analysis": "估值处于历史中位"},
        },
        "module_3_财务健康": {
            "profitability": "增收又增利",
            "key_indicators": [
                {"name": "毛利率", "value": "30%", "trend": "稳定", "verdict": "竞争力稳定"},
                {"name": "ROE", "value": "12%", "trend": "稳定", "verdict": "回报尚可"},
                {"name": "资产负债率", "value": "40%", "trend": "稳定", "verdict": "财务稳健"},
                {"name": "经营现金流/净利润", "value": "1.2", "trend": "稳定", "verdict": "真金白银"},
            ],
            "risk_alerts": ["暂无明显财务风险信号"],
        },
        "module_4_股价走势": {
            "trend": "高位震荡换手充分",
            "capital_flow": {"margin_trading": "融资余额稳定", "main_force": "主力小幅净流入"},
        },
        "module_5_北向资金": {
            "available": True,
            "trend": "北向连续3日净买入",
            "interpretation": "外资逢低布局",
        },
        "module_6_股东筹码": {
            "major_moves": [],  # 空列表合规：确实无增减持
            "chip_analysis": "股东户数减少，筹码趋于集中",
        },
        "module_7_催化舆情": {
            "positive": ["中标3亿大单，业绩有保障"],
            "negative": ["收到监管问询函，需关注"],
            "sentiment": "偏乐观",
            "sentiment_reason": "研报整体正面",
        },
        "module_8_风险ESG": {
            "risk_level": "中",
            "risks": [
                {"type": "市场风险", "level": "中", "desc": "大盘回调风险"},
                {"type": "政策风险", "level": "低", "desc": "行业监管趋严"},
            ],
            "esg": "环保无重大事件，大股东持股稳定",
        },
        "module_9_操作指南": {
            "buy_strategy": "建议分批在5.0-5.3元关注",
            "stop_loss": "跌破4.8元需警惕",
            "take_profit": "5.8-6.0元遇阻可分批止盈",
            "holding_period": {"type": "中短线波段", "reason": "估值修复需要时间"},
        },
        "signal_attribution": [
            {"source": "估值面", "weight": 0.20, "direction": "偏多", "note": "PE 低位"},
            {"source": "财务面", "weight": 0.25, "direction": "偏多", "note": "双增"},
            {"source": "资金面", "weight": 0.15, "direction": "偏空", "note": "流出"},
            {"source": "情绪面", "weight": 0.15, "direction": "中性", "note": "多空交织"},
            {"source": "风险面", "weight": 0.10, "direction": "偏空", "note": "涨幅大"},
            {"source": "筹码面", "weight": 0.15, "direction": "偏多", "note": "集中"},
        ],
    }


# ═══════════════════════════════════════════
# 基线：合规报告零违规
# ═══════════════════════════════════════════

def test_valid_report_passes():
    """完全合规的报告应零违规（防误报）"""
    issues = validate_report(make_valid_report())
    assert issues == [], f"合规报告不应有违规，实际: {issues}"
    print("[OK] 合规基线：零违规")


def test_non_dict_input():
    """非 dict 输入应返回单条兜底违规而非崩溃"""
    assert validate_report("不是 dict") == ["报告不是 JSON 对象，无法校验"]
    assert validate_report(None) == ["报告不是 JSON 对象，无法校验"]
    print("[OK] 非 dict 输入兜底")


# ═══════════════════════════════════════════
# 规则 1：顶层必需字段
# ═══════════════════════════════════════════

def test_missing_top_level_field():
    report = make_valid_report()
    del report["module_9_操作指南"]
    issues = validate_report(report)
    assert any("module_9_操作指南" in i and "缺少" in i for i in issues), f"应报 module_9 缺失: {issues}"
    print("[OK] 顶层字段缺失")


def test_null_top_level_field():
    report = make_valid_report()
    report["score"] = None
    issues = validate_report(report)
    assert any("score" in i and "null" in i for i in issues), f"应报 score 为 null: {issues}"
    print("[OK] 顶层字段 null")


def test_wrong_type_field():
    report = make_valid_report()
    report["signal_attribution"] = "不是列表"
    issues = validate_report(report)
    assert any("signal_attribution" in i and "类型错误" in i for i in issues), f"应报类型错误: {issues}"
    print("[OK] 顶层字段类型错误")


def test_empty_string_field():
    report = make_valid_report()
    report["decision"] = "   "
    issues = validate_report(report)
    assert any("decision" in i and "空字符串" in i for i in issues), f"应报 decision 空字符串: {issues}"
    print("[OK] 顶层字段空字符串")


# ═══════════════════════════════════════════
# 规则 2/3：score 范围与 decision 枚举
# ═══════════════════════════════════════════

def test_score_out_of_range():
    for bad_score in (150, -5):
        report = make_valid_report()
        report["score"] = bad_score
        issues = validate_report(report)
        assert any("score" in i and "超出" in i for i in issues), f"score={bad_score} 应报越界: {issues}"
    print("[OK] score 越界")


def test_decision_not_in_enum():
    report = make_valid_report()
    report["decision"] = "买入"  # 违反 core_rules 第 5 条的典型输出
    issues = validate_report(report)
    assert any("decision" in i and "枚举" in i for i in issues), f"应报 decision 枚举违规: {issues}"
    print("[OK] decision 枚举")


# ═══════════════════════════════════════════
# 规则 4：模块子字段
# ═══════════════════════════════════════════

def test_module_sub_field_missing():
    report = make_valid_report()
    del report["module_1_核心结论"]["rating_sentence"]
    issues = validate_report(report)
    assert any("module_1_核心结论" in i and "rating_sentence" in i for i in issues), f"应报子字段缺失: {issues}"
    print("[OK] 模块子字段缺失")


def test_module_sub_field_empty_string():
    report = make_valid_report()
    report["module_2_公司画像"]["business"] = "  "
    issues = validate_report(report)
    assert any("business" in i and "空字符串" in i for i in issues), f"应报 business 空字符串: {issues}"
    print("[OK] 模块子字段空字符串")


# ═══════════════════════════════════════════
# 规则 5/6/7：模块内数量下限
# ═══════════════════════════════════════════

def test_key_indicators_too_few():
    report = make_valid_report()
    report["module_3_财务健康"]["key_indicators"] = report["module_3_财务健康"]["key_indicators"][:3]
    issues = validate_report(report)
    assert any("key_indicators" in i or "核心财务指标" in i for i in issues), f"应报指标不足 4 项: {issues}"
    print("[OK] module_3 指标少于 4 项")


def test_positive_or_negative_empty():
    for side, label in (("positive", "利好"), ("negative", "利空")):
        report = make_valid_report()
        report["module_7_催化舆情"][side] = []
        issues = validate_report(report)
        assert any(label in i for i in issues), f"应报 module_7 {label}为空: {issues}"
    print("[OK] module_7 利好/利空为空")


def test_risks_too_few():
    report = make_valid_report()
    report["module_8_风险ESG"]["risks"] = report["module_8_风险ESG"]["risks"][:1]
    issues = validate_report(report)
    assert any("风险点" in i for i in issues), f"应报风险点少于 2 个: {issues}"
    print("[OK] module_8 风险点不足 2 个")


# ═══════════════════════════════════════════
# 规则 8：signal_attribution 权重
# ═══════════════════════════════════════════

def test_weight_sum_off():
    report = make_valid_report()
    report["signal_attribution"][0]["weight"] = 0.10  # 总和变成 0.90
    issues = validate_report(report)
    assert any("权重和" in i for i in issues), f"应报权重和偏离: {issues}"
    print("[OK] 权重和偏离 1.0")


def test_weight_sum_within_tolerance():
    """0.04 的偏差在容差内应通过（浮点误差防误报）"""
    report = make_valid_report()
    report["signal_attribution"][0]["weight"] = 0.16  # 总和 0.96，偏差 0.04 < 0.05
    issues = validate_report(report)
    assert not any("权重和" in i for i in issues), f"容差内不应报权重和违规: {issues}"
    print("[OK] 权重和容差内通过")


def test_negative_weight():
    report = make_valid_report()
    report["signal_attribution"][1]["weight"] = -0.25
    issues = validate_report(report)
    assert any("负数" in i for i in issues), f"应报负权重: {issues}"
    print("[OK] 负权重")


def test_weight_not_number():
    report = make_valid_report()
    report["signal_attribution"][2]["weight"] = "0.15"
    issues = validate_report(report)
    assert any("非数值" in i for i in issues), f"应报权重非数值: {issues}"
    print("[OK] 权重非数值")


# ═══════════════════════════════════════════
# 规则 9：score-decision 一致性
# ═══════════════════════════════════════════

def test_consistency_conflict():
    # 高分看空
    report = make_valid_report()
    report["score"], report["decision"] = 80, "看空"
    issues = validate_report(report)
    assert any("一致性矛盾" in i for i in issues), f"80+看空 应报矛盾: {issues}"

    # 低分看多
    report = make_valid_report()
    report["score"], report["decision"] = 30, "看多"
    issues = validate_report(report)
    assert any("一致性矛盾" in i for i in issues), f"30+看多 应报矛盾: {issues}"

    # 边界：60+看空 / 40+看多 同样矛盾（≥60 偏乐观，≤40 偏悲观）
    report = make_valid_report()
    report["score"], report["decision"] = 60, "看空"
    assert any("一致性矛盾" in i for i in validate_report(report)), "60+看空 边界应报矛盾"
    print("[OK] score-decision 一致性矛盾")


def test_consistency_ok():
    """中间地带与震荡判断不应误报"""
    for score, decision in ((72, "震荡"), (50, "看多"), (50, "看空"), (45, "震荡")):
        report = make_valid_report()
        report["score"], report["decision"] = score, decision
        issues = validate_report(report)
        assert not any("一致性矛盾" in i for i in issues), f"score={score}+{decision} 不应报矛盾: {issues}"
    print("[OK] 一致性合规不误报")


# ═══════════════════════════════════════════
# 多违规累积
# ═══════════════════════════════════════════

def test_multiple_issues_accumulate():
    """多处违规应全部列出（供 LLM 一次性定点修正）"""
    report = make_valid_report()
    del report["module_9_操作指南"]
    report["score"] = 999
    report["decision"] = "买入"
    issues = validate_report(report)
    assert len(issues) >= 3, f"应至少 3 条违规，实际 {len(issues)}: {issues}"
    print(f"[OK] 多违规累积：{len(issues)} 条")


# ═══════════════════════════════
# 结构坍塌判定（偶发空报告门关）
# ═══════════════════════════════

def test_collapsed_fragment_detected():
    """思考文字里救出的草稿残片（单个风险点对象）应判坍塌"""
    fragment = {"type": "估值陷阱", "level": "高", "desc": "PE 1852倍..."}
    assert is_collapsed_report(fragment) is True
    print("[OK] 坍塌判定：草稿残片")


def test_collapsed_missing_score_or_decision():
    """缺 score 或 decision → 坍塌"""
    r1 = make_valid_report()
    del r1["score"]
    r2 = make_valid_report()
    del r2["decision"]
    assert is_collapsed_report(r1) is True
    assert is_collapsed_report(r2) is True
    print("[OK] 坍塌判定：缺 score/decision")


def test_collapsed_modules_threshold():
    """9 大模块在场少于 6 个 → 坍塌；6 个及以上 → 不坍塌（小违规走校验流程）"""
    r = make_valid_report()
    for key in ("module_5_北向资金", "module_6_股东筹码", "module_7_催化舆情", "module_8_风险ESG"):
        del r[key]  # 剩 5 个模块 → 坍塌
    assert is_collapsed_report(r) is True

    r2 = make_valid_report()
    del r2["module_9_操作指南"]  # 剩 8 个 → 不坍塌
    assert is_collapsed_report(r2) is False
    print("[OK] 坍塌判定：模块数量阈值")


def test_collapsed_non_dict():
    """非 dict 输入应判坍塌（不崩溃）"""
    assert is_collapsed_report("不是 dict") is True
    assert is_collapsed_report(None) is True
    print("[OK] 坍塌判定：非 dict 兜底")


# ═══════════════════════════════════════════
# E1 v2：历史对比字段校验（has_history=True）
# ═══════════════════════════════════════════

def make_valid_report_with_history() -> dict:
    """构造一份含历史对比字段的合规报告（has_history=True 基线）"""
    r = make_valid_report()
    r["module_9_操作指南"]["history_anchor"] = "2026-07-20"
    r["module_9_操作指南"]["history_compared"] = True
    r["module_9_操作指南"]["changed_aspects"] = ["财务面", "股价面"]
    r["module_9_操作指南"]["history_changes"] = [
        "毛利率从 45% 降至 38%，2026-07-20 报告为 45%，建议下调盈利预期",
        "股价从 5.2 涨至 6.1，2026-07-20 为 5.2，趋势向上",
    ]
    return r


def test_history_passes_when_has_history_true():
    """has_history=True 时，合规历史字段应零违规"""
    r = make_valid_report_with_history()
    issues = validate_report(r, has_history=True)
    assert issues == [], f"合规历史字段不应违规，实际: {issues}"
    print("[OK] 历史对比基线：has_history=True 零违规")


def test_history_skipped_when_has_history_false():
    """has_history=False 时，即使历史字段缺失也不检查"""
    r = make_valid_report()
    # module_9 不含任何历史字段
    issues = validate_report(r, has_history=False)
    assert not any("历史对比" in i for i in issues), f"has_history=False 不应报历史违规: {issues}"
    print("[OK] 历史对比：has_history=False 跳过历史字段检查")


def test_history_compared_missing_or_not_true():
    """history_compared 缺失或非 true → 违规"""
    # 场景1：缺失
    r = make_valid_report_with_history()
    del r["module_9_操作指南"]["history_compared"]
    issues = validate_report(r, has_history=True)
    assert any("history_compared" in i for i in issues), f"缺失 history_compared 应违规: {issues}"

    # 场景2：false
    r2 = make_valid_report_with_history()
    r2["module_9_操作指南"]["history_compared"] = False
    issues2 = validate_report(r2, has_history=True)
    assert any("history_compared" in i for i in issues2), f"history_compared=False 应违规: {issues2}"

    # 场景3：None
    r3 = make_valid_report_with_history()
    r3["module_9_操作指南"]["history_compared"] = None
    issues3 = validate_report(r3, has_history=True)
    assert any("history_compared" in i for i in issues3), f"history_compared=None 应违规: {issues3}"
    print("[OK] 历史对比：history_compared 缺失/非 true → 违规")


def test_history_anchor_invalid():
    """history_anchor 缺失或非 YYYY-MM-DD → 违规"""
    # 场景1：缺失
    r = make_valid_report_with_history()
    del r["module_9_操作指南"]["history_anchor"]
    issues = validate_report(r, has_history=True)
    assert any("history_anchor" in i for i in issues), f"缺失 history_anchor 应违规: {issues}"

    # 场景2：非日期格式
    r2 = make_valid_report_with_history()
    r2["module_9_操作指南"]["history_anchor"] = "昨天"
    issues2 = validate_report(r2, has_history=True)
    assert any("history_anchor" in i for i in issues2), f"非法 history_anchor 应违规: {issues2}"

    # 场景3：空字符串
    r3 = make_valid_report_with_history()
    r3["module_9_操作指南"]["history_anchor"] = ""
    issues3 = validate_report(r3, has_history=True)
    assert any("history_anchor" in i for i in issues3), f"empty history_anchor 应违规: {issues3}"
    print("[OK] 历史对比：history_anchor 格式校验")


def test_changed_aspects_out_of_bounds():
    """changed_aspects 取值越界 → 违规"""
    r = make_valid_report_with_history()
    r["module_9_操作指南"]["changed_aspects"] = ["财务面", "技术面"]  # 技术面不合法
    issues = validate_report(r, has_history=True)
    assert any("技术面" in i for i in issues), f"越界 changed_aspects 应违规: {issues}"
    print("[OK] 历史对比：changed_aspects 取值越界 → 违规")


def test_changed_aspects_not_list():
    """changed_aspects 非 list → 违规"""
    r = make_valid_report_with_history()
    r["module_9_操作指南"]["changed_aspects"] = "财务面"  # 字符串而非列表
    issues = validate_report(r, has_history=True)
    assert any("changed_aspects" in i and "list" in i for i in issues), f"非 list 应违规: {issues}"
    print("[OK] 历史对比：changed_aspects 非 list → 违规")


def test_changed_aspects_history_changes_inconsistent():
    """changed_aspects 非空但 history_changes 空 → 违规"""
    r = make_valid_report_with_history()
    r["module_9_操作指南"]["changed_aspects"] = ["财务面"]
    r["module_9_操作指南"]["history_changes"] = []
    issues = validate_report(r, has_history=True)
    assert any("不一致" in i for i in issues), f"aspects 非空 changes 空应违规: {issues}"

    # 反向：changed_aspects 空但 history_changes 非空
    r2 = make_valid_report_with_history()
    r2["module_9_操作指南"]["changed_aspects"] = []
    r2["module_9_操作指南"]["history_changes"] = ["某变化"]
    issues2 = validate_report(r2, has_history=True)
    assert any("不一致" in i for i in issues2), f"aspects 空 changes 非空应违规: {issues2}"
    print("[OK] 历史对比：changed_aspects 与 history_changes 不一致 → 违规")


def test_history_both_empty_consistent():
    """changed_aspects 与 history_changes 均为空时不应报不一致"""
    r = make_valid_report_with_history()
    r["module_9_操作指南"]["changed_aspects"] = []
    r["module_9_操作指南"]["history_changes"] = []
    issues = validate_report(r, has_history=True)
    assert not any("不一致" in i for i in issues), f"双方均为空不应报不一致: {issues}"
    print("[OK] 历史对比：双方均为空一致通过")


if __name__ == "__main__":
    print("=" * 50)
    print("E0: validator.py 语义校验测试")
    print("=" * 50)
    test_valid_report_passes()
    test_non_dict_input()
    test_missing_top_level_field()
    test_null_top_level_field()
    test_wrong_type_field()
    test_empty_string_field()
    test_score_out_of_range()
    test_decision_not_in_enum()
    test_module_sub_field_missing()
    test_module_sub_field_empty_string()
    test_key_indicators_too_few()
    test_positive_or_negative_empty()
    test_risks_too_few()
    test_weight_sum_off()
    test_weight_sum_within_tolerance()
    test_negative_weight()
    test_weight_not_number()
    test_consistency_conflict()
    test_consistency_ok()
    test_multiple_issues_accumulate()
    test_collapsed_fragment_detected()
    test_collapsed_missing_score_or_decision()
    test_collapsed_modules_threshold()
    test_collapsed_non_dict()
    # E1 v2 历史对比
    test_history_passes_when_has_history_true()
    test_history_skipped_when_has_history_false()
    test_history_compared_missing_or_not_true()
    test_history_anchor_invalid()
    test_changed_aspects_out_of_bounds()
    test_changed_aspects_not_list()
    test_changed_aspects_history_changes_inconsistent()
    test_history_both_empty_consistent()
    print("\n" + "=" * 50)
    print("[OK] All validator tests passed")
