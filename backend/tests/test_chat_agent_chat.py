"""chat_agent.routers.chat 队列桥接测试"""
import asyncio
from unittest.mock import patch

from chat_agent.routers import chat


def _collect(events_async_gen):
    """跑 async generator 收集事件列表（不需要 pytest-asyncio）"""
    async def _run():
        return [e async for e in events_async_gen]
    return asyncio.run(_run())


class TestStreamEvents:
    """_stream_events：线程内事件实时转发 + 线程结束后的 delta/done/error"""

    def test_success_emits_events_in_order(self):
        def fake_run_qa(question, stock_code, stock_name, report_context,
                        tool_hints, history, on_event=None):
            on_event({"type": "phase", "phase": "understand"})
            on_event({"type": "tool_start", "name": "search_news",
                      "label": "查询近期新闻"})
            on_event({"type": "tool_done", "name": "search_news",
                      "label": "查询近期新闻", "ok": True})
            return {"answer": "五粮液近期新闻显示……", "is_off_topic": False,
                    "tool_calls": [{"name": "search_news", "label": "查询近期新闻",
                                    "ok": True, "duration_ms": 50}],
                    "success": True, "error": ""}

        session = {"id": 1, "stock_name": "五粮液"}
        req = chat.AskRequest(question="最近有什么新闻", report_id=None, stock_name="")
        with patch.object(chat, "run_qa_agent", side_effect=fake_run_qa), \
             patch.object(chat, "add_message", lambda *a, **k: None):
            events = _collect(chat._stream_events(session, req, "000858", "报告", []))

        types = [e["type"] for e in events]
        assert types[0:3] == ["phase", "tool_start", "tool_done"]
        assert types[0] == "phase" and events[0]["phase"] == "understand"
        assert types[-1] == "done"
        assert "delta" in types
        assert all(t not in ("error",) for t in types)

    def test_failure_emits_error_and_stops(self):
        def fake_run_qa(question, stock_code, stock_name, report_context,
                        tool_hints, history, on_event=None):
            return {"answer": "karens 暂时遇到问题，请稍后重试。（boom）",
                    "is_off_topic": False, "tool_calls": [],
                    "success": False, "error": "boom"}

        session = {"id": 1, "stock_name": "五粮液"}
        req = chat.AskRequest(question="问题", report_id=None, stock_name="")
        with patch.object(chat, "run_qa_agent", side_effect=fake_run_qa), \
             patch.object(chat, "add_message", lambda *a, **k: None):
            events = _collect(chat._stream_events(session, req, "000858", "报告", []))

        assert events == [{"type": "error", "message": "karens 暂时遇到问题，请稍后重试。（boom）"}]

    def test_phase_events_forwarded_realtime(self):
        """即使 run_qa_agent 不发工具事件，成功路径也能产出 answer 阶段"""
        def fake_run_qa(question, stock_code, stock_name, report_context,
                        tool_hints, history, on_event=None):
            return {"answer": "纯报告解读", "is_off_topic": False,
                    "tool_calls": [], "success": True, "error": ""}

        session = {"id": 1, "stock_name": "五粮液"}
        req = chat.AskRequest(question="报告说了什么", report_id=None, stock_name="")
        with patch.object(chat, "run_qa_agent", side_effect=fake_run_qa), \
             patch.object(chat, "add_message", lambda *a, **k: None):
            events = _collect(chat._stream_events(session, req, "000858", "报告", []))

        assert events[-1]["type"] == "done"
        assert events[-1]["full"] == "纯报告解读"
