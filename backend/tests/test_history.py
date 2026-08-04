"""E1 历史对比：history.py 采样器与骨架提取测试

采样规则为用户确认的硬性需求（高优先级），边界用例必须全覆盖：
N=0/1/2（全取）→ N=3~5（奇数位）→ N≥6（奇数位封顶 5 份）。
"""
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from stock_agent.core.history import (
    sample_history_indices,
    extract_skeleton,
    build_history_context,
)


# ═══════════════════════════════════════════
# 采样规则（用户确认，边界全覆盖）
# ═══════════════════════════════════════════

def test_sample_indices_zero():
    assert sample_history_indices(0) == []
    assert sample_history_indices(-3) == []  # 防御性：负数同 0
    print("[OK] N=0/负数 → 空")


def test_sample_indices_small_takes_all():
    """N≤2：全取最近 N 份（连续序号）"""
    assert sample_history_indices(1) == [1]
    assert sample_history_indices(2) == [1, 2]
    print("[OK] N≤2 全取")


def test_sample_indices_odd_positions():
    """N=3~5：取奇数位 [1,3,5]（缺位自然截断）"""
    assert sample_history_indices(3) == [1, 3]
    assert sample_history_indices(4) == [1, 3]
    assert sample_history_indices(5) == [1, 3, 5]
    print("[OK] N=3~5 奇数位")


def test_sample_indices_large_capped():
    """N≥6：奇数位序列最多 5 份 [1,3,5,7,9]"""
    assert sample_history_indices(6) == [1, 3, 5]       # 第 7 位不存在
    assert sample_history_indices(7) == [1, 3, 5, 7]
    assert sample_history_indices(9) == [1, 3, 5, 7, 9]
    assert sample_history_indices(10) == [1, 3, 5, 7, 9]
    assert sample_history_indices(100) == [1, 3, 5, 7, 9]  # 封顶 5 份
    print("[OK] N≥6 奇数位封顶 5 份")


# ═══════════════════════════════════════════
# 骨架提取
# ═══════════════════════════════════════════

def test_extract_skeleton_fields():
    """骨架含 7 个字段（score/decision/rating_sentence/core_logic/
    financials/price_trend/advice），不含 signal_attribution"""
    report = {
        "score": 66,
        "decision": "震荡",
        "module_1_核心结论": {
            "rating_sentence": "一句话评级",
            "core_logic": ["逻辑1", "逻辑2"],
            "reference_prices": {"support": "5.0"},  # 不进骨架
        },
        "module_3_财务健康": {
            "key_indicators": [
                {"name": "毛利率", "value": "45%", "trend": "稳定", "verdict": "还行"},
                {"name": "ROE", "value": "12%", "trend": "上升", "verdict": "不错"},
            ]
        },
        "module_4_股价走势": {"trend": "放量上涨"},
        "module_9_操作指南": {
            "buy_strategy": "分批建仓",
            "stop_loss": "跌破5元止损",
            "take_profit": "6元止盈",
        },
        "signal_attribution": [{"source": "估值面", "weight": 1.0}],  # 不再提取
    }
    sk = extract_skeleton(report)
    assert set(sk.keys()) == {
        "score", "decision", "rating_sentence", "core_logic",
        "financials", "price_trend", "advice",
    }
    assert sk["score"] == 66 and sk["decision"] == "震荡"
    assert sk["rating_sentence"] == "一句话评级"
    assert sk["core_logic"] == ["逻辑1", "逻辑2"]
    # 新字段
    assert sk["financials"] == [
        {"name": "毛利率", "value": "45%", "trend": "稳定"},
        {"name": "ROE", "value": "12%", "trend": "上升"},
    ]
    assert sk["price_trend"] == "放量上涨"
    assert sk["advice"] == {
        "buy_strategy": "分批建仓",
        "stop_loss": "跌破5元止损",
        "take_profit": "6元止盈",
    }
    # signal_attribution 不再出现
    assert "signal_attribution" not in sk
    print("[OK] 骨架字段精确（7 字段，无 signal_attribution）")


def test_extract_skeleton_missing_module1():
    """module_1 缺失/非 dict 时不崩溃"""
    sk = extract_skeleton({"score": 50})
    assert sk["rating_sentence"] == "" and sk["core_logic"] == []
    sk2 = extract_skeleton({"module_1_核心结论": "坏数据"})
    assert sk2["rating_sentence"] == ""
    print("[OK] 骨架提取容错")


def test_extract_skeleton_missing_new_modules():
    """module_3/4/9 缺失时新字段返回空值，不崩溃"""
    sk = extract_skeleton({"score": 50, "module_1_核心结论": {}})
    assert sk["financials"] == []
    assert sk["price_trend"] == ""
    assert sk["advice"] == {}
    # 坏类型也不崩溃
    sk2 = extract_skeleton({
        "score": 50,
        "module_3_财务健康": "坏数据",
        "module_4_股价走势": 123,
        "module_9_操作指南": None,
    })
    assert sk2["financials"] == []
    assert sk2["price_trend"] == ""
    assert sk2["advice"] == {}
    print("[OK] 新模块缺失/坏类型容错")


# ═══════════════════════════════════════════
# 历史上下文构建
# ═══════════════════════════════════════════

def _fake_row(report_id: int, score: int, decision: str, created_at: str,
              with_new_modules: bool = False) -> dict:
    """模拟 database.get_recent_reports 的一行"""
    report = {
        "score": score,
        "decision": decision,
        "module_1_核心结论": {
            "rating_sentence": f"评级{report_id}",
            "core_logic": [f"逻辑{report_id}"],
        },
        "signal_attribution": [],
    }
    if with_new_modules:
        report["module_3_财务健康"] = {
            "key_indicators": [
                {"name": "毛利率", "value": f"{40+report_id}%", "trend": "稳定", "verdict": "还行"},
            ]
        }
        report["module_4_股价走势"] = {"trend": f"走势{report_id}"}
        report["module_9_操作指南"] = {
            "buy_strategy": f"建仓{report_id}",
            "stop_loss": f"止损{report_id}",
            "take_profit": f"止盈{report_id}",
        }
    return {
        "id": report_id,
        "stock_code": "600519",
        "created_at": created_at,
        "report_json": json.dumps(report, ensure_ascii=False),
    }


def test_build_context_empty():
    assert build_history_context([]) == ""
    print("[OK] 无历史 → 空串")


def test_build_context_sampling_applied():
    """7 行历史 → 按 [1,3,5,7] 采样，第 2/4/6 份不出现"""
    rows = [_fake_row(i, 50 + i, "震荡", f"2026-07-{i:02d}") for i in range(1, 8)]  # 倒序：1 最新
    ctx = build_history_context(rows)
    assert "评级1" in ctx and "评级3" in ctx and "评级5" in ctx and "评级7" in ctx
    assert "评级2" not in ctx and "评级4" not in ctx and "评级6" not in ctx
    assert "历史报告回顾" in ctx
    print("[OK] 上下文按采样规则构建")


def test_build_context_corrupt_rows_skipped():
    """坏 JSON 行跳过，其余历史正常构建"""
    rows = [
        _fake_row(1, 70, "看多", "2026-07-20"),
        {"id": 2, "created_at": "2026-07-19", "report_json": "{坏 JSON"},
        _fake_row(3, 60, "震荡", "2026-07-18"),
    ]
    ctx = build_history_context(rows)
    assert "评级1" in ctx and "评级3" in ctx
    print("[OK] 坏行跳过不崩溃")


def test_build_context_new_blocks_rendered():
    """新增三块：财务指标、股价走势、历史操作 均正确渲染"""
    rows = [
        _fake_row(1, 70, "看多", "2026-07-20", with_new_modules=True),
    ]
    ctx = build_history_context(rows)
    # 财务指标
    assert "财务指标：" in ctx
    assert "- 毛利率：41%（稳定）" in ctx
    # 股价走势
    assert "股价走势：走势1" in ctx
    # 历史操作
    assert "历史操作：" in ctx
    assert "- 建仓策略：建仓1" in ctx
    assert "- 止损参考：止损1" in ctx
    assert "- 止盈参考：止盈1" in ctx
    print("[OK] 新三块渲染正确")


def test_build_context_missing_modules_no_render():
    """旧报告缺模块/字段为空时对应块不渲染，不报错"""
    rows = [
        _fake_row(1, 70, "看多", "2026-07-20", with_new_modules=False),
    ]
    ctx = build_history_context(rows)
    assert "财务指标：" not in ctx
    assert "股价走势：" not in ctx
    assert "历史操作：" not in ctx
    assert "评级1" in ctx  # 基础块仍存在
    print("[OK] 缺模块不渲染不报错")


if __name__ == "__main__":
    print("=" * 50)
    print("E1: history.py 采样与骨架测试")
    print("=" * 50)
    test_sample_indices_zero()
    test_sample_indices_small_takes_all()
    test_sample_indices_odd_positions()
    test_sample_indices_large_capped()
    test_extract_skeleton_fields()
    test_extract_skeleton_missing_module1()
    test_extract_skeleton_missing_new_modules()
    test_build_context_empty()
    test_build_context_sampling_applied()
    test_build_context_corrupt_rows_skipped()
    test_build_context_new_blocks_rendered()
    test_build_context_missing_modules_no_render()
    print("\n" + "=" * 50)
    print("[OK] All history tests passed")
