"""summary 维度查询修复 TDD：get_stock_summary 只认股票简称（iFinD 服务端识别）

根因：「股票代码600519」格式被服务端拒（"未识别到有效的A股股票代码"），
summary critical 维度失败触发硬终止门，导致 LLM 分析整体不触发。
修复：summary 查询构建前先用东财查简称，查不到降级回代码格式。
"""
import sys
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND))

from stock_agent.skill.report import _build_params, DIMENSIONS

SUMMARY_DIM = next(d for d in DIMENSIONS if d["key"] == "summary")


def test_summary_query_uses_shortname():
    """东财返回简称时，summary 查询必须以简称开头（iFinD 只认简称）"""
    from stock_agent.skill.report import _resolve_summary_query
    with patch("stock_agent.skill.report._get_name_eastmoney", return_value="贵州茅台"):
        query = _resolve_summary_query("600519")
    assert query.startswith("贵州茅台"), f"查询应以简称开头，实际: {query[:50]}"
    assert "基本信息" in query
    print("[OK] summary 查询用简称")


def test_summary_query_fallback_to_code():
    """简称查不到时降级回代码格式（不崩溃，行为等同旧版）"""
    from stock_agent.skill.report import _resolve_summary_query
    with patch("stock_agent.skill.report._get_name_eastmoney", return_value=None):
        query = _resolve_summary_query("600519")
    assert "600519" in query
    print("[OK] 简称失败降级代码格式")


def test_build_params_summary_uses_resolver():
    """_build_params 的 summary 分支应走简称解析器"""
    with patch("stock_agent.skill.report._get_name_eastmoney", return_value="贵州茅台"):
        params = _build_params(SUMMARY_DIM, "600519")
    assert params["query"].startswith("贵州茅台"), f"实际: {params['query'][:50]}"
    print("[OK] _build_params 接入简称解析")


def test_dim_collect_retries_on_transient_error():
    """iFinD 间歇性拒绝（疑似限速）时，维度采集应自动重试一次"""
    from stock_agent.skill import report as rp
    from stock_agent.skill.report import _call_dim_with_retry
    calls = []

    def flaky_call(server, tool, params):
        calls.append(1)
        if len(calls) == 1:
            return {"type": "answer", "text": "[错误] 未识别到有效的A股股票代码"}
        return {"type": "answer", "text": "正常数据", "raw": {"k": "v"}}

    with patch.object(rp, "call_skill", side_effect=flaky_call), \
         patch.object(rp, "extract_text", side_effect=lambda r: r["text"]), \
         patch.object(rp, "extract_raw", side_effect=lambda r: r.get("raw")), \
         patch.object(rp.time, "sleep"):
        text, raw = _call_dim_with_retry(SUMMARY_DIM, "600519")

    assert text == "正常数据", f"重试后应拿到正常数据，实际: {text}"
    assert len(calls) == 2, f"应重试到第 2 次成功，实际调用 {len(calls)} 次"
    print("[OK] 维度采集间歇失败自动重试")
