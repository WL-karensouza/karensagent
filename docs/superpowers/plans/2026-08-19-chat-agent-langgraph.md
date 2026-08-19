# karens 问答助理 LangGraph 迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `chat_agent` 编排层从手写命令式流程迁移为纯 LangGraph 图（4 节点 + 2 条件边），替换手写 `for` 循环与线程桥接，保持前端事件协议零改动。

**Architecture:** LangGraph `StateGraph` + `TypedDict` 状态；4 节点（understand → llm_round ⇄ execute_tools → answer）；工具循环用条件边表达；节点内保留原生 OpenAI SDK 调 DeepSeek（thinking 参数）；事件用 `StreamWriter` + `stream_mode="custom"` 推送；`_stream_events` 改异步驱动图，去掉 `run_in_executor` 线程 + `asyncio.Queue` 桥接。

**Tech Stack:** langgraph 1.2.9（环境已装）、openai（保留，不引入 langchain-openai）、FastAPI、pytest。

## Global Constraints

（来自 `docs/superpowers/specs/2026-08-19-chat-agent-langgraph-design.md`，每个 Task 隐含包含本节）

1. 编排用 LangGraph（`StateGraph` + `TypedDict`），LLM 调用层保留原生 OpenAI SDK（`chat.completions.create` + `extra_body={"thinking": ...}`）。
2. 前端事件协议不变：`phase` / `tool_start` / `tool_done` / `delta` / `done` / `error`；`routers/chat.py` 的 `_build_report_context` / `_chunk_text` / 落库逻辑保留。
3. `MAX_TOOL_ROUNDS = 4` 保留；条件边 `state["rounds"] < MAX_TOOL_ROUNDS` 才回环。
4. 保留 2026-08-19 修复：`execute_tool_call` 假成功判定（`ok=False`）、answer 空 content fallback 文案、`_build_tools_for`、`_format_history`、arguments 非 dict 包成 `{"query": ...}` 守卫。
5. 目标股票上下文注入 `llm_round` **首轮**（`rounds == 0`）执行：`messages[0]` 替换为 `f"当前对话股票目标：{target_code}（{stock_name}）。问题：{question}"`（跨股票提问时 `target_code` 可能 ≠ `stock_code`）。
6. `understand` 节点 `thinking` disabled（`max_tokens=500`）；`llm_round`/`answer` `thinking` enabled（`max_tokens=2048` / `16000`）。
7. 测试 mock 策略：`patch` `graph._get_client()` 返回假 client（`side_effect` 控制 LLM 响应序列），**真图跑通**。
8. 中文注释；commit message 用中文一句话。
9. 前端零改动；本迁移不引入 langchain-openai。

---

### Task 1: graph.py 状态与节点层（QaState / build_initial_state / 4 节点）

**Files:**
- Modify: `backend/chat_agent/graph.py`（新增状态与 4 个节点函数，**保留旧函数不动**）
- Rewrite: `backend/tests/test_chat_agent_graph.py`（替换为节点单测）

**Interfaces:**
- Produces:
  - `class QaState(TypedDict)` — 13 字段状态
  - `build_initial_state(question, stock_code, stock_name, report_context, tool_hints, history=None) -> dict`
  - `understand_node(state, writer) -> dict`
  - `llm_round_node(state) -> dict`
  - `execute_tools_node(state, writer) -> dict`
  - `answer_node(state, writer) -> dict`
  - 依赖既有：`_get_client()`、`_format_history(history)`、`_build_tools_for(tool_hints)`、`TOOL_FRIENDLY_NAMES`、`execute_tool_call(name, args)`、`MAX_TOOL_ROUNDS`（Task 2 消费全部）

- [ ] **Step 1: 重写 test_chat_agent_graph.py 为节点单测**

```python
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
    """understand 节点：解析、JSON 包裹剥离、异常兜底"""

    def test_parses_json_and_maps_fields(self, monkeypatch):
        writer = MagicMock()
        resp = _make_resp('{"is_off_topic": false, "stock_code": "000858", '
                          '"needs_tools": true, "tool_hints": ["财务"]}')
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        state = graph.build_initial_state("财报分析", "000858", "五粮液", "报告", [], None)
        out = graph.understand_node(state, writer)
        assert out["needs_tools"] is True
        assert out["target_code"] == "000858"
        assert out["tool_hints"] == ["财务"]
        writer.assert_called_once_with({"type": "phase", "phase": "understand"})

    def test_strips_code_fence(self, monkeypatch):
        writer = MagicMock()
        resp = _make_resp('```json\n{"is_off_topic": false, "needs_tools": false}\n```')
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        state = graph.build_initial_state("问", "000858", "五粮液", "报告", [], None)
        out = graph.understand_node(state, writer)
        assert out["needs_tools"] is False

    def test_parse_failure_falls_back_to_stock_related(self, monkeypatch):
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd /d/karensAgent/backend && python -m pytest tests/test_chat_agent_graph.py -q`
Expected: FAIL —— `ImportError: cannot import name 'understand_node' from 'chat_agent.graph'`

- [ ] **Step 3: graph.py 新增状态与 4 个节点函数**

在 `backend/chat_agent/graph.py` 顶部补充 import（放在 `from datetime import datetime` 后）：

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import StreamWriter
```

在 `MAX_TOOL_ROUNDS = 4` 之后插入（**不要删除任何现有函数**）：

```python
class QaState(TypedDict):
    """LangGraph 工作流状态"""
    # 输入（build_initial_state 一次注入）
    question: str
    stock_code: str          # 会话绑定股票（报告锚点，始终保持）
    stock_name: str
    report_context: str
    history: list[dict]      # 最近 8 轮 [{role, content}]
    tool_hints: list[str]    # understand 失败兜底方向
    # understand 产出
    is_off_topic: bool
    needs_tools: bool
    target_code: str         # 跨股票提问时 ≠ stock_code
    # tool 循环维护
    messages: list[dict]     # OpenAI 格式对话（首条为纯问题，含工具结果回填）
    tool_results: str        # 拼接的工具文本（喂 answer）
    tool_calls: list[dict]   # records [{name, label, ok, duration_ms, arguments}]
    rounds: int              # 已执行工具轮数（替换 for 循环计数器）
    # answer 产出
    answer_text: str


def build_initial_state(question, stock_code, stock_name, report_context,
                        tool_hints, history=None) -> dict:
    """构建初始 state（messages 仅含纯问题；目标股票上下文由 llm_round 首轮注入）"""
    return {
        "question": question,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "report_context": report_context,
        "history": history or [],
        "tool_hints": tool_hints,
        "is_off_topic": False,
        "needs_tools": False,
        "target_code": stock_code,
        "messages": [{"role": "user", "content": question}],
        "tool_results": "",
        "tool_calls": [],
        "rounds": 0,
        "answer_text": "",
    }
```

在 `run_qa_agent` 定义之前插入（`_understand` / `_tool_loop` / `_answer` 保留，Task 2 删除）：

```python
def understand_node(state: QaState, writer: StreamWriter) -> dict:
    """意图理解节点：发 phase understand 事件，产出意图分析结果"""
    from .prompts import UNDERSTAND_PROMPT

    writer({"type": "phase", "phase": "understand"})
    now = datetime.now()
    prompt = UNDERSTAND_PROMPT.format(
        question=state["question"], stock_code=state["stock_code"],
        stock_name=state["stock_name"], today_str=now.strftime("%Y-%m-%d"),
    )
    try:
        resp = _get_client().chat.completions.create(
            model=LLM_MODEL_ID, max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
            extra_body={"thinking": {"type": "disabled"}},  # 意图分析求快
        )
        text = resp.choices[0].message.content or ""
        # 剥离 ```json 包裹（先处理 ```json 再处理 ```，避免 json 前缀残留）
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0]
        data = json.loads(text.strip())
        return {
            "is_off_topic": bool(data.get("is_off_topic", False)),
            "needs_tools": bool(data.get("needs_tools", False)),
            "target_code": data.get("stock_code") or state["stock_code"],
            "tool_hints": data.get("tool_hints", []),
        }
    except Exception as e:
        print(f"[chat_agent] [警告] 意图理解失败，默认按股票相关处理: {e}")
        return {
            "is_off_topic": False,
            "needs_tools": False,
            "target_code": state["stock_code"],
            "tool_hints": [],
        }


def llm_round_node(state: QaState) -> dict:
    """单轮 Function Calling：调用 LLM，产出本轮 tool_calls 或收尾消息

    首轮（rounds == 0）把 messages[0] 替换为目标股票上下文（含证券实体名，
    2026-08-19 根因修复）；target_code 由 understand 产出，跨股票提问时 ≠ stock_code。
    """
    tools = _build_tools_for(state["tool_hints"])
    messages = list(state["messages"])
    if state["rounds"] == 0:
        messages = [{
            "role": "user",
            "content": (f"当前对话股票目标：{state['target_code']}"
                        f"（{state['stock_name']}）。问题：{state['question']}"),
        }] + messages[1:]
    try:
        resp = _get_client().chat.completions.create(
            model=LLM_MODEL_ID, messages=messages, tools=tools,
            max_tokens=2048,
            extra_body={"thinking": {"type": "enabled"}},
            temperature=1.0,
        )
        msg = resp.choices[0].message
        tool_calls = msg.tool_calls or []
        if not tool_calls:
            # 收尾：无工具调用
            return {"messages": messages + [{"role": "assistant", "content": msg.content or ""}]}
        # 干净 assistant 消息：只保留 OpenAI 兼容字段，剔除 reasoning_content
        return {"messages": messages + [{
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id, "type": tc.type,
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        }]}
    except Exception as e:
        # LLM 调用失败：本轮无工具，避免死循环，走 answer
        print(f"[chat_agent] [警告] 工具循环 LLM 调用失败: {e}")
        return {"messages": messages + [{"role": "assistant", "content": ""}]}


def execute_tools_node(state: QaState, writer: StreamWriter) -> dict:
    """执行本轮全部工具调用：发 tool_start/tool_done，累积 records 与 tool_results"""
    import time as _t

    last = state["messages"][-1]
    calls = last.get("tool_calls") or []
    messages = list(state["messages"])
    records = list(state["tool_calls"])
    results_parts = []

    for tc in calls:
        name = tc["function"]["name"]
        label = TOOL_FRIENDLY_NAMES.get(name, name)
        writer({"type": "tool_start", "name": name, "label": label})
        try:
            args = json.loads(tc["function"]["arguments"])
        except Exception:
            args = {}
        # 边界守卫：LLM 返回的 arguments 可能是不可信的非 dict，统一包成 {"query": ...}
        if not isinstance(args, dict):
            args = {"query": str(args)}
        t0 = _t.time()
        out = execute_tool_call(name, args)
        dt = int((_t.time() - t0) * 1000)
        writer({"type": "tool_done", "name": name, "label": label, "ok": out["ok"]})
        records.append({
            "name": name, "label": label, "ok": out["ok"],
            "duration_ms": dt, "arguments": args,
        })
        results_parts.append(out["text"])
        messages.append({"role": "tool", "tool_call_id": tc["id"], "content": out["text"]})

    return {
        "messages": messages,
        "tool_results": (state["tool_results"] + "\n\n".join(results_parts)
                         if results_parts else state["tool_results"]),
        "tool_calls": records,
        "rounds": state["rounds"] + 1,
    }


def answer_node(state: QaState, writer: StreamWriter) -> dict:
    """生成最终回答：off_topic 拒绝（不发 phase）；否则发 phase answer 事件 + 正文"""
    from .prompts import ANSWER_PROMPT, REPORT_ONLY_PROMPT, DISCLAIMER

    if state["is_off_topic"]:
        return {"answer_text": "karens暂时无法回答您这个问题哦？"}

    writer({"type": "phase", "phase": "answer"})

    history_text = _format_history(state["history"])
    # 跨股票提问时标注目标股票，让 LLM 把工具数据归属到目标股票；同股则留空
    target_line = (f"目标股票：{state['target_code']}"
                   if state["target_code"] != state["stock_code"] else "")
    tool_results = state["tool_results"].strip()

    if tool_results:
        prompt = ANSWER_PROMPT.format(
            question=state["question"], stock_code=state["stock_code"],
            stock_name=state["stock_name"], target_line=target_line,
            report_context=state["report_context"], tool_results=tool_results,
            history=history_text,
        )
    else:
        prompt = REPORT_ONLY_PROMPT.format(
            question=state["question"], stock_code=state["stock_code"],
            stock_name=state["stock_name"], target_line=target_line,
            report_context=state["report_context"], history=history_text,
        )

    resp = _get_client().chat.completions.create(
        model=LLM_MODEL_ID, messages=[{"role": "user", "content": prompt}],
        # max_tokens 放大（2026-08-19）：工具结果可达 1.3 万字符，4096 偶发耗尽
        max_tokens=16000,
        extra_body={"thinking": {"type": "enabled"}},
        temperature=1.0,
    )
    answer = resp.choices[0].message.content or ""
    # 兜底（2026-08-19）：思考完成但正文为空时给友好提示而非只拼免责声明
    if not answer.strip():
        answer = "抱歉，我未能获取到足够的实时数据来完成这次分析，请换个问法或稍后再试。"
    return {"answer_text": answer + DISCLAIMER}
```

注意：`graph.py` 需在顶部已有 `from typing import TypedDict` 与 `from datetime import datetime`。若 `TypedDict` 未导入，在 import 区补充 `from typing import TypedDict`。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd /d/karensAgent/backend && python -m pytest tests/test_chat_agent_graph.py -q`
Expected: PASS（14 tests）

- [ ] **Step 5: 提交**

```bash
git add backend/chat_agent/graph.py backend/tests/test_chat_agent_graph.py
git commit -m "feat(chat_agent): LangGraph 迁移——状态与四节点层"
```

---

### Task 2: graph.py 图层（条件边 / 编译 / run_qa_agent 切换 / 删旧函数）

**Files:**
- Modify: `backend/chat_agent/graph.py`（条件边 + 图编译 + run_qa_agent 切换，删除 `_understand`/`_tool_loop`/`_answer`）
- Modify: `backend/tests/test_chat_agent_graph.py`（追加图流转测试）

**Interfaces:**
- Consumes: Task 1 的 `QaState` / `build_initial_state` / 4 节点
- Produces:
  - `decide_after_understand(state) -> str`
  - `decide_after_llm(state) -> str`
  - `create_qa_workflow() -> CompiledStateGraph`
  - `qa_workflow() -> CompiledStateGraph`（编译单例缓存）
  - `run_qa_agent(question, stock_code, stock_name, report_context, tool_hints, history=None) -> dict`（薄封装，**移除 on_event 参数**，Task 3 消费）

- [ ] **Step 1: 追加图流转测试到 test_chat_agent_graph.py**

在文件末尾追加：

```python
class TestWorkflow:
    """真图流转：条件边循环、事件序列、轮次上限、off_topic/无工具路径"""

    def test_full_flow_event_sequence(self, monkeypatch):
        """带工具问答：phase understand → tool_start/tool_done → phase answer"""
        responses = [
            _make_resp('{"is_off_topic": false, "needs_tools": true, "tool_hints": ["财务"]}'),
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
            _make_resp('{"is_off_topic": false, "needs_tools": true}'),
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

    def test_off_topic_path_no_tool_events(self, monkeypatch):
        """无关问题：仅 phase understand 事件，answer 返回拒绝文案"""
        responses = [
            _make_resp('{"is_off_topic": true}'),
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
            _make_resp('{"is_off_topic": false, "needs_tools": false}'),
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
            _make_resp('{"is_off_topic": false, "needs_tools": false}'),
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd /d/karensAgent/backend && python -m pytest tests/test_chat_agent_graph.py -q`
Expected: FAIL —— `AttributeError: module 'chat_agent.graph' has no attribute 'qa_workflow'`（节点测试仍 PASS）

- [ ] **Step 3: graph.py 实现图层 + 切换 run_qa_agent + 删旧函数**

在 `answer_node` 之后、`run_qa_agent` 之前插入：

```python
def decide_after_understand(state: QaState) -> str:
    """understand 后：off_topic 或不需要工具 → answer；否则 → llm_round"""
    if state["is_off_topic"] or not state["needs_tools"]:
        return "answer"
    return "llm_round"


def decide_after_llm(state: QaState) -> str:
    """llm_round 后：本轮有工具调用 且 未达轮次上限 → execute_tools；否则 → answer"""
    last = state["messages"][-1]
    has_calls = bool(last.get("tool_calls")) and state["rounds"] < MAX_TOOL_ROUNDS
    return "execute_tools" if has_calls else "answer"


def create_qa_workflow():
    """构建并编译 QA 工作流（4 节点 + 2 条件边）"""
    wf = StateGraph(QaState)
    wf.add_node("understand", understand_node)
    wf.add_node("llm_round", llm_round_node)
    wf.add_node("execute_tools", execute_tools_node)
    wf.add_node("answer", answer_node)
    wf.add_edge(START, "understand")
    wf.add_conditional_edges("understand", decide_after_understand)
    wf.add_conditional_edges("llm_round", decide_after_llm)
    wf.add_edge("execute_tools", "llm_round")
    wf.add_edge("answer", END)
    return wf.compile()


_compiled_workflow = None


def qa_workflow():
    """获取编译后的工作流（单例缓存，避免每次调用重建）"""
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = create_qa_workflow()
    return _compiled_workflow
```

**删除旧函数** `_understand` / `_tool_loop` / `_answer`（保留 `_format_history` 与 `_build_tools_for`）。

**重写 `run_qa_agent`** 为薄封装（替换原定义，**移除 `on_event` 参数**）：

```python
def run_qa_agent(question: str, stock_code: str, stock_name: str,
                 report_context: str, tool_hints: list[str],
                 history: list[dict] | None = None) -> dict:
    """同步执行完整问答（LangGraph 薄封装）

    流式路径由 routers/chat.py 直接调用 qa_workflow().astream()；
    本函数供同步调用/测试/诊断，返回结构保持兼容。

    Returns:
        {
            "answer": str,
            "is_off_topic": bool,
            "tool_calls": list[dict],   # [{name, label, ok, duration_ms, arguments}]
            "success": bool,
            "error": str,
        }
    """
    try:
        initial = build_initial_state(question, stock_code, stock_name,
                                      report_context, tool_hints, history)
        result = qa_workflow().invoke(initial)
        return {
            "answer": result["answer_text"],
            "is_off_topic": result["is_off_topic"],
            "tool_calls": result["tool_calls"],
            "success": True,
            "error": "",
        }
    except Exception as e:
        print(f"[chat_agent] [错误] run_qa_agent 失败: {e}")
        return {
            "answer": f"karens 暂时遇到问题，请稍后重试。（{type(e).__name__}）",
            "is_off_topic": False,
            "tool_calls": [],
            "success": False,
            "error": str(e),
        }
```

- [ ] **Step 4: 跑全量 graph 测试确认通过**

Run: `cd /d/karensAgent/backend && python -m pytest tests/test_chat_agent_graph.py -q`
Expected: PASS（18 tests：14 节点 + 4 图流转 + 2 run_qa_agent = 20？以实际计数为准，全部 PASS）

- [ ] **Step 5: 提交**

```bash
git add backend/chat_agent/graph.py backend/tests/test_chat_agent_graph.py
git commit -m "feat(chat_agent): LangGraph 迁移——条件边图编译与 run_qa_agent 切换"
```

---

### Task 3: routers/chat.py `_stream_events` 重写 + 测试适配

**Files:**
- Modify: `backend/chat_agent/routers/chat.py`（`_stream_events` 改异步驱动图，import 更新）
- Rewrite: `backend/tests/test_chat_agent_chat.py`（真图 + mock LLM client）

**Interfaces:**
- Consumes: Task 2 的 `qa_workflow()` / `build_initial_state`
- Produces: `_stream_events` 改为异步驱动图，前端协议不变

- [ ] **Step 1: 重写 test_chat_agent_chat.py**

```python
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
        with patch.object(chat, "add_message", lambda *a, **k: None) as add_msg:
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
        with patch.object(chat, "add_message", lambda *a, **k: None) as add_msg:
            events = _collect(chat._stream_events(session, req, "000858", "报告", []))

        assert events[0]["type"] == "error"
        assert "boom" in events[0]["message"]
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd /d/karensAgent/backend && python -m pytest tests/test_chat_agent_chat.py -q`
Expected: FAIL（`_stream_events` 仍走旧 `run_qa_agent` 路径，新测试因缺 `graph._get_client` 行为不符而失败；以首个断言失败为准）

- [ ] **Step 3: 重写 routers/chat.py**

更新 import（第 13 行附近）：

```python
from ..graph import build_initial_state, qa_workflow
```

（删除 `from ..graph import run_qa_agent` 与未使用的 `from ..tools import TOOL_FRIENDLY_NAMES`；确认 TOOL_FRIENDLY_NAMES 在文件内无其他使用再删。）

**重写 `_stream_events`**（替换原实现，其余 `ask` / `get_chat_session` / `_build_report_context` / `_chunk_text` 不动）：

```python
async def _stream_events(session, req, stock_code, report_context, history):
    """产事件 dict 的异步生成器：异步驱动 LangGraph 图

    - 节点内 StreamWriter 发 phase/tool_start/tool_done（stream_mode="custom" 实时透传）
    - 图结束后由本函数发 delta×N + done（成功）或 error（图异常）
    """
    initial = build_initial_state(
        req.question, stock_code, req.stock_name or session["stock_name"],
        report_context, [], history,
    )
    final_answer = None
    tool_calls = []
    try:
        async for mode, chunk in qa_workflow().astream(
                initial, stream_mode=["custom", "updates"]):
            if mode == "custom":
                yield chunk            # phase / tool_start / tool_done 原样透传
            else:                      # updates：每节点结束后的 state 更新
                for node, upd in chunk.items():
                    if node == "answer" and upd.get("answer_text"):
                        final_answer = upd["answer_text"]
                    if node == "execute_tools":
                        tool_calls = upd.get("tool_calls", tool_calls)
    except Exception as e:
        print(f"[chat_agent] [错误] 问答图执行失败: {e}")
        msg = f"karens 暂时遇到问题，请稍后重试。（{type(e).__name__}）"
        yield {"type": "error", "message": msg}
        add_message(session["id"], "assistant", msg, None)
        return

    if not final_answer:
        final_answer = "抱歉，我未能获取到足够的实时数据来完成这次分析，请换个问法或稍后再试。"

    for chunk in _chunk_text(final_answer):
        yield {"type": "delta", "text": chunk}
        await asyncio.sleep(0.02)
    yield {"type": "done", "full": final_answer}
    add_message(session["id"], "assistant", final_answer, tool_calls or None)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd /d/karensAgent/backend && python -m pytest tests/test_chat_agent_chat.py -q`
Expected: PASS（3 tests）

- [ ] **Step 5: 提交**

```bash
git add backend/chat_agent/routers/chat.py backend/tests/test_chat_agent_chat.py
git commit -m "refactor(chat_agent): _stream_events 改异步驱动 LangGraph 去线程桥接"
```

---

### Task 4: requirements + 全量回归

**Files:**
- Modify: `backend/requirements.txt`
- 无测试改动

- [ ] **Step 1: requirements.txt 补 langgraph**

在 `backend/requirements.txt` 末尾追加一行：

```
langgraph>=1.2.9
```

（`langchain-openai` 已在环境，但本迁移**不引入**，不声明。）

- [ ] **Step 2: 后端全量测试**

Run: `cd /d/karensAgent/backend && python -m pytest -q`
Expected: PASS（`test_chat_agent_graph.py` 18+、`test_chat_agent_chat.py` 3、`test_chat_agent_tools.py` 2、`test_skill_extract.py` 8 等，全部通过）

- [ ] **Step 3: 前端 build 回归（确认未误伤）**

Run: `cd /d/karensAgent/frontend && npm run build`
Expected: 构建成功（前端零改动，仅回归确认）

- [ ] **Step 4: 提交**

```bash
git add backend/requirements.txt
git commit -m "chore(chat_agent): requirements 补 langgraph 依赖"
```

---

## 实施后验证（非测试，手动）

重启后端后，浏览器实测"该公司的财报进行分析一下"：
1. 思考面板三行正常显示（phase understand → 工具行 → phase answer）
2. 财报分析返回完整数据（非空、非仅免责声明）
3. 聊天自动滚动到底部
4. 工具行合并逻辑不回归（连续相同工具只显示一行）
