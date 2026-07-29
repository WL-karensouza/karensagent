"""skill/report.py 纯函数单元测试

测试目标:
  1. _market_suffix 各市场后缀正确
  2. 港股代码误调用后缀函数时快速失败（而非静默拼出错误后缀）
"""
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def test_market_suffix_sh():
    from stock_agent.skill.report import _market_suffix
    assert _market_suffix("600519") == ".SH"
    assert _market_suffix("688981") == ".SH"


def test_market_suffix_sz():
    from stock_agent.skill.report import _market_suffix
    assert _market_suffix("000858") == ".SZ"
    assert _market_suffix("002415") == ".SZ"  # 002 前缀由 00 覆盖
    assert _market_suffix("003032") == ".SZ"  # 003 前缀由 00 覆盖
    assert _market_suffix("300750") == ".SZ"


def test_market_suffix_bj():
    from stock_agent.skill.report import _market_suffix
    assert _market_suffix("830799") == ".BJ"
    assert _market_suffix("430047") == ".BJ"


def test_market_suffix_hk_raises():
    """港股应走 global_stock 服务（query_tpl 分支），后缀函数被误调用时必须大声报错"""
    from stock_agent.skill.report import _market_suffix
    with pytest.raises(ValueError):
        _market_suffix("2513.HK")