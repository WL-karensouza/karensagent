"""E4 生产化 TDD 测试（测试先行，RED→GREEN）

覆盖生产化新增行为：
  1. 进度回调（on_progress 各阶段按序上报）
  2. 历史记忆注入（stock_code → 自动载入 E1 历史骨架）
  3. 故障边界（千问失败 → 抛出供调用方降级）
  4. 降级入口 debate_with_fallback（正常走辩论 / 失败静默降级）
  5. 降级后仍保留 E1 历史记忆
  6. StockReport 表 debate_stats 字段
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).parent))

from test_validator import make_valid_report

USAGE = {"prompt": 100, "completion": 100, "total": 200, "finish_reason": "stop"}


def _mock_llm_for_consensus(report):
    """构造 _call_llm mock：B 报告 + writer 合并报告（双方一致 → 0 轮共识，仅 2 次调用）"""
    return [
        (json.dumps(report, ensure_ascii=False), dict(USAGE)),  # 顾问B完整报告
        (json.dumps(report, ensure_ascii=False), dict(USAGE)),  # writer 合并报告
    ]


# ═══════════════════════════════════════════
# 1. 进度回调
# ═══════════════════════════════════════════

def test_debate_progress_stages_in_order():
    """debate_analyze(on_progress=...) 应按序上报 advisor_a → advisor_b → merge 阶段"""
    import stock_agent.debate as D
    report = make_valid_report()
    stages = []

    with patch("stock_agent.analyze.analyze", return_value=(report, dict(USAGE))), \
         patch("stock_agent.debate._call_llm", side_effect=_mock_llm_for_consensus(report)):
        D.debate_analyze("## 数据报告\n测试数据", on_progress=lambda stage, info=None: stages.append(stage))

    assert "advisor_a" in stages, f"应有 advisor_a 阶段，实际 {stages}"
    assert "advisor_b" in stages, f"应有 advisor_b 阶段，实际 {stages}"
    assert "merge" in stages, f"应有 merge 阶段，实际 {stages}"
    assert stages.index("advisor_a") < stages.index("advisor_b") < stages.index("merge"), \
        f"阶段顺序应为 advisor_a < advisor_b < merge，实际 {stages}"
    print("[OK] 进度回调阶段与顺序")


# ═══════════════════════════════════════════
# 2. 历史记忆注入
# ═══════════════════════════════════════════

def test_debate_history_injection_via_stock_code():
    """传 stock_code 时应自动载入 E1 历史骨架并注入顾问A 的分析 prompt"""
    import stock_agent.debate as D
    report = make_valid_report()
    history_row = {"id": 1, "stock_code": "600519", "created_at": "2026-07-01 10:00:00",
                   "report_json": json.dumps(make_valid_report(), ensure_ascii=False)}
    analyze_calls = []

    def fake_analyze(md, history_context=""):
        analyze_calls.append(history_context)
        return report, dict(USAGE)

    with patch("stock_agent.analyze.analyze", side_effect=fake_analyze), \
         patch("database.get_recent_reports", return_value=[history_row]), \
         patch("stock_agent.debate._call_llm", side_effect=_mock_llm_for_consensus(report)):
        D.debate_analyze("## 数据报告\n测试数据", stock_code="600519")

    assert len(analyze_calls) == 1
    assert "历史报告回顾" in analyze_calls[0], "历史骨架应注入顾问A 分析（含'历史报告回顾'标记）"
    print("[OK] 历史记忆自动注入")


# ═══════════════════════════════════════════
# 3. 故障边界
# ═══════════════════════════════════════════

def test_debate_qwen_failure_raises_for_fallback():
    """千问调用失败时 debate_analyze 应抛出异常（交由调用方降级），不得吞掉"""
    import stock_agent.debate as D
    report = make_valid_report()

    with patch("stock_agent.analyze.analyze", return_value=(report, dict(USAGE))), \
         patch("stock_agent.debate._call_llm", side_effect=RuntimeError("qwen endpoint down")):
        try:
            D.debate_analyze("## 数据报告\n测试数据")
            assert False, "千问失败应抛出异常"
        except RuntimeError as e:
            assert "qwen" in str(e)
    print("[OK] 千问故障向上抛出")


# ═══════════════════════════════════════════
# 4. 降级入口 debate_with_fallback
# ═══════════════════════════════════════════

def test_fallback_returns_debate_when_ok():
    """辩论链路健康时 debate_with_fallback 返回辩论结果（stats 非空）"""
    from stock_agent.debate import debate_with_fallback
    report = make_valid_report()
    stats = {"rounds": 0, "consensus": True}

    with patch("stock_agent.debate.debate_analyze", return_value=(report, dict(USAGE), stats)):
        r, u, s = debate_with_fallback("数据报告", "600519")

    assert s is stats, "正常时应返回辩论 stats"
    assert r is report
    print("[OK] 正常走辩论")


def test_fallback_silent_to_standard():
    """辩论链路失败时静默降级标准分析：返回标准报告且 stats=None（不抛异常）"""
    from stock_agent.debate import debate_with_fallback
    report = make_valid_report()

    with patch("stock_agent.debate.debate_analyze", side_effect=RuntimeError("debate down")), \
         patch("database.get_recent_reports", return_value=[]), \
         patch("stock_agent.analyze.analyze", return_value=(report, dict(USAGE))):
        r, u, s = debate_with_fallback("数据报告", "600519")

    assert s is None, "降级时 stats 应为 None（前端角标据此不显示）"
    assert r is report, "应返回标准分析的报告"
    print("[OK] 静默降级标准分析")


def test_fallback_keeps_history_memory():
    """降级回标准分析时仍保留 E1 历史记忆（历史骨架照常注入）"""
    from stock_agent.debate import debate_with_fallback
    report = make_valid_report()
    history_row = {"id": 1, "stock_code": "600519", "created_at": "2026-07-01 10:00:00",
                   "report_json": json.dumps(make_valid_report(), ensure_ascii=False)}
    analyze_calls = []

    def fake_analyze(md, history_context=""):
        analyze_calls.append(history_context)
        return report, dict(USAGE)

    with patch("stock_agent.debate.debate_analyze", side_effect=RuntimeError("debate down")), \
         patch("database.get_recent_reports", return_value=[history_row]), \
         patch("stock_agent.analyze.analyze", side_effect=fake_analyze):
        debate_with_fallback("数据报告", "600519")

    assert len(analyze_calls) == 1
    assert "历史报告回顾" in analyze_calls[0], "降级后历史记忆仍应注入"
    print("[OK] 降级保留历史记忆")


# ═══════════════════════════════════════════
# 6. DB 字段
# ═══════════════════════════════════════════

def test_stock_report_has_debate_stats_column():
    """StockReport 表应有 debate_stats 字段（可空，标准分析/降级时为 null）"""
    from models import StockReport

    assert hasattr(StockReport, "debate_stats"), "StockReport 缺少 debate_stats 字段"
    obj = StockReport(debate_stats='{"rounds": 0, "consensus": true}')
    assert obj.debate_stats == '{"rounds": 0, "consensus": true}'
    print("[OK] debate_stats 字段")


if __name__ == "__main__":
    print("=" * 50)
    print("E4 生产化 TDD 测试")
    print("=" * 50)
    test_debate_progress_stages_in_order()
    test_debate_history_injection_via_stock_code()
    test_debate_qwen_failure_raises_for_fallback()
    test_fallback_returns_debate_when_ok()
    test_fallback_silent_to_standard()
    test_fallback_keeps_history_memory()
    test_stock_report_has_debate_stats_column()
    print("\n" + "=" * 50)
    print("[OK] All E4 production TDD tests passed")
