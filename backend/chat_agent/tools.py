"""投研 AI 问答 —— iFinD 工具层

职责：
  1. 维护工具→友好名映射（前端步骤卡片展示用，不暴露接口名）
  2. 拉取 iFinD tools/list 缓存工具描述（供 Function Calling 声明）
  3. execute_tool_call：把 LLM 的 tool_call 映射到 stock_agent.skill.call_skill 执行
"""
import json

from stock_agent.skill import call_skill, list_skill_tools
from stock_agent.skill.extract import extract_text

# 工具名 → 友好展示名（前端步骤卡片用）
TOOL_FRIENDLY_NAMES = {
    "get_stock_summary": "获取基本信息",
    "search_stocks": "智能选股",
    "get_stock_performance": "查询行情走势",
    "get_stock_info": "查询基本资料",
    "get_stock_shareholders": "查询股东结构",
    "get_stock_financials": "核对财务数据",
    "get_risk_indicators": "分析风险指标",
    "get_stock_events": "查询重大事件",
    "get_esg_data": "查询 ESG 评级",
    "stock_highfreq_quotes": "查询实时行情",
    "search_notice": "查询公司公告",
    "search_news": "查询近期新闻",
    # 港股 global_stock
    "global_stock_profile": "查询港股基本资料",
    "global_stock_quotes": "查询港股行情",
    "global_stock_financial": "查询港股财务",
    "global_stock_events": "查询港股事件",
    # 指数 / 板块 / 基金
    "index_data": "查询指数数据",
    "sector_data": "查询板块数据",
    "index_highfreq_quotes": "查询指数实时行情",
    "get_fund_profile": "查询基金资料",
    "get_fund_market_performance": "查询基金业绩",
    "get_fund_ownership": "查询基金持仓",
    "get_fund_portfolio": "查询基金组合",
    "get_fund_financials": "查询基金财务",
    "get_fund_company_info": "查询基金公司",
    "fund_highfreq_quotes": "查询基金实时行情",
}

# 工具名 → 所属 iFinD 服务
TOOL_SERVER_MAP = {
    # A股 / 股票
    "get_stock_summary": "stock",
    "search_stocks": "stock",
    "get_stock_performance": "stock",
    "get_stock_info": "stock",
    "get_stock_shareholders": "stock",
    "get_stock_financials": "stock",
    "get_risk_indicators": "stock",
    "get_stock_events": "stock",
    "get_esg_data": "stock",
    "stock_highfreq_quotes": "stock",
    # 新闻
    "search_notice": "news",
    "search_news": "news",
    # 港股
    "global_stock_profile": "global_stock",
    "global_stock_quotes": "global_stock",
    "global_stock_financial": "global_stock",
    "global_stock_events": "global_stock",
    # 指数
    "index_data": "index",
    "sector_data": "index",
    "index_highfreq_quotes": "index",
    # 基金
    "get_fund_profile": "fund",
    "get_fund_market_performance": "fund",
    "get_fund_ownership": "fund",
    "get_fund_portfolio": "fund",
    "get_fund_financials": "fund",
    "get_fund_company_info": "fund",
    "fund_highfreq_quotes": "fund",
}


_tool_descriptions_cache = {}


def get_tool_descriptions(server: str = "stock") -> list[dict]:
    """获取某服务全部工具描述（供 Function Calling 声明）

    首次调用从 iFinD tools/list 拉取并缓存；返回 MCP 工具结构，
    含 name/description/inputSchema。
    """
    if server in _tool_descriptions_cache:
        return _tool_descriptions_cache[server]
    try:
        res = list_skill_tools(server)
        # list_skill_tools 返回 {"data": {"result": {"tools": [...]}}}
        tools = res.get("data", {}).get("result", {}).get("tools", [])
        _tool_descriptions_cache[server] = tools
        return tools
    except Exception as e:
        print(f"[chat_agent] ⚠️ 拉取 {server} 工具描述失败: {e}")
        return []


def execute_tool_call(tool_name: str, arguments: dict) -> dict:
    """执行一个 iFinD 工具调用

    Args:
        tool_name: iFinD 工具名
        arguments: LLM 生成的参数 dict（query 自然语言 / 结构化参数）

    Returns:
        {"ok": bool, "text": str}   # text 为提取后的业务文本，可直接喂回 LLM
        ok 反映数据有效性：仅调用层成功但文本是 [无数据]/[错误] 时置 False（防假成功）
    """
    server = TOOL_SERVER_MAP.get(tool_name)
    if server is None:
        return {"ok": False, "text": f"[错误] 未知工具: {tool_name}"}

    # 高频行情用结构化参数；news 类需补 time 参数（可默认最近 90 天）
    params = dict(arguments)
    if tool_name == "search_news" and "time_start" not in params:
        params["time_start"] = _days_ago_str(90)
        params["time_end"] = _days_ago_str(0)
    if tool_name == "search_notice" and "time_start" not in params:
        params["time_start"] = _days_ago_str(180)
        params["time_end"] = _days_ago_str(0)

    try:
        result = call_skill(server, tool_name, params)
        text = extract_text(result)
        # ok 判定 = 调用层成功 且 提取文本不是无数据/错误。防止"假成功"：
        # iFinD 内层 code=1 成功包装但 answer 是"未返回有效结果"类业务失败时，
        # extract_text 已转 [无数据]，此处置 ok=False，避免误导 LLM 反复重试。
        ok = bool(result.get("ok", False)) and not text.startswith(("[无数据]", "[错误]"))
        return {"ok": ok, "text": text}
    except Exception as e:
        return {"ok": False, "text": f"[错误] {type(e).__name__}: {str(e)}"}


def _days_ago_str(days: int) -> str:
    """返回 N 天前的日期字符串 YYYY-MM-DD"""
    from datetime import datetime, timedelta
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
