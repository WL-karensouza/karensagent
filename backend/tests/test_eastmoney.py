"""东方财富数据源防御性测试

测试目标:
  1. 纯后缀/空代码不抛 IndexError（守卫在 HTTP 之前，测试不走网络）
  2. secid 构造逻辑正确
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def test_get_name_empty_code_guard():
    """'.SH' 剥后缀为空，应返回 None 而不是 IndexError"""
    from stock_agent.datasources.eastmoney import _get_name_eastmoney

    assert _get_name_eastmoney(".SH") is None
    assert _get_name_eastmoney(".SZ") is None
    assert _get_name_eastmoney("   ") is None


def test_fetch_ohlcv_empty_code_guard():
    from stock_agent.datasources.eastmoney import _fetch_ohlcv_eastmoney

    assert _fetch_ohlcv_eastmoney(".SH") is None
    assert _fetch_ohlcv_eastmoney("") is None


def test_hk_code_zfill(monkeypatch):
    """港股 secid 应为 116.{5位补零}，且走港股分支不受 A 股守卫影响"""
    import stock_agent.datasources.eastmoney as em

    captured = {}

    class FakeResp:
        def json(self):
            return {"data": {"f58": "美图公司"}}

    def fake_get(url, params=None, timeout=None):
        captured["params"] = params
        return FakeResp()

    monkeypatch.setattr(em.requests, "get", fake_get)
    name = em._get_name_eastmoney("2513.HK")
    assert name == "美图公司"
    assert captured["params"]["secid"] == "116.02513"
