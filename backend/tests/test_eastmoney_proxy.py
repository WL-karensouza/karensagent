"""东财 HTTP 代理绕过 TDD：国内 API 不得走系统代理

根因：用户环境全局代理（127.0.0.1:17891，GitHub 加速用）宕掉时，
requests 默认信任系统代理 → 东财调用 ProxyError → 简称查询全挂 →
summary 降级代码格式 → 部分股票被 iFinD 拒 → critical 门硬终止。
东财是境内服务，必须显式绕过系统代理。
"""
import sys
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND))


class _FakeResp:
    def json(self):
        return {"data": {"f57": "600519", "f58": "贵州茅台"}}


def test_get_name_bypasses_system_proxy():
    """_get_name_eastmoney 必须绕过系统代理（代理宕掉时国内 API 仍可用）"""
    from stock_agent.datasources import eastmoney as em
    captured = {}

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return _FakeResp()

    with patch("stock_agent.datasources.eastmoney.requests.get", side_effect=fake_get):
        name = em._get_name_eastmoney("600519")

    assert name == "贵州茅台"
    assert captured.get("proxies") == {"http": None, "https": None}, \
        f"应显式绕过系统代理，实际 proxies={captured.get('proxies')}"
    assert "Mozilla" in str(captured.get("headers", {}).get("User-Agent", "")), \
        "应伪装浏览器 UA（东财会掐断 python-requests 默认 UA 的连接）"
    print("[OK] 查名接口绕过系统代理 + 浏览器 UA")


def test_get_name_retries_on_connection_error():
    """东财间歇性掐断连接时，应重试最多 3 次（不因单次断连判失败）"""
    from stock_agent.datasources import eastmoney as em
    import requests as _rq
    calls = []

    def flaky_get(url, **kwargs):
        calls.append(1)
        if len(calls) < 3:
            raise _rq.exceptions.ConnectionError("RemoteDisconnected")
        return _FakeResp()

    with patch("stock_agent.datasources.eastmoney.requests.get", side_effect=flaky_get):
        name = em._get_name_eastmoney("600519")

    assert name == "贵州茅台", f"重试后应返回名称，实际: {name}"
    assert len(calls) == 3, f"应重试到第 3 次成功，实际调用 {len(calls)} 次"
    print("[OK] 东财掐断连接自动重试")


def test_fetch_ohlcv_bypasses_system_proxy():
    """_fetch_ohlcv_eastmoney 同样必须绕过系统代理"""
    from stock_agent.datasources import eastmoney as em
    captured = {}

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        raise __import__("requests").exceptions.RequestException("stop here")

    with patch("stock_agent.datasources.eastmoney.requests.get", side_effect=fake_get):
        em._fetch_ohlcv_eastmoney("600519")  # 抛 RequestException 会被吞掉返回 None，无所谓

    assert captured.get("proxies") == {"http": None, "https": None}, \
        f"应显式绕过系统代理，实际 proxies={captured.get('proxies')}"
    assert "Mozilla" in str(captured.get("headers", {}).get("User-Agent", "")), \
        "应伪装浏览器 UA（东财会掐断 python-requests 默认 UA 的连接）"
    print("[OK] K线接口绕过系统代理 + 浏览器 UA")
