"""chat_agent.routers.chat 异步驱动 LangGraph 测试"""
import asyncio
import json
from unittest.mock import MagicMock, patch

from chat_agent import graph
from chat_agent.routers import chat


def _make_resp(content, tool_calls=None):
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


def _collect(events_async_gen):
    """跑 async generator 收集事件列表（不需要 pytest-asyncio）"""
    async def _run():
        return [e async for e in events_async_gen]
    return asyncio.run(_run())


class TestStreamEvents:
    """_stream_events：异步驱动 LangGraph，custom 事件透传 + 结尾 delta/done/error"""

    def test_success_emits_events_in_order(self, monkeypatch):
        """真图 + mock LLM：工具事件实时转发 + delta/done"""
        responses = [
            _make_resp('{"is_off_topic": false, "needs_tools": true, "tool_hints": []}'),
            _make_resp("", tool_calls=[_make_tool_call("search_news", {"query": "五粮液新闻"})]),
            _make_resp("收尾"),
            _make_resp("五粮液近期新闻显示……"),
        ]
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = responses
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        monkeypatch.setattr(graph, "execute_tool_call",
                            lambda name, args: {"ok": True, "text": "新闻数据"})
        monkeypatch.setattr(graph, "get_tool_descriptions",
                            lambda server: [{"name": "search_news",
                                             "description": "新闻", "inputSchema": {}}])

        session = {"id": 1, "stock_name": "五粮液"}
        req = chat.AskRequest(question="最近有什么新闻", report_id=None, stock_name="")
        with patch.object(chat, "add_message", MagicMock()) as add_msg:
            events = _collect(chat._stream_events(session, req, "000858", "报告", []))

        types = [e["type"] for e in events]
        assert types[0] == "phase" and events[0]["phase"] == "understand"
        assert "tool_start" in types and "tool_done" in types
        assert "delta" in types
        assert types[-1] == "done"
        assert all(t != "error" for t in types)
        assert add_msg.called
        # 落库参数：assistant + answer + tool_calls
        args, _ = add_msg.call_args
        assert args[1] == "assistant"
        assert args[3][0]["name"] == "search_news"

    def test_failure_emits_error_and_stops(self, monkeypatch):
        """图执行异常（answer 节点 LLM 抛错）：error 事件 + 落库失败消息"""
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = Exception("boom")
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)

        session = {"id": 1, "stock_name": "五粮液"}
        req = chat.AskRequest(question="问题", report_id=None, stock_name="")
        with patch.object(chat, "add_message", MagicMock()) as add_msg:
            events = _collect(chat._stream_events(session, req, "000858", "报告", []))

        # understand 节点会吞掉首轮 LLM 异常（默认按股票相关处理），error 由 answer 节点抛出，位于事件末尾
        assert events[-1]["type"] == "error"
        assert "Exception" in events[-1]["message"]
        assert add_msg.called

    def test_no_tools_produces_delta_and_done(self, monkeypatch):
        """纯报告解读：两 phase + delta + done"""
        responses = [
            _make_resp('{"is_off_topic": false, "needs_tools": false}'),
            _make_resp("纯报告解读"),
        ]
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = responses
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)

        session = {"id": 1, "stock_name": "五粮液"}
        req = chat.AskRequest(question="报告说了什么", report_id=None, stock_name="")
        with patch.object(chat, "add_message", lambda *a, **k: None):
            events = _collect(chat._stream_events(session, req, "000858", "报告", []))

        types = [e["type"] for e in events]
        assert types[:2] == ["phase", "phase"]
        assert types[-1] == "done"
        assert events[-1]["full"].startswith("纯报告解读")
        assert "delta" in types
