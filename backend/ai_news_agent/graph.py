"""AI 前沿咨询 Agent —— LangGraph 工作流（搜索 → 摘要）"""

import os
from typing import TypedDict
from datetime import datetime

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from tavily import TavilyClient

from config import TAVILY_API_KEY, LLM_MODEL_ID, LLM_API_KEY, LLM_BASE_URL
from .prompts import (
    DAILY_SEARCH_QUERY, WEEKLY_SEARCH_QUERY,
    DAILY_SUMMARIZE_PROMPT, WEEKLY_SUMMARIZE_PROMPT,
)


# ═══════════════════════════════════════════
# State 定义
# ═══════════════════════════════════════════

class AiNewsState(TypedDict):
    """LangGraph 工作流状态"""
    query: str                # 搜索查询词
    search_results: str       # Tavily 原始搜索结果
    summary: str              # LLM 整理后的中文摘要
    search_days: int          # 搜索时效天数（1 或 7）
    report_type: str          # 报告类型 daily / weekly


# ═══════════════════════════════════════════
# LLM 和 Tavily 客户端（延迟初始化）
# ═══════════════════════════════════════════

_llm = None
_tavily = None


def _get_llm() -> ChatOpenAI:
    """获取 LLM 客户端（单例）"""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=LLM_MODEL_ID,
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            temperature=0.3,
        )
    return _llm


def _get_tavily() -> TavilyClient:
    """获取 Tavily 客户端（单例）"""
    global _tavily
    if _tavily is None:
        _tavily = TavilyClient(api_key=TAVILY_API_KEY)
    return _tavily


# ═══════════════════════════════════════════
# Node 1: Tavily 搜索
# ═══════════════════════════════════════════

def tavily_search_node(state: AiNewsState) -> dict:
    """调用 Tavily API 搜索 AI 新闻"""

    query = state["query"]
    search_days = state["search_days"]

    try:
        client = _get_tavily()
        search_kwargs = {
            "query": query,
            "search_depth": "advanced",
            "include_answer": True,
            "include_raw_content": False,
            "max_results": 10,
        }
        if search_days is not None:
            search_kwargs["days"] = search_days

        print(f"[ai_news] 🔍 Tavily 搜索: {query[:80]}... (days={search_days})")
        response = client.search(**search_kwargs)

        # 格式化搜索结果
        search_results = ""
        if response.get("answer"):
            search_results = f"综合答案：\n{response['answer']}\n\n"

        if response.get("results"):
            search_results += "详细结果：\n"
            for i, result in enumerate(response["results"][:10], 1):
                title = result.get("title", "")
                content = result.get("content", "")
                url = result.get("url", "")
                published = result.get("published_date", "")
                time_info = published if published else "时间未知"
                search_results += (
                    f"{i}. {title}\n"
                    f"   {content}\n"
                    f"   📅 {time_info}\n"
                    f"   🔗 {url}\n\n"
                )

        if not search_results:
            search_results = "未找到相关新闻。"

        print(f"[ai_news] ✅ 搜索完成，获取 {len(response.get('results', []))} 条结果")
        return {"search_results": search_results}

    except Exception as e:
        error_msg = f"Tavily 搜索失败: {str(e)}"
        print(f"[ai_news] ❌ {error_msg}")
        return {"search_results": f"搜索失败：{error_msg}"}


# ═══════════════════════════════════════════
# Node 2: LLM 摘要
# ═══════════════════════════════════════════

def summarize_node(state: AiNewsState) -> dict:
    """调用 LLM 将搜索结果整理为中文摘要"""

    search_results = state["search_results"]
    report_type = state["report_type"]
    today_str = datetime.now().strftime("%Y年%m月%d日")

    # 搜索失败时走 fallback
    if search_results.startswith("搜索失败") or search_results.startswith("未找到"):
        return {"summary": f"⚠️ {search_results}"}

    # 选择对应的 Prompt 模板
    if report_type == "daily":
        summarize_prompt = DAILY_SUMMARIZE_PROMPT.format(
            today_str=today_str,
            search_results=search_results,
        )
    else:
        summarize_prompt = WEEKLY_SUMMARIZE_PROMPT.format(
            today_str=today_str,
            search_results=search_results,
        )

    try:
        llm = _get_llm()
        print(f"[ai_news] 🤖 LLM 摘要中... (type={report_type})")
        response = llm.invoke(summarize_prompt)
        summary = response.content
        print(f"[ai_news] ✅ 摘要完成，{len(summary)} 字符")
        return {"summary": summary}
    except Exception as e:
        error_msg = f"LLM 摘要失败: {str(e)}"
        print(f"[ai_news] ❌ {error_msg}")
        return {"summary": f"⚠️ LLM 摘要生成失败，以下为原始搜索结果：\n\n{search_results}"}


# ═══════════════════════════════════════════
# Workflow 编译
# ═══════════════════════════════════════════

def create_news_workflow() -> StateGraph:
    """创建 LangGraph 新闻搜索+摘要工作流

    Returns:
        编译后的 StateGraph，可直接 invoke()
    """
    workflow = StateGraph(AiNewsState)

    # 添加节点
    workflow.add_node("search", tavily_search_node)
    workflow.add_node("summarize", summarize_node)

    # 线性流程: START → search → summarize → END
    workflow.add_edge(START, "search")
    workflow.add_edge("search", "summarize")
    workflow.add_edge("summarize", END)

    app = workflow.compile()
    print("[ai_news] ✅ LangGraph 工作流已编译 (search → summarize)")
    return app


# ═══════════════════════════════════════════
# 便捷调用函数
# ═══════════════════════════════════════════

def run_news_search(report_type: str) -> dict:
    """执行一次 AI 新闻搜索+摘要

    Args:
        report_type: "daily"（昨日AI新闻） 或 "weekly"（近一周AI新闻）

    Returns:
        {
            "report_type": str,
            "search_query": str,
            "search_results": str,
            "summary": str,
            "success": bool,
        }
    """
    if report_type == "daily":
        query = DAILY_SEARCH_QUERY
        search_days = 1
    else:
        query = WEEKLY_SEARCH_QUERY
        search_days = 7

    workflow = create_news_workflow()

    initial_state: AiNewsState = {
        "query": query,
        "search_results": "",
        "summary": "",
        "search_days": search_days,
        "report_type": report_type,
    }

    # 同步执行（非流式）
    result = workflow.invoke(initial_state)

    return {
        "report_type": report_type,
        "search_query": query,
        "search_results": result.get("search_results", ""),
        "summary": result.get("summary", ""),
        "success": not result.get("summary", "").startswith("⚠️"),
    }
