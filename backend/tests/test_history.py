"""E1 历史对比：history.py 采样器与骨架提取测试

采样规则为用户确认的硬性需求（高优先级），边界用例必须全覆盖：
N=0/1/2（全取）→ N=3~5（奇数位）→ N≥6（奇数位封顶 5 份）。
"""
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from stock_agent.history import (
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
    """骨架只含 5 个字段，不含模块全文（控制 token）"""
    report = {
        "score": 66,
        "decision": "震荡",
        "module_1_核心结论": {
            "rating_sentence": "一句话评级",
            "core_logic": ["逻辑1", "逻辑2"],
            "reference_prices": {"support": "5.0"},  # 不进骨架
        },
        "module_3_财务健康": {"profitability": "全文不应进骨架"},
        "signal_attribution": [{"source": "估值面", "weight": 1.0}],
    }
    sk = extract_skeleton(report)
    assert set(sk.keys()) == {"score", "decision", "rating_sentence", "core_logic", "signal_attribution"}
    assert sk["score"] == 66 and sk["decision"] == "震荡"
    assert sk["rating_sentence"] == "一句话评级"
    assert sk["core_logic"] == ["逻辑1", "逻辑2"]
    print("[OK] 骨架字段精确")


def test_extract_skeleton_missing_module1():
    """module_1 缺失/非 dict 时不崩溃"""
    sk = extract_skeleton({"score": 50})
    assert sk["rating_sentence"] == "" and sk["core_logic"] == []
    sk2 = extract_skeleton({"module_1_核心结论": "坏数据"})
    assert sk2["rating_sentence"] == ""
    print("[OK] 骨架提取容错")


# ═══════════════════════════════════════════
# 历史上下文构建
# ═══════════════════════════════════════════

def _fake_row(report_id: int, score: int, decision: str, created_at: str) -> dict:
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
    test_build_context_empty()
    test_build_context_sampling_applied()
    test_build_context_corrupt_rows_skipped()
    print("\n" + "=" * 50)
    print("[OK] All history tests passed")
