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
