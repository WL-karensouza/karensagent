"""技术指标计算测试

测试目标:
  1. 窗口函数（MA/BOLL）对 None 缺口不抛 TypeError
  2. 全 None 窗口返回 None 而不是崩溃
  3. 正常数据结果正确性不受防御逻辑影响
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def test_calc_ma_normal():
    from stock_agent.skill.indicators import _calc_ma
    out = _calc_ma([1.0, 2.0, 3.0, 4.0, 5.0], 3)
    assert out[:2] == [None, None]
    assert out[2] == 2.0
    assert out[4] == 4.0


def test_calc_ma_with_none_gap():
    """价格序列含 None 缺口时窗口取有效值平均，不抛 TypeError"""
    from stock_agent.skill.indicators import _calc_ma
    out = _calc_ma([1.0, None, 3.0, 4.0, 5.0], 3)
    assert len(out) == 5
    # 窗口 [None, 3.0, 4.0] → 有效值平均 3.5
    assert out[3] == 3.5
    # 窗口 [3.0, 4.0, 5.0] → 4.0
    assert out[4] == 4.0


def test_calc_ma_all_none_window():
    from stock_agent.skill.indicators import _calc_ma
    out = _calc_ma([None, None, None], 2)
    assert out == [None, None, None]


def test_calc_boll_with_none_gap():
    """BOLL 窗口含 None 时不崩，有效值不足时该点为 None"""
    from stock_agent.skill.indicators import _calc_boll
    closes = [10.0, None, 10.5, 11.0, 10.8, 10.9, 11.1, 10.7,
              10.6, 10.8, 11.0, 10.9, 10.8, 11.2, 11.3, 11.1,
              10.9, 10.8, 11.0, 11.1]
    out = _calc_boll(closes, 20)
    assert len(out["upper"]) == 20
    assert out["middle"][19] is not None  # 末点窗口有效值足够


def test_calc_kdj_none_fallback_unchanged():
    """KDJ 对 highs/lows 含 None 的回退行为保持原样"""
    from stock_agent.skill.indicators import _calc_kdj
    closes = [float(10 + i % 3) for i in range(15)]
    highs = [c + 0.5 if i % 4 else None for i, c in enumerate(closes)]
    lows = [c - 0.5 if i % 5 else None for i, c in enumerate(closes)]
    out = _calc_kdj(highs, lows, closes, 9)
    assert out["k"][14] is not None
    assert out["d"][14] is not None
