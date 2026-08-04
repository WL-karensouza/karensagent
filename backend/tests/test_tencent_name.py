"""腾讯行情查名备份通道 TDD：东财被限速/掐断时的简称备份链路

背景：东财 push2 对本机 IP 间歇性限速掐断（RemoteDisconnected），
腾讯 qt.gtimg.cn 实测可用，作为简称查询的备份通道，
保证 summary 维度能拼出 iFinD 认识的简称 query。
"""
import sys
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND))


class _FakeTencentResp:
    encoding = "gbk"
    status_code = 200
    text = 'v_sh600519="1~贵州茅台~600519~1358.98~1350.60~"'


def test_get_name_tencent_parses_shortname():
    """腾讯接口：GBK 响应、~ 分隔、字段[1] 为简称"""
    from stock_agent.datasources import eastmoney as em

    with patch.object(em._session, "get", return_value=_FakeTencentResp()):
        assert em._get_name_tencent("600519") == "贵州茅台"
    print("[OK] 腾讯接口解析简称")


def test_get_name_tencent_sz_and_hk_prefix():
    """深市 sz 前缀；港股两种格式（2513.HK 归一化态 / HK2513 输入态）都走 hk+5位"""
    from stock_agent.datasources import eastmoney as em
    urls = []

    def fake_get(url, **kwargs):
        urls.append(url)
        return _FakeTencentResp()

    with patch.object(em._session, "get", side_effect=fake_get):
        em._get_name_tencent("000858")
        em._get_name_tencent("2513.HK")
        em._get_name_tencent("HK2513")

    assert "sz000858" in urls[0], f"深市应 sz 前缀，实际 {urls[0]}"
    assert "hk02513" in urls[1], f"港股归一化态应 hk+5位，实际 {urls[1]}"
    assert "hk02513" in urls[2], f"港股输入态 HKxxxx 也应 hk+5位，实际 {urls[2]}"
    print("[OK] 深市/港股代码前缀（含 HKxxxx 兼容）")


def test_resolve_summary_query_tencent_fallback():
    """东财失败 → 腾讯兜底查简称 → summary query 用简称"""
    from stock_agent.skill import collect as collect_mod

    with patch.object(collect_mod, "_get_name_eastmoney", return_value=None), \
         patch.object(collect_mod, "_get_name_tencent", return_value="贵州茅台"):
        q = collect_mod._resolve_summary_query("600519")

    assert q.startswith("贵州茅台"), f"东财失败时应用腾讯简称，实际: {q[:30]}"
    print("[OK] 东财失败腾讯兜底")
