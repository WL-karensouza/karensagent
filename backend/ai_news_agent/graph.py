"""AI 前沿咨询 Agent —— LangGraph 工作流（理解意图 → 搜索 → 摘要）

3 节点工作流（对齐 Dialogue_system.py 架构）：
  START → understand（LLM 分析意图 → 动态生成搜索词 + 时效）
       → search（Tavily API 搜索）
       → summarize（LLM 中文摘要）
       → END
"""

from typing import TypedDict
from datetime import datetime

from anthropic import Anthropic
from langgraph.graph import StateGraph, START, END
from tavily import TavilyClient

from config import TAVILY_API_KEY, LLM_MODEL_ID, LLM_API_KEY, LLM_BASE_URL
from .prompts import (
    DAILY_SEARCH_INTENT, WEEKLY_SEARCH_INTENT,
    UNDERSTAND_QUERY_PROMPT,
    SUMMARIZE_PROMPT,
)


# ═══════════════════════════════════════════
# State 定义
# ═══════════════════════════════════════════

class AiNewsState(TypedDict):
    """LangGraph 工作流状态"""
    search_intent: str         # 搜索意图描述（输入）
    search_query: str          # LLM 动态生成的搜索词（understand 节点产出）
    search_results: str        # Tavily 原始搜索结果
    summary: str               # LLM 整理后的中文摘要
    search_days: int | None           # 搜索时效天数（understand 节点动态判断，None=不限）
    report_type: str           # 报告类型 daily / weekly
    step: str                  # 当前步骤: start → understood → searched → completed
    error: str                 # 错误信息（空字符串=无错误）


# ═══════════════════════════════════════════
# LLM 和 Tavily 客户端（延迟初始化）
# ═══════════════════════════════════════════

_llm = None
_tavily = None


def _get_llm() -> Anthropic:
    """获取 LLM 客户端（单例）

    使用原生 anthropic SDK + DeepSeek 的 Anthropic 兼容端点
    （LLM_BASE_URL=https://api.deepseek.com/anthropic）。
    deepseek-v4-flash 默认开启思考模式，思考模式下 temperature 等采样参数不生效；
    新闻摘要求快速确定性输出，此处显式关闭思考，让 temperature=0.3 生效。
    """
    global _llm
    if _llm is None:
        _llm = Anthropic(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    return _llm


def _get_tavily() -> TavilyClient:
    """获取 Tavily 客户端（单例）"""
    global _tavily
    if _tavily is None:
        _tavily = TavilyClient(api_key=TAVILY_API_KEY)
    return _tavily


# ═══════════════════════════════════════════
# Node 1: 理解搜索意图 → 动态生成搜索词 + 时效
# ═══════════════════════════════════════════

def understand_query_node(state: AiNewsState) -> dict:
    """分析搜索意图，LLM 自动生成最佳搜索关键词和时效判断

    对齐参照代码 Dialogue_system.py 的 understand_query_node：
    输入 search_intent（意图描述） → LLM 分析 → 输出 search_query + search_days
    """

    search_intent = state["search_intent"]

    # 获取当前日期，确保时效判断准确
    now = datetime.now()
    today_str = now.strftime("%Y年%m月%d日")
    day_of_week = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]

    # 构建分析 prompt（对齐参照代码格式）
    understand_prompt = UNDERSTAND_QUERY_PROMPT.format(
        search_intent=search_intent,
        today_str=today_str,
        day_of_week=day_of_week,
    )

    try:
        llm = _get_llm()
        print(f"[ai_news] 🧠 分析搜索意图: {search_intent[:60]}...")
        response = llm.messages.create(
            model=LLM_MODEL_ID,
            max_tokens=200,
            thinking={"type": "disabled"},  # 意图分析求快，关思考
            messages=[{"role": "user", "content": understand_prompt}],
        )
        response_text = _extract_text(response)

        # 解析搜索关键词
        search_query = search_intent  # 默认使用意图原文
        if "搜索词：" in response_text:
            search_query = response_text.split("搜索词：")[1].split("\n")[0].strip()
        elif "搜索关键词：" in response_text:
            search_query = response_text.split("搜索关键词：")[1].split("\n")[0].strip()

        # 解析时效
        search_days = None
        if "时效：" in response_text:
            time_line = response_text.split("时效：")[1].split("\n")[0].strip()
            time_str = "".join(c for c in time_line if c.isdigit())
            if time_str:
                search_days = int(time_str)

        print(f"[ai_news] ⏱️ 时效: {search_days if search_days else '不限'}天 | 🔑 搜索词: {search_query[:80]}")

        return {
            "search_query": search_query,
            "search_days": search_days,
            "step": "understood",
        }

    except Exception as e:
        # LLM 调用失败时，回退使用搜索意图原文
        # 用 `or` 而非 `.get()` 因为 key 存在但值为 0（falsy）时需用默认值
        fallback_days = state.get("search_days") or 1
        print(f"[ai_news] ⚠️ 意图分析失败: {e}，回退使用原始意图作为搜索词 (days={fallback_days})")
        return {
            "search_query": search_intent,
            "search_days": fallback_days,
            "step": "understood",
        }


# ═══════════════════════════════════════════
# Node 2: Tavily 搜索
# ═══════════════════════════════════════════

def tavily_search_node(state: AiNewsState) -> dict:
    """调用 Tavily API 搜索 AI 新闻（使用 understand 节点生成的 search_query）"""

    search_query = state["search_query"]
    search_days = state.get("search_days")
    # 日报 5 条（昨日新闻精筛），周报 10 条（一周覆盖）
    max_results = 5 if state.get("report_type") == "daily" else 10

    try:
        client = _get_tavily()
        search_kwargs = {
            "query": search_query,
            "search_depth": "advanced",
            "include_answer": False,   # 关闭 Tavily 自带 AI 答案，避免把它的总结性话术带进摘要
            "include_raw_content": False,
            "max_results": max_results,
        }
        if search_days is not None:
            search_kwargs["days"] = search_days

        print(f"[ai_news] 🔍 Tavily 搜索: {search_query[:80]}... (days={search_days})")
        response = client.search(**search_kwargs)

        # 格式化搜索结果（不注入 Tavily 的 answer 段落，只取原始条目）
        search_results = ""

        if response.get("results"):
            search_results += "详细信息：\n"
            for i, result in enumerate(response["results"][:max_results], 1):
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
        return {"search_results": search_results, "step": "searched"}

    except Exception as e:
        error_msg = f"Tavily 搜索失败: {str(e)}"
        print(f"[ai_news] ❌ {error_msg}")
        return {
            "search_results": f"搜索失败：{error_msg}",
            "error": error_msg,
            "step": "search_failed",
        }


# ═══════════════════════════════════════════
# Node 3: LLM 摘要
# ═══════════════════════════════════════════

def _extract_text(response) -> str:
    """从 anthropic messages.create 响应中提取纯文本

    思考模式开启时 content 里混有 thinking / text 两种 block，只取 text 类型。
    """
    parts = []
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", "") == "text":
            parts.append(getattr(block, "text", "") or "")
    return "\n".join(parts)


def _invoke_summary_with_retry(llm, summarize_prompt: str, retries: int = 1) -> str:
    """调用 LLM 生成摘要，失败自动重试指定次数

    LLM 偶发超时/限流时自动重试一次，避免直接落入失败提示。
    """
    last_exc = None
    for attempt in range(retries + 1):
        try:
            response = llm.messages.create(
                model=LLM_MODEL_ID,
                max_tokens=3000,  # 摘要可能较长，预留充足空间
                thinking={"type": "disabled"},  # 摘要求确定性，关思考
                messages=[{"role": "user", "content": summarize_prompt}],
            )
            text = _extract_text(response)
            if text.strip():
                return text
            raise RuntimeError("摘要响应为空")
        except Exception as e:
            last_exc = e
            if attempt < retries:
                print(f"[ai_news] ⚠️ 摘要失败，重试 {attempt + 1}/{retries}: {e}")
    raise last_exc


def summarize_node(state: AiNewsState) -> dict:
    """调用 LLM 将搜索结果整理为中文摘要"""

    search_results = state["search_results"]
    report_type = state["report_type"]
    today_str = datetime.now().strftime("%Y年%m月%d日")

    # 搜索失败或无结果时直接返回
    if state.get("error") or search_results.startswith("未找到"):
        msg = state.get("error") or search_results
        return {"summary": f"⚠️ {msg}", "step": "completed"}

    # 日报/周报共用同一个摘要 Prompt
    summarize_prompt = SUMMARIZE_PROMPT.format(
        today_str=today_str,
        search_results=search_results,
    )

    try:
        llm = _get_llm()
        print(f"[ai_news] 🤖 LLM 摘要中... (type={report_type})")
        summary = _invoke_summary_with_retry(llm, summarize_prompt)
        print(f"[ai_news] ✅ 摘要完成，{len(summary)} 字符")
        return {"summary": summary, "step": "completed"}
    except Exception as e:
        error_msg = f"LLM 摘要失败: {str(e)}"
        print(f"[ai_news] ❌ {error_msg}")
        # 摘要失败不回退原始搜索垃圾：宁可少推，不推脏数据
        return {
            "summary": f"⚠️ 今日{report_type} AI 新闻摘要生成失败，请稍后重试。",
            "step": "completed",
        }


# ═══════════════════════════════════════════
# Workflow 编译
# ═══════════════════════════════════════════

_compiled_workflow = None


def create_news_workflow() -> StateGraph:
    """创建 LangGraph 新闻工作流（3 节点：understand → search → summarize）

    Returns:
        编译后的 StateGraph，可直接 invoke()
    """
    workflow = StateGraph(AiNewsState)

    # 添加三个节点
    workflow.add_node("understand", understand_query_node)
    workflow.add_node("search", tavily_search_node)
    workflow.add_node("summarize", summarize_node)

    # 线性流程: START → understand → search → summarize → END
    workflow.add_edge(START, "understand")
    workflow.add_edge("understand", "search")
    workflow.add_edge("search", "summarize")
    workflow.add_edge("summarize", END)

    app = workflow.compile()
    print("[ai_news] ✅ LangGraph 工作流已编译 (understand → search → summarize)")
    return app


def _get_workflow() -> StateGraph:
    """获取编译后的工作流（单例缓存，避免每次调用重建）"""
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = create_news_workflow()
    return _compiled_workflow


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
            "search_query": str,       # LLM 动态生成的搜索词
            "search_results": str,
            "summary": str,
            "success": bool,
        }
    """
    # 选择搜索意图（非硬编码 query，由 understand 节点动态生成搜索词）
    if report_type == "daily":
        search_intent = DAILY_SEARCH_INTENT
    else:
        search_intent = WEEKLY_SEARCH_INTENT

    workflow = _get_workflow()

    initial_state: AiNewsState = {
        "search_intent": search_intent,
        "search_query": "",
        "search_results": "",
        "summary": "",
        "search_days": None,
        "report_type": report_type,
        "step": "start",
        "error": "",
    }

    # 同步执行（非流式）
    result = workflow.invoke(initial_state)

    return {
        "report_type": report_type,
        "search_query": result.get("search_query", search_intent),
        "search_results": result.get("search_results", ""),
        "summary": result.get("summary", ""),
        "success": not result.get("error", ""),
    }
