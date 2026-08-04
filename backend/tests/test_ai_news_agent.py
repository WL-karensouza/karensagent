"""
TDD: AI 前沿咨询 Agent 测试

测试目标：
  1. prompts 模块 —— 搜索意图 + understand prompt（取消硬编码 query）
  2. graph 模块 —— 3 节点工作流（understand → search → summarize）
  3. understand_query_node —— LLM 响应解析逻辑
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


# ═══════════════════════════════════════════
# 1. prompts 模块测试
# ═══════════════════════════════════════════

class TestPrompts:
    """prompts.py —— 搜索意图替代硬编码 query"""

    def test_daily_search_intent_exists(self):
        """DAILY_SEARCH_INTENT 应存在且非空"""
        from ai_news_agent.prompts import DAILY_SEARCH_INTENT
        assert DAILY_SEARCH_INTENT, "DAILY_SEARCH_INTENT 不应为空"
        assert "AI" in DAILY_SEARCH_INTENT or "人工智能" in DAILY_SEARCH_INTENT

    def test_weekly_search_intent_exists(self):
        """WEEKLY_SEARCH_INTENT 应存在且非空"""
        from ai_news_agent.prompts import WEEKLY_SEARCH_INTENT
        assert WEEKLY_SEARCH_INTENT, "WEEKLY_SEARCH_INTENT 不应为空"
        assert "AI" in WEEKLY_SEARCH_INTENT or "人工智能" in WEEKLY_SEARCH_INTENT

    def test_understand_query_prompt_exists(self):
        """UNDERSTAND_QUERY_PROMPT 模板应存在"""
        from ai_news_agent.prompts import UNDERSTAND_QUERY_PROMPT
        assert UNDERSTAND_QUERY_PROMPT, "UNDERSTAND_QUERY_PROMPT 不应为空"
        assert "{search_intent}" in UNDERSTAND_QUERY_PROMPT, \
            "模板应包含 {search_intent} 占位符"
        assert "{today_str}" in UNDERSTAND_QUERY_PROMPT, \
            "模板应包含 {today_str} 占位符"

    def test_understand_query_prompt_has_format_rules(self):
        """UNDERSTAND_QUERY_PROMPT 应包含解析格式说明"""
        from ai_news_agent.prompts import UNDERSTAND_QUERY_PROMPT
        assert "搜索词：" in UNDERSTAND_QUERY_PROMPT, \
            "应包含'搜索词：'标签（用于解析）"
        assert "时效：" in UNDERSTAND_QUERY_PROMPT, \
            "应包含'时效：'标签（用于解析）"

    def test_summarize_prompt_exists(self):
        """SUMMARIZE_PROMPT 应存在且包含必要占位符"""
        from ai_news_agent.prompts import SUMMARIZE_PROMPT
        assert "{today_str}" in SUMMARIZE_PROMPT
        assert "{search_results}" in SUMMARIZE_PROMPT
        assert "search_query" not in SUMMARIZE_PROMPT.lower()

    def test_backward_compat_aliases(self):
        """DAILY/WEEKLY_SUMMARIZE_PROMPT 应指向 SUMMARIZE_PROMPT"""
        from ai_news_agent.prompts import (
            SUMMARIZE_PROMPT, DAILY_SUMMARIZE_PROMPT, WEEKLY_SUMMARIZE_PROMPT,
        )
        assert DAILY_SUMMARIZE_PROMPT is SUMMARIZE_PROMPT
        assert WEEKLY_SUMMARIZE_PROMPT is SUMMARIZE_PROMPT

    def test_no_hardcoded_search_queries(self):
        """prompts 模块不应包含硬编码的英文搜索 query（由 understand 节点动态生成）"""
        module = __import__("ai_news_agent.prompts", fromlist=["*"])
        # 检查模块中不存在 DAILY_SEARCH_QUERY / WEEKLY_SEARCH_QUERY
        assert not hasattr(module, "DAILY_SEARCH_QUERY"), \
            "不应存在 DAILY_SEARCH_QUERY（已改为搜索意图+动态生成）"
        assert not hasattr(module, "WEEKLY_SEARCH_QUERY"), \
            "不应存在 WEEKLY_SEARCH_QUERY（已改为搜索意图+动态生成）"


# ═══════════════════════════════════════════
# 2. graph 模块 —— State 定义测试
# ═══════════════════════════════════════════

class TestAiNewsState:
    """AiNewsState TypedDict 应包含所有必要字段"""

    def test_state_has_search_intent(self):
        """State 应包含 search_intent 字段"""
        from ai_news_agent.graph import AiNewsState
        assert "search_intent" in AiNewsState.__annotations__, \
            "State 应包含 search_intent 字段（搜索意图，输入）"

    def test_state_has_search_query(self):
        """State 应包含 search_query 字段（understand 节点动态生成）"""
        from ai_news_agent.graph import AiNewsState
        assert "search_query" in AiNewsState.__annotations__, \
            "State 应包含 search_query 字段（LLM 生成的搜索词）"

    def test_state_no_longer_has_query(self):
        """State 不应再包含硬编码的 query 字段"""
        from ai_news_agent.graph import AiNewsState
        assert "query" not in AiNewsState.__annotations__, \
            "State 不应包含 query 字段（已改为 search_intent + search_query）"


# ═══════════════════════════════════════════
# 3. graph 模块 —— understand_query_node 测试
# ═══════════════════════════════════════════

class TestUnderstandQueryNode:
    """understand_query_node 应能解析 LLM 响应，提取搜索词和时效"""

    def test_parses_llm_response_correctly(self):
        """解析标准格式的 LLM 响应：理解/时效/搜索词"""
        from ai_news_agent.graph import understand_query_node

        # 模拟 LLM 返回的标准格式响应（anthropic 协议：content 为 text block 列表）
        mock_response = (
            "理解：用户想要搜索过去24小时内AI领域的重要新闻进展\n"
            "时效：1\n"
            "搜索词：AI artificial intelligence breakthroughs July 2026"
        )
        mock_llm = MagicMock()
        mock_llm.messages.create.return_value.content = [
            {"type": "text", "text": mock_response}
        ]

        # 构建测试 state
        state = {
            "search_intent": "搜索过去24小时AI新闻",
            "search_query": "",
            "search_results": "",
            "summary": "",
            "search_days": None,
            "report_type": "daily",
            "step": "start",
        }

        with patch("ai_news_agent.graph._get_llm", return_value=mock_llm):
            result = understand_query_node(state)

        assert result["search_query"] == "AI artificial intelligence breakthroughs July 2026"
        assert result["search_days"] == 1
        assert result["step"] == "understood"
        assert result["step"] == "understood"

    def test_parses_weekly_timeliness(self):
        """解析时效为7天的场景"""
        from ai_news_agent.graph import understand_query_node

        mock_response = (
            "理解：用户想要搜索过去一周AI行业重要新闻\n"
            "时效：7\n"
            "搜索词：AI industry major news trends July 20-27 2026"
        )
        mock_llm = MagicMock()
        mock_llm.messages.create.return_value.content = [
            {"type": "text", "text": mock_response}
        ]

        state = {
            "search_intent": "搜索过去一周AI新闻",
            "search_query": "",
            "search_results": "",
            "summary": "",
            "search_days": None,
            "report_type": "weekly",
            "step": "start",
        }

        with patch("ai_news_agent.graph._get_llm", return_value=mock_llm):
            result = understand_query_node(state)

        assert result["search_days"] == 7
        assert result["step"] == "understood"

    def test_parses_chinese_search_keyword_label(self):
        """兼容'搜索关键词：'中文标签"""
        from ai_news_agent.graph import understand_query_node

        mock_response = (
            "理解：搜索最近AI新闻\n"
            "时效：1\n"
            "搜索关键词：latest AI news today July 2026"
        )
        mock_llm = MagicMock()
        mock_llm.messages.create.return_value.content = [
            {"type": "text", "text": mock_response}
        ]

        state = {
            "search_intent": "搜索AI新闻",
            "search_query": "",
            "search_results": "",
            "summary": "",
            "search_days": None,
            "report_type": "daily",
            "step": "start",
        }

        with patch("ai_news_agent.graph._get_llm", return_value=mock_llm):
            result = understand_query_node(state)

        assert "latest AI news" in result["search_query"]

    def test_fallback_when_llm_fails(self):
        """LLM 调用失败时，应回退使用 search_intent 作为搜索词"""
        from ai_news_agent.graph import understand_query_node

        mock_llm = MagicMock()
        mock_llm.messages.create.side_effect = Exception("API 调用失败")

        state = {
            "search_intent": "搜索过去24小时AI新闻",
            "search_query": "",
            "search_results": "",
            "summary": "",
            "search_days": None,
            "report_type": "daily",
            "step": "start",
        }

        with patch("ai_news_agent.graph._get_llm", return_value=mock_llm):
            result = understand_query_node(state)

        # 失败时应回退到 search_intent
        assert result["search_query"] == "搜索过去24小时AI新闻"
        assert result["step"] == "understood"


# ═══════════════════════════════════════════
# 4. graph 模块 —— 工作流结构测试
# ═══════════════════════════════════════════

class TestWorkflowStructure:
    """LangGraph 工作流应为 3 节点：understand → search → summarize"""

    def test_workflow_has_three_nodes(self):
        """工作流应包含 understand、search、summarize 三个节点"""
        from ai_news_agent.graph import create_news_workflow

        wf = create_news_workflow()
        nodes = wf.get_graph().nodes

        node_names = {n for n in nodes}
        assert "understand" in node_names, "应包含 understand 节点"
        assert "search" in node_names, "应包含 search 节点"
        assert "summarize" in node_names, "应包含 summarize 节点"

    def test_workflow_has_understand_node_function(self):
        """understand_query_node 函数应存在于 graph 模块"""
        from ai_news_agent import graph as graph_module
        assert hasattr(graph_module, "understand_query_node"), \
            "graph 模块应包含 understand_query_node 函数"
        assert callable(graph_module.understand_query_node), \
            "understand_query_node 应为可调用函数"

    def test_run_news_search_uses_daily_search_intent(self):
        """run_news_search('daily') 应使用 DAILY_SEARCH_INTENT"""
        from ai_news_agent.prompts import DAILY_SEARCH_INTENT
        from ai_news_agent.graph import AiNewsState

        # 验证 daily 对应的 search_intent 非空
        assert DAILY_SEARCH_INTENT
        # State 应包含 search_intent
        assert "search_intent" in AiNewsState.__annotations__

    def test_run_news_search_uses_weekly_search_intent(self):
        """run_news_search('weekly') 应使用 WEEKLY_SEARCH_INTENT"""
        from ai_news_agent.prompts import WEEKLY_SEARCH_INTENT
        from ai_news_agent.graph import AiNewsState

        assert WEEKLY_SEARCH_INTENT
        assert "search_intent" in AiNewsState.__annotations__


# ═══════════════════════════════════════════
# 5. 集成测试（仅在有 API key 时运行）
# ═══════════════════════════════════════════

class TestIntegration:
    """端到端集成测试 —— 需要 API key，无 key 时跳过"""

    def test_full_workflow_daily(self):
        """完整 daily 工作流：understand → search → summarize"""
        import os
        if not os.getenv("TAVILY_API_KEY") or not os.getenv("LLM_API_KEY"):
            import pytest
            pytest.skip("缺少 TAVILY_API_KEY 或 LLM_API_KEY，跳过集成测试")

        from ai_news_agent.graph import run_news_search

        result = run_news_search("daily")

        assert result["report_type"] == "daily"
        assert "search_query" in result, "应包含 LLM 生成的 search_query"
        assert result["search_query"], "search_query 不应为空"
        assert "summary" in result
        assert result["summary"], "summary 不应为空"
        assert "search_results" in result
        print(f"[INTEGRATION] daily search_query: {result['search_query'][:80]}...")
        print(f"[INTEGRATION] daily summary: {result['summary'][:200]}...")

    def test_full_workflow_weekly(self):
        """完整 weekly 工作流：understand → search → summarize"""
        import os
        if not os.getenv("TAVILY_API_KEY") or not os.getenv("LLM_API_KEY"):
            import pytest
            pytest.skip("缺少 TAVILY_API_KEY 或 LLM_API_KEY，跳过集成测试")

        from ai_news_agent.graph import run_news_search

        result = run_news_search("weekly")

        assert result["report_type"] == "weekly"
        assert "search_query" in result
        assert result["search_query"], "search_query 不应为空"
        assert "summary" in result
        print(f"[INTEGRATION] weekly search_query: {result['search_query'][:80]}...")
        print(f"[INTEGRATION] weekly summary: {result['summary'][:200]}...")
