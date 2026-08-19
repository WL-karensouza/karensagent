"""chat_agent.graph 事件插桩测试"""
import json
from unittest.mock import MagicMock, patch

import chat_agent.graph as graph


def _make_resp(content, tool_calls=None):
    """构造 OpenAI 风格响应：msg.content / msg.tool_calls"""
    msg = MagicMock()
    msg.content = content
    msg.reasoning_content = None
    msg.tool_calls = tool_calls
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_tool_call(name, arguments):
    tc = MagicMock()
    tc.id = "call_1"
    tc.type = "function"
    fn = MagicMock()
    fn.name = name
    fn.arguments = json.dumps(arguments)
    tc.function = fn
    return tc


class TestRunQaAgentEvents:
    """run_qa_agent 插桩：phase 事件按序发出、透传工具事件"""

    def test_emits_phase_events_with_tools(self):
        """带工具问答：事件序 = understand → tool_start → tool_done → answer"""
        events = []

        def fake_understand(question, stock_code, stock_name):
            return {"is_off_topic": False, "stock_code": stock_code,
                    "needs_tools": True, "tool_hints": ["财务"]}

        def fake_tool_loop(question, target_code, hints, on_event=None, stock_name=""):
            on_event({"type": "tool_start", "name": "get_stock_financials",
                      "label": "核对财务数据"})
            on_event({"type": "tool_done", "name": "get_stock_financials",
                      "label": "核对财务数据", "ok": True})
            return "财务数据", [{"name": "get_stock_financials",
                                 "label": "核对财务数据", "ok": True, "duration_ms": 100}]

        def fake_answer(question, stock_code, stock_name, target_code,
                        report_context, tool_results, is_off_topic, history=None):
            return "这是回答"

        with patch.object(graph, "_understand", side_effect=fake_understand), \
             patch.object(graph, "_tool_loop", side_effect=fake_tool_loop), \
             patch.object(graph, "_answer", side_effect=fake_answer):
            result = graph.run_qa_agent(
                "估值如何", "000858", "五粮液", "报告", [], None,
                on_event=events.append,
            )

        types = [e["type"] for e in events]
        assert types == ["phase", "tool_start", "tool_done", "phase"]
        assert events[0]["phase"] == "understand"
        assert events[3]["phase"] == "answer"
        assert result["success"] is True
        assert result["tool_calls"][0]["name"] == "get_stock_financials"

    def test_no_tools_no_tool_events(self):
        """纯报告解读（needs_tools=False）：只有 understand/answer 两个 phase"""
        events = []

        with patch.object(graph, "_understand", return_value={
            "is_off_topic": False, "stock_code": "000858",
            "needs_tools": False, "tool_hints": [],
        }), \
             patch.object(graph, "_tool_loop", return_value=("", [])) as tl, \
             patch.object(graph, "_answer", return_value="报告解读"):
            graph.run_qa_agent("报告说了什么", "000858", "五粮液",
                               "报告", [], None, on_event=events.append)

        types = [e["type"] for e in events]
        assert types == ["phase", "phase"]
        assert events[0]["phase"] == "understand"
        assert events[1]["phase"] == "answer"
        tl.assert_not_called()

    def test_off_topic_still_emits_understand(self):
        """无关问题：只发 understand 阶段事件，不发 answer（边界态 B1：②③ 不出现）"""
        events = []

        with patch.object(graph, "_understand", return_value={
            "is_off_topic": True, "stock_code": "000858",
            "needs_tools": False, "tool_hints": [],
        }), \
             patch.object(graph, "_tool_loop", return_value=("", [])), \
             patch.object(graph, "_answer", return_value="karens暂时无法回答您这个问题哦？"):
            graph.run_qa_agent("今天天气如何", "000858", "五粮液",
                               "报告", [], None, on_event=events.append)

        assert events[0] == {"type": "phase", "phase": "understand"}
        assert {"type": "phase", "phase": "answer"} not in events

    def test_on_event_none_keeps_old_behavior(self):
        """不传 on_event：事件插桩无副作用，返回结构不变"""
        with patch.object(graph, "_understand", return_value={
            "is_off_topic": False, "stock_code": "000858",
            "needs_tools": False, "tool_hints": [],
        }), \
             patch.object(graph, "_answer", return_value="回答"):
            result = graph.run_qa_agent("问", "000858", "五粮液", "报告", [], None)

        assert result["success"] is True
        assert result["answer"] == "回答"


class TestToolLoopEvents:
    """_tool_loop 真实执行：每个工具调用发 tool_start + tool_done"""

    def test_emits_start_and_done_per_tool(self, monkeypatch):
        events = []
        first = _make_resp("", tool_calls=[
            _make_tool_call("search_news", {"query": "五粮液最新新闻"}),
        ])
        second = _make_resp("好的，还有问题吗")
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = [first, second]
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        monkeypatch.setattr(graph, "execute_tool_call",
                            lambda name, args: {"ok": True, "text": "新闻数据"})
        monkeypatch.setattr(graph, "get_tool_descriptions",
                            lambda server: [{"name": "search_news",
                                             "description": "查新闻",
                                             "inputSchema": {}}])

        results, records = graph._tool_loop(
            "最近有什么新闻", "000858", [], on_event=events.append)

        assert len(records) == 1
        assert records[0]["arguments"] == {"query": "五粮液最新新闻"}
        assert events[0]["type"] == "tool_start"
        assert events[0]["label"] == "查询近期新闻"
        assert events[1]["type"] == "tool_done"
        assert events[1]["ok"] is True

    def test_failed_tool_emits_ok_false(self, monkeypatch):
        events = []
        first = _make_resp("", tool_calls=[
            _make_tool_call("search_news", {"query": "x"}),
        ])
        second = _make_resp("结束")
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = [first, second]
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        monkeypatch.setattr(graph, "execute_tool_call",
                            lambda name, args: {"ok": False, "text": "[错误] iFinD 限速"})
        monkeypatch.setattr(graph, "get_tool_descriptions",
                            lambda server: [{"name": "search_news",
                                             "description": "查新闻",
                                             "inputSchema": {}}])

        _, records = graph._tool_loop("新闻", "000858", [], on_event=events.append)

        assert events[1] == {"type": "tool_done", "name": "search_news",
                             "label": "查询近期新闻", "ok": False}
        assert records[0]["arguments"] == {"query": "x"}

    def test_context_contains_stock_name(self, monkeypatch):
        """_tool_loop 的 context 应含股票名称，让 LLM 生成 query 时能带上证券实体

        实证（2026-08-19）：query 缺证券实体名导致财务查询"假成功"，本测试确保
        context 注入目标股票名称，LLM 得以在 query 中携带实体名。
        """
        resp = _make_resp("结束")
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        monkeypatch.setattr(graph, "get_tool_descriptions", lambda server: [])

        graph._tool_loop("财报分析", "301301", [], on_event=None, stock_name="川宁生物")

        sent = fake_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
        assert "川宁生物" in sent
        assert "301301" in sent


class TestAnswerFallback:
    """_answer 空 content 兜底"""

    def test_empty_content_returns_friendly_hint(self, monkeypatch):
        """LLM 返回空 content 时 answer 应为兜底文案而非空（防只显示免责声明）"""
        resp = _make_resp("")
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)

        answer = graph._answer("财报分析", "301301", "川宁生物", "301301",
                               "报告", "工具结果", False)
        assert "抱歉" in answer
        assert "不构成投资建议" in answer  # DISCLAIMER 仍在
