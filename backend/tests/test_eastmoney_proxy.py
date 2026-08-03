"""东财 HTTP 通道 TDD：专用 session（trust_env=False）+ 浏览器 UA + 重试

根因链：
  1. requests 默认信任系统代理（含 Windows 注册表代理）→ 用户全局代理宕掉时 ProxyError；
     proxies={"http": None} 只能盖 http/https，注册表里的 ftp 等条目仍会漏进来，不彻底；
     trust_env=False 才是完全绕过。
  2. 东财 UA 检测：python-requests 默认 UA 被服务端直接掐断（RemoteDisconnected），必须伪装浏览器。
  3. 东财对部分 IP 间歇性掐断连接：重试最多 3 次。
"""
import sys
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND))


class _FakeResp:
    def json(self):
        return {"data": {"f57": "600519", "f58": "贵州茅台"}}


def test_session_trust_env_disabled():
    """东财专用 session 必须 trust_env=False（完全绕过系统/注册表代理）"""
    from stock_agent.datasources import eastmoney as em
    assert em._session.trust_env is False, "东财 session 必须禁用环境代理信任"
    assert "Mozilla" in em._session.headers.get("User-Agent", ""), \
        "session 默认 UA 必须是浏览器（东财掐 python-requests 默认 UA）"
    print("[OK] 专用 session：trust_env=False + 浏览器 UA")


def test_get_name_uses_dedicated_session():
    """查名走专用 session，返回简称"""
    from stock_agent.datasources import eastmoney as em
    captured = {}

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return _FakeResp()

    with patch.object(em._session, "get", side_effect=fake_get):
        name = em._get_name_eastmoney("600519")

    assert name == "贵州茅台"
    print("[OK] 查名走专用 session")


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

    with patch.object(em._session, "get", side_effect=flaky_get), \
         patch.object(em.time, "sleep"):
        name = em._get_name_eastmoney("600519")

    assert name == "贵州茅台", f"重试后应返回名称，实际: {name}"
    assert len(calls) == 3, f"应重试到第 3 次成功，实际调用 {len(calls)} 次"
    print("[OK] 东财掐断连接自动重试")


def test_fetch_ohlcv_uses_dedicated_session():
    """K线同样走专用 session（trust_env=False + 浏览器 UA 由 session 承载）"""
    from stock_agent.datasources import eastmoney as em
    import requests as _rq
    captured = {}

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        raise _rq.exceptions.RequestException("stop here")

    with patch.object(em._session, "get", side_effect=fake_get):
        em._fetch_ohlcv_eastmoney("600519")  # 抛 RequestException 被吞掉返回 None

    assert "secid" in captured.get("params", {}), "K线请求应正常发出（走专用 session）"
    print("[OK] K线走专用 session")
