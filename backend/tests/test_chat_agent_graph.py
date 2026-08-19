"""chat_agent.graph 节点层测试（LangGraph 迁移 Task 1）"""
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


class TestBuildInitialState:
    """build_initial_state：初始状态字段正确"""

    def test_messages_starts_with_plain_question(self):
        st = graph.build_initial_state("财报分析", "301301", "川宁生物", "报告", [], None)
        assert st["messages"] == [{"role": "user", "content": "财报分析"}]
        assert st["target_code"] == "301301"
        assert st["rounds"] == 0
        assert st["tool_calls"] == []
        assert st["answer_text"] == ""
        assert st["is_off_topic"] is False


class TestUnderstandNode:
    """understand 节点：文本行解析、全半角冒号兼容、字段级/整体兜底"""

    def test_parses_textlines_and_maps_fields(self, monkeypatch):
        writer = MagicMock()
        resp = _make_resp("是否股票相关：是\n"
                          "目标股票代码：000858\n"
                          "需要实时查数：是\n"
                          "数据方向：财务、估值")
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        state = graph.build_initial_state("财报分析", "000858", "五粮液", "报告", [], None)
        out = graph.understand_node(state, writer)
        assert out["is_off_topic"] is False
        assert out["needs_tools"] is True
        assert out["target_code"] == "000858"
        assert out["tool_hints"] == ["财务", "估值"]
        writer.assert_called_once_with({"type": "phase", "phase": "understand"})

    def test_halfwidth_colon_compatible(self, monkeypatch):
        """LLM 输出半角冒号也能解析（宽松兼容）"""
        writer = MagicMock()
        resp = _make_resp("是否股票相关:是\n需要实时查数:是\n数据方向:财务,估值")
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        state = graph.build_initial_state("问", "000858", "五粮液", "报告", [], None)
        out = graph.understand_node(state, writer)
        assert out["is_off_topic"] is False
        assert out["needs_tools"] is True
        assert out["tool_hints"] == ["财务", "估值"]

    def test_missing_field_falls_back_per_field(self, monkeypatch):
        """只输出部分字段：缺失字段取默认，其余字段正常"""
        writer = MagicMock()
        resp = _make_resp("是否股票相关：否")
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        state = graph.build_initial_state("今天天气如何", "000858", "五粮液", "报告", [], None)
        out = graph.understand_node(state, writer)
        assert out["is_off_topic"] is True
        assert out["needs_tools"] is False
        assert out["target_code"] == "000858"
        assert out["tool_hints"] == []

    def test_current_stock_keyword_uses_session_code(self, monkeypatch):
        """目标股票代码填"当前股票"→ 回退会话股票"""
        writer = MagicMock()
        resp = _make_resp("是否股票相关：是\n目标股票代码：当前股票\n需要实时查数：是")
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        state = graph.build_initial_state("问", "000858", "五粮液", "报告", [], None)
        out = graph.understand_node(state, writer)
        assert out["target_code"] == "000858"

    def test_no_hint_means_empty_list(self, monkeypatch):
        """数据方向填"无"→ 空列表"""
        writer = MagicMock()
        resp = _make_resp("是否股票相关：是\n需要实时查数：是\n数据方向：无")
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        state = graph.build_initial_state("问", "000858", "五粮液", "报告", [], None)
        out = graph.understand_node(state, writer)
        assert out["tool_hints"] == []

    def test_garbage_output_full_fallback(self, monkeypatch):
        """完全无标签的乱输出：不抛异常，字段全默认"""
        writer = MagicMock()
        resp = _make_resp("完全不相关的废话，没有任何标签")
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        state = graph.build_initial_state("问", "000858", "五粮液", "报告", [], None)
        out = graph.understand_node(state, writer)
        assert out["is_off_topic"] is False
        assert out["needs_tools"] is False
        assert out["target_code"] == "000858"
        assert out["tool_hints"] == []

    def test_parse_failure_falls_back_to_stock_related(self, monkeypatch):
        """LLM 调用异常：整体兜底（is_off_topic=False, needs_tools=False）"""
        writer = MagicMock()
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = Exception("LLM 500")
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        state = graph.build_initial_state("问", "000858", "五粮液", "报告", [], None)
        out = graph.understand_node(state, writer)
        assert out["is_off_topic"] is False
        assert out["needs_tools"] is False
        assert out["target_code"] == "000858"
        assert out["tool_hints"] == []

    def test_offtopic_but_needs_tools_degrades(self, monkeypatch):
        """矛盾守卫：LLM 判无关却要查数（自相矛盾）→ 降级为不 off_topic

        实证（2026-08-19）："分析一下该股票今日的时分线"被 LLM 误填
        "是否股票相关：否 + 需要实时查数：是"，旧代码触发 off_topic 拒绝。
        守卫：矛盾时相信查数意图（股票相关）。
        """
        writer = MagicMock()
        resp = _make_resp("是否股票相关：否\n需要实时查数：是\n数据方向：财务")
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        state = graph.build_initial_state("分析一下该股票今日的时分线", "301301", "川宁生物", "报告", [], None)
        out = graph.understand_node(state, writer)
        assert out["is_off_topic"] is False   # 守卫降级：矛盾时相信查数意图
        assert out["needs_tools"] is True


class TestLlmRoundNode:
    """llm_round 节点：首轮注入目标股票、干净 assistant 消息、失败兜底"""

    def test_injects_target_context_on_first_round(self, monkeypatch):
        resp = _make_resp("")
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        monkeypatch.setattr(graph, "get_tool_descriptions", lambda server: [])
        state = graph.build_initial_state("财报分析", "301301", "川宁生物", "报告", [], None)
        state["target_code"] = "600000"   # 跨股票提问：目标股 ≠ 会话股
        graph.llm_round_node(state)
        sent = fake_client.chat.completions.create.call_args.kwargs["messages"]
        assert "600000" in sent[0]["content"]
        assert "川宁生物" in sent[0]["content"]

    def test_appends_clean_assistant_with_tool_calls(self, monkeypatch):
        resp = _make_resp("", tool_calls=[_make_tool_call("search_news", {"query": "x"})])
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        monkeypatch.setattr(graph, "get_tool_descriptions", lambda server: [])
        state = graph.build_initial_state("问", "000858", "五粮液", "报告", [], None)
        out = graph.llm_round_node(state)
        last = out["messages"][-1]
        assert last["role"] == "assistant"
        assert last["tool_calls"][0]["function"]["name"] == "search_news"
        assert "reasoning_content" not in last

    def test_llm_failure_appends_closeout_message(self, monkeypatch):
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = Exception("API 500")
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        monkeypatch.setattr(graph, "get_tool_descriptions", lambda server: [])
        state = graph.build_initial_state("问", "000858", "五粮液", "报告", [], None)
        out = graph.llm_round_node(state)
        last = out["messages"][-1]
        assert last["role"] == "assistant"
        assert "tool_calls" not in last


class TestExecuteToolsNode:
    """execute_tools 节点：工具执行、records、事件、arguments 守卫"""

    def test_executes_tools_and_emits_events(self, monkeypatch):
        writer = MagicMock()
        monkeypatch.setattr(graph, "execute_tool_call",
                            lambda name, args: {"ok": True, "text": "财务数据"})
        state = graph.build_initial_state("财报分析", "000858", "五粮液", "报告", [], None)
        state["messages"].append({
            "role": "assistant", "content": "",
            "tool_calls": [{
                "id": "call_1", "type": "function",
                "function": {"name": "get_stock_financials",
                             "arguments": json.dumps({"query": "营收"})},
            }],
        })
        out = graph.execute_tools_node(state, writer)
        assert out["rounds"] == 1
        assert out["tool_results"] == "财务数据"
        assert out["tool_calls"][0]["name"] == "get_stock_financials"
        assert out["tool_calls"][0]["arguments"] == {"query": "营收"}
        assert writer.call_count == 2          # tool_start + tool_done
        assert out["messages"][-1]["role"] == "tool"
        assert out["messages"][-1]["content"] == "财务数据"

    def test_ok_false_propagates_to_records_and_events(self, monkeypatch):
        """工具返回 ok=False：tool_done 事件与 records 均透传 False，不做假成功"""
        writer = MagicMock()
        monkeypatch.setattr(graph, "execute_tool_call",
                            lambda name, args: {"ok": False, "text": "[无数据] x"})
        state = graph.build_initial_state("问", "000858", "五粮液", "报告", [], None)
        state["messages"].append({
            "role": "assistant", "content": "",
            "tool_calls": [{
                "id": "call_1", "type": "function",
                "function": {"name": "search_news", "arguments": json.dumps({"query": "x"})},
            }],
        })
        out = graph.execute_tools_node(state, writer)
        done_events = [c.args[0] for c in writer.call_args_list
                       if c.args[0]["type"] == "tool_done"]
        assert done_events and done_events[0]["ok"] is False
        assert out["tool_calls"][0]["ok"] is False

    def test_non_dict_arguments_wrapped(self, monkeypatch):
        writer = MagicMock()
        captured = {}

        def fake_exec(name, args):
            captured["args"] = args
            return {"ok": True, "text": "数据"}
        monkeypatch.setattr(graph, "execute_tool_call", fake_exec)
        state = graph.build_initial_state("问", "000858", "五粮液", "报告", [], None)
        state["messages"].append({
            "role": "assistant", "content": "",
            "tool_calls": [{
                "id": "call_1", "type": "function",
                "function": {"name": "search_news", "arguments": json.dumps("随便")},
            }],
        })
        graph.execute_tools_node(state, writer)
        assert captured["args"] == {"query": "随便"}


class TestAnswerNode:
    """answer 节点：off_topic 拒绝、空 content fallback、REPORT_ONLY 分支"""

    def test_off_topic_returns_rejection_no_phase(self):
        writer = MagicMock()
        state = graph.build_initial_state("今天天气如何", "000858", "五粮液", "报告", [], None)
        state["is_off_topic"] = True
        out = graph.answer_node(state, writer)
        assert out["answer_text"] == "karens暂时无法回答您这个问题哦？"
        writer.assert_not_called()

    def test_empty_content_fallback_and_disclaimer(self, monkeypatch):
        writer = MagicMock()
        resp = _make_resp("")
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        state = graph.build_initial_state("财报分析", "301301", "川宁生物", "报告", [], None)
        state["tool_results"] = "财务数据"
        out = graph.answer_node(state, writer)
        assert "抱歉" in out["answer_text"]
        assert "不构成投资建议" in out["answer_text"]
        writer.assert_called_once_with({"type": "phase", "phase": "answer"})

    def test_uses_report_only_when_no_tool_results(self, monkeypatch):
        writer = MagicMock()
        resp = _make_resp("报告解读内容")
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        state = graph.build_initial_state("报告说了什么", "000858", "五粮液", "报告", [], None)
        out = graph.answer_node(state, writer)
        assert "报告解读内容" in out["answer_text"]
        assert "不构成投资建议" in out["answer_text"]


class TestWorkflow:
    """真图流转：条件边循环、事件序列、轮次上限、off_topic/无工具路径"""

    def test_full_flow_event_sequence(self, monkeypatch):
        """带工具问答：phase understand → tool_start/tool_done → phase answer"""
        responses = [
            _make_resp("是否股票相关：是\n需要实时查数：是\n数据方向：财务"),
            _make_resp("", tool_calls=[_make_tool_call("get_stock_financials", {"query": "川宁生物营收"})]),
            _make_resp("好的，分析如下"),
            _make_resp("## 川宁生物财报分析\n营收 10.9 亿"),
        ]
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = responses
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        monkeypatch.setattr(graph, "execute_tool_call",
                            lambda name, args: {"ok": True, "text": "营收 10.9 亿"})
        monkeypatch.setattr(graph, "get_tool_descriptions",
                            lambda server: [{"name": "get_stock_financials",
                                             "description": "财务", "inputSchema": {}}])

        events = []
        final_answer = None
        initial = graph.build_initial_state("财报分析", "301301", "川宁生物", "报告", [], None)
        for mode, chunk in graph.qa_workflow().stream(initial, stream_mode=["custom", "updates"]):
            if mode == "custom":
                events.append(chunk)
            else:
                for node, upd in chunk.items():
                    if node == "answer" and upd.get("answer_text"):
                        final_answer = upd["answer_text"]

        types = [e["type"] for e in events]
        assert types[0] == "phase" and events[0]["phase"] == "understand"
        assert "tool_start" in types and "tool_done" in types
        assert types[-1] == "phase" and events[-1]["phase"] == "answer"
        assert "川宁生物财报分析" in final_answer

    def test_rounds_capped_at_max(self, monkeypatch):
        """LLM 一直要工具：循环在 MAX_TOOL_ROUNDS 轮后强制收尾"""
        responses = [
            _make_resp("是否股票相关：是\n需要实时查数：是"),
            *[_make_resp("", tool_calls=[_make_tool_call("search_news", {"query": "x"})])
              for _ in range(graph.MAX_TOOL_ROUNDS)],
            _make_resp("已收尾"),
            _make_resp("回答"),
        ]
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = responses
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        monkeypatch.setattr(graph, "execute_tool_call",
                            lambda name, args: {"ok": True, "text": "数据"})
        monkeypatch.setattr(graph, "get_tool_descriptions", lambda server: [])

        final = graph.qa_workflow().invoke(
            graph.build_initial_state("问", "000858", "五粮液", "报告", [], None))
        assert final["rounds"] == graph.MAX_TOOL_ROUNDS
        assert "回答" in final["answer_text"]

    def test_multi_round_tool_results_joined_with_separator(self, monkeypatch):
        """多轮工具：tool_results 轮与轮之间以 \\n\\n 分隔，两段数据顺序正确"""
        responses = [
            _make_resp("是否股票相关：是\n需要实时查数：是\n数据方向：财务"),
            _make_resp("", tool_calls=[_make_tool_call("search_news", {"query": "第一轮"})]),
            _make_resp("", tool_calls=[_make_tool_call("search_news", {"query": "第二轮"})]),
            _make_resp("收尾"),
            _make_resp("最终回答"),
        ]
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = responses
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        # 按工具参数区分轮次返回不同数据
        monkeypatch.setattr(graph, "execute_tool_call",
                            lambda name, args: {"ok": True,
                                                "text": "第一轮数据" if args.get("query") == "第一轮"
                                                        else "第二轮数据"})
        monkeypatch.setattr(graph, "get_tool_descriptions",
                            lambda server: [{"name": "search_news",
                                             "description": "资讯", "inputSchema": {}}])

        final = graph.qa_workflow().invoke(
            graph.build_initial_state("问", "000858", "五粮液", "报告", [], None))
        assert "第一轮数据\n\n第二轮数据" in final["tool_results"]

    def test_off_topic_path_no_tool_events(self, monkeypatch):
        """无关问题：仅 phase understand 事件，answer 返回拒绝文案"""
        responses = [
            _make_resp("是否股票相关：否"),
            _make_resp("回答"),
        ]
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = responses
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)

        initial = graph.build_initial_state("今天天气", "000858", "五粮液", "报告", [], None)
        events = [c for c in graph.qa_workflow().stream(initial, stream_mode="custom")]
        assert events == [{"type": "phase", "phase": "understand"}]

    def test_no_tools_only_phase_events(self, monkeypatch):
        """纯报告解读：仅两个 phase 事件"""
        responses = [
            _make_resp("是否股票相关：是\n需要实时查数：否"),
            _make_resp("报告解读"),
        ]
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = responses
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)

        events = []
        initial = graph.build_initial_state("报告说了什么", "000858", "五粮液", "报告", [], None)
        for mode, chunk in graph.qa_workflow().stream(initial, stream_mode=["custom", "updates"]):
            if mode == "custom":
                events.append(chunk)
        assert [e["type"] for e in events] == ["phase", "phase"]
        assert events[0]["phase"] == "understand"
        assert events[1]["phase"] == "answer"


class TestRunQaAgent:
    """run_qa_agent 同步薄封装"""

    def test_sync_wrapper_invokes_graph(self, monkeypatch):
        responses = [
            _make_resp("是否股票相关：是\n需要实时查数：否"),
            _make_resp("报告解读回答"),
        ]
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = responses
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)

        result = graph.run_qa_agent("报告说了什么", "000858", "五粮液", "报告", [], None)
        assert result["success"] is True
        assert "报告解读回答" in result["answer"]
        assert result["is_off_topic"] is False

    def test_sync_wrapper_error_fallback(self, monkeypatch):
        """answer 节点 LLM 异常（understand 已兜底不抛）→ 图抛 → success=False"""
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = Exception("boom")
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)

        result = graph.run_qa_agent("问", "000858", "五粮液", "报告", [], None)
        assert result["success"] is False
        assert "暂时遇到问题" in result["answer"]


class TestPrompts:
    """prompts 模板：应要求 LLM 不要输出免责声明（方案 B，2026-08-19 免责声明重复 bug）

    实证：投研模型常在回答末尾自己输出免责声明，若后端再无条件拼接 DISCLAIMER
    会导致免责声明重复。方案 B 在 prompt 源头抑制；本测试防止将来删掉该要求。
    """

    def test_answer_prompt_instructs_no_disclaimer(self):
        from chat_agent.prompts import ANSWER_PROMPT
        assert "不添加免责声明" in ANSWER_PROMPT

    def test_report_only_prompt_instructs_no_disclaimer(self):
        from chat_agent.prompts import REPORT_ONLY_PROMPT
        assert "不要输出免责声明" in REPORT_ONLY_PROMPT
