# AI 问答思考过程三行面板 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 karens 问答助理在提问后实时展示"理解问题 → 工具调用 → 生成回答"的三行思考过程面板，最终回答出现时面板闭合消失、不可点击、历史不留痕。

**Architecture:** 事件级流式——后端 `run_qa_agent` 加 `on_event` 回调在各阶段插桩，`chat.py` 用 `asyncio.Queue` 桥接后台线程与 SSE 协程实现阶段事件实时推送；前端新增 `ThinkingStepsCard` 三行面板，由 store 的 `chatSteps` 数组驱动，首个 `delta` 到达时清空触发闭合动画。

**Tech Stack:** 后端 Python/FastAPI/OpenAI SDK（同步调用，不启用 stream）；前端 Vue 3 + Pinia + vitest；SSE 事件协议扩展。

## Global Constraints

（源自 `docs/superpowers/specs/2026-08-18-thinking-stream-design.md`，每个任务隐式包含）

- **不改 LLM 真流式**：三处 `chat.completions.create` 均不传 `stream=True`，`reasoning_content` 不输出
- **思考内容 = 定制阶段文案**：理解行固定"正在理解问题…"，生成行固定"正在生成回答…"，工具行动态 `"正在{label}…"`
- **工具行 label 来源**：`backend/chat_agent/tools.py` 的 `TOOL_FRIENDLY_NAMES`，查不到时回退工具接口名
- **闭合时机**：首个 `delta` 事件到达时，store 清空 `chatSteps`
- **面板不可点击、闭合后不可回看**：`ThinkingStepsCard` 无任何交互元素；历史消息（`ChatMessageItem`）不渲染 `tool_calls`
- **不新增数据库字段**：`chat_messages.tool_calls` 保留落库，前端不渲染
- **SSE 事件协议**：`phase`（phase:understand|answer）/ `tool_start` / `tool_done` / `delta` / `done` / `error`；`thinking` 事件废弃
- **错误与中断兜底**：`onError` / `onStreamEnd` 也必须清空 `chatSteps`
- 命名：前端变量 camelCase / 组件 PascalCase；后端 Python snake_case

## 文件结构

| 文件 | 职责 | 动作 |
|---|---|---|
| backend/chat_agent/graph.py | 问答工作流，插桩 on_event | 修改 |
| backend/chat_agent/routers/chat.py | SSE 接口，队列桥接 | 修改 |
| backend/tests/test_chat_agent_graph.py | graph 插桩事件测试 | 新增 |
| backend/tests/test_chat_agent_chat.py | chat 队列桥接测试 | 新增 |
| frontend/src/api/index.js | SSE 解析扩展 | 修改 |
| frontend/src/stores/stock.js | `chatSteps` 状态 + `askChat` 改造 | 修改 |
| frontend/src/stores/chat-steps.test.js | askChat 事件映射测试 | 新增 |
| frontend/src/components/report/ThinkingStepsCard.vue | 三行面板组件 | 新增 |
| frontend/src/components/report/AiChatPanel.vue | 接入新面板 | 修改 |
| frontend/src/components/report/AiStepsCard.vue | 旧步骤卡片 | 删除 |

任务顺序：Task 1-2 后端（graph 插桩 → chat 桥接）→ Task 3-5 前端（api → store → 组件）→ Task 6 联调回归。每个任务独立可测、独立提交。

---

### Task 1: 后端 graph.py 事件插桩

**Files:**
- Modify: `backend/chat_agent/graph.py`
- Test: `backend/tests/test_chat_agent_graph.py`（新建）

**Interfaces:**
- Consumes: `run_qa_agent(question, stock_code, stock_name, report_context, tool_hints, history=None)`（现有签名）
- Produces:
  - `run_qa_agent(..., on_event=None)` —— 新增第 7 参数，回调签名 `on_event(evt: dict)`
  - `_tool_loop(question, target_code, tool_hints, on_event=None)` —— 新增第 4 参数
  - 事件结构：`{"type":"phase","phase":"understand"}` / `{"type":"phase","phase":"answer"}` / `{"type":"tool_start","name":...,"label":...}` / `{"type":"tool_done","name":...,"label":...,"ok":bool}`
  - 返回结构不变（`{answer, is_off_topic, tool_calls, success, error}`），`on_event=None` 时行为与现状完全一致

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_chat_agent_graph.py`：

```python
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

        def fake_tool_loop(question, target_code, hints, on_event=None):
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
        """无关问题：至少发出 understand 阶段事件，answer 阶段事件由主流程决定"""
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
```

- [ ] **Step 2: 跑测试验证失败**

```bash
cd d:/karensAgent/backend && python -m pytest tests/test_chat_agent_graph.py -v
```
Expected: FAIL —— `TypeError: run_qa_agent() got an unexpected keyword argument 'on_event'`

- [ ] **Step 3: 实现插桩**

修改 `backend/chat_agent/graph.py`：

1. `_tool_loop` 签名加 `on_event=None`，循环内每个工具调用**前**发 `tool_start`、**后**发 `tool_done`（在 [graph.py:126](backend/chat_agent/graph.py#L126) 的 `for tc in tool_calls:` 循环内）：
```python
def _tool_loop(question, target_code, tool_hints, on_event=None):
    ...
    for tc in tool_calls:
        if on_event is not None:
            on_event({"type": "tool_start", "name": tc.function.name,
                      "label": TOOL_FRIENDLY_NAMES.get(tc.function.name, tc.function.name)})
        try:
            args = json.loads(tc.function.arguments)
        except Exception:
            args = {}
        ...
        out = execute_tool_call(tc.function.name, args)
        ...
        if on_event is not None:
            on_event({"type": "tool_done", "name": tc.function.name,
                      "label": TOOL_FRIENDLY_NAMES.get(tc.function.name, tc.function.name),
                      "ok": out["ok"]})
```

2. `run_qa_agent` 签名加 `on_event=None`，在两处插桩 phase 事件：
```python
def run_qa_agent(question, stock_code, stock_name, report_context,
                 tool_hints, history=None, on_event=None):
    ...
    try:
        if on_event is not None:
            on_event({"type": "phase", "phase": "understand"})
        und = _understand(question, stock_code, stock_name)
        ...
        if needs_tools:
            hints = und["tool_hints"] or tool_hints
            tool_results, records = _tool_loop(question, target_code, hints,
                                               on_event=on_event)
        if on_event is not None:
            on_event({"type": "phase", "phase": "answer"})
        answer = _answer(...)
```

- [ ] **Step 4: 跑测试验证通过**

```bash
cd d:/karensAgent/backend && python -m pytest tests/test_chat_agent_graph.py -v
```
Expected: PASS（6 个用例全绿）

- [ ] **Step 5: 回归现有测试**

```bash
cd d:/karensAgent/backend && python -m pytest tests/ -q --ignore=tests/probe_results
```
Expected: 无新增失败（graph 改动只新增参数，不改变默认行为）

- [ ] **Step 6: Commit**

```bash
git add backend/chat_agent/graph.py backend/tests/test_chat_agent_graph.py
git commit -m "feat(chat_agent): run_qa_agent 事件插桩（phase/tool_start/tool_done）"
```

---

### Task 2: 后端 chat.py 队列桥接（阶段事件实时推送）

**Files:**
- Modify: `backend/chat_agent/routers/chat.py`
- Test: `backend/tests/test_chat_agent_chat.py`（新建）

**Interfaces:**
- Consumes:
  - `run_qa_agent(question, stock_code, stock_name, report_context, tool_hints, history=None, on_event=None)`（Task 1 产出）
  - 现有 `get_or_create_session` / `update_session_report` / `add_message` / `list_messages` / `_build_report_context` / `_chunk_text` / `_sse`
- Produces:
  - `async def _stream_events(session, req, stock_code, report_context, history) -> AsyncIterator[dict]` —— 产事件 **dict**（非 SSE 字符串），供 `ask()` 包成 `StreamingResponse`
  - 事件序列契约：线程内实时 `phase`/`tool_start`/`tool_done`；线程结束后 `error`（失败时）或 `delta`×N + `done`（成功时）；失败时**不发 delta/done**

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_chat_agent_chat.py`：

```python
"""chat_agent.routers.chat 队列桥接测试"""
import asyncio
from unittest.mock import patch

from chat_agent.routers import chat


def _collect(events_async_gen):
    """跑 async generator 收集事件列表（不需要 pytest-asyncio）"""
    return asyncio.run([e async for e in events_async_gen])


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
```

- [ ] **Step 2: 跑测试验证失败**

```bash
cd d:/karensAgent/backend && python -m pytest tests/test_chat_agent_chat.py -v
```
Expected: FAIL —— `AttributeError: module 'chat_agent.routers.chat' has no attribute '_stream_events'`

- [ ] **Step 3: 实现队列桥接**

修改 `backend/chat_agent/routers/chat.py`：

1. 新增 `_stream_events`（放在 `_build_report_context` 附近）：
```python
async def _stream_events(session, req, stock_code, report_context, history):
    """产事件 dict 的异步生成器：后台线程跑问答，主协程实时转发队列事件

    - 线程内 on_event 发出 phase/tool_start/tool_done（实时）
    - 线程结束后由主协程发 error（失败）或 delta×N + done（成功）
    """
    queue = asyncio.Queue()

    def emit(evt):
        queue.put_nowait(evt)  # put_nowait 线程安全

    loop = asyncio.get_running_loop()
    task = loop.run_in_executor(
        None,
        lambda: run_qa_agent(
            req.question, stock_code, req.stock_name or session["stock_name"],
            report_context, [], history, on_event=emit,
        ),
    )

    # 实时转发线程内事件，直到线程结束且队列排空
    while not task.done() or not queue.empty():
        try:
            evt = queue.get_nowait()
        except asyncio.QueueEmpty:
            await asyncio.sleep(0.02)
            continue
        yield evt

    result = task.result()
    if not result["success"]:
        yield {"type": "error", "message": result["answer"]}
        add_message(session["id"], "assistant", result["answer"], None)
        return

    # tool_start/tool_done 已在线程内实时发出，此处不再重发
    answer = result["answer"]
    for chunk in _chunk_text(answer):
        yield {"type": "delta", "text": chunk}
        await asyncio.sleep(0.02)
    yield {"type": "done", "full": answer}
    add_message(session["id"], "assistant", answer, result["tool_calls"] or None)
```

2. `ask()` 里替换 `gen()` 与事件发送逻辑：删除原 `gen()` 中的 `_sse({"type": "thinking"})`、`run_in_executor` 手动结果处理、`for tc in result["tool_calls"]` 循环，改为直接消费 `_stream_events`：
```python
@router.post("/{stock_code}/ask")
async def ask(stock_code: str, req: AskRequest):
    session = get_or_create_session(stock_code, req.stock_name)
    if req.report_id:
        update_session_report(session["id"], req.report_id)
    report_context = _build_report_context(req.report_id, stock_code)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in list_messages(session["id"])[-16:]
    ]
    add_message(session["id"], "user", req.question)

    async def gen():
        async for evt in _stream_events(session, req, stock_code, report_context, history):
            yield _sse(evt)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 4: 跑测试验证通过**

```bash
cd d:/karensAgent/backend && python -m pytest tests/test_chat_agent_chat.py -v
```
Expected: PASS（3 个用例全绿）

- [ ] **Step 5: Commit**

```bash
git add backend/chat_agent/routers/chat.py backend/tests/test_chat_agent_chat.py
git commit -m "feat(chat_agent): SSE 队列桥接，阶段事件实时推送"
```

---

### Task 3: 前端 api/index.js SSE 解析扩展

**Files:**
- Modify: `frontend/src/api/index.js`
- Test: `frontend/src/api/index.test.js`（新建）

**Interfaces:**
- Consumes: 无（独立模块）
- Produces: `fetchChatAsk(stockCode, body, callbacks)` 新增回调 `onPhase(data)`、`onToolStart(data)`；`thinking` 事件不再触发任何回调

- [ ] **Step 1: 写失败测试**

创建 `frontend/src/api/index.test.js`：

```javascript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import * as api from './index.js'

/* 构造带 SSE 数据的 ReadableStream */
function sseStream(bodyStr) {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(bodyStr))
      controller.close()
    },
  })
}

describe('fetchChatAsk SSE 解析', () => {
  let originalFetch

  beforeEach(() => { originalFetch = globalThis.fetch })
  afterEach(() => { globalThis.fetch = originalFetch })

  it('解析 phase/tool_start/tool_done/delta/done 全链路', async () => {
    const body = [
      'data: {"type":"phase","phase":"understand"}\n\n',
      'data: {"type":"tool_start","name":"search_news","label":"查询近期新闻"}\n\n',
      'data: {"type":"tool_done","name":"search_news","label":"查询近期新闻","ok":true}\n\n',
      'data: {"type":"delta","text":"你好"}\n\n',
      'data: {"type":"done","full":"你好"}\n\n',
    ].join('')
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, body: sseStream(body) })

    const calls = []
    await new Promise((resolve) => {
      api.fetchChatAsk('000858', { question: 'q' }, {
        onPhase: (d) => calls.push(`phase:${d.phase}`),
        onToolStart: (d) => calls.push(`tool_start:${d.label}`),
        onToolDone: (d) => calls.push(`tool_done:${d.label}:${d.ok}`),
        onDelta: (d) => calls.push(`delta:${d.text}`),
        onDone: (d) => calls.push(`done:${d.full}`),
        onStreamEnd: resolve,
      })
    })

    expect(calls).toEqual([
      'phase:understand',
      'tool_start:查询近期新闻',
      'tool_done:查询近期新闻:true',
      'delta:你好',
      'done:你好',
    ])
  })

  it('废弃的 thinking 事件不触发回调', async () => {
    const body = 'data: {"type":"thinking"}\n\n' +
                 'data: {"type":"done","full":"答"}\n\n'
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, body: sseStream(body) })

    const calls = []
    await new Promise((resolve) => {
      api.fetchChatAsk('000858', { question: 'q' }, {
        onThinking: () => calls.push('thinking'),
        onDone: (d) => calls.push(`done:${d.full}`),
        onStreamEnd: resolve,
      })
    })

    expect(calls).toEqual(['done:答'])
  })

  it('error 事件触发 onError', async () => {
    const body = 'data: {"type":"error","message":"失败啦"}\n\n'
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, body: sseStream(body) })

    const calls = []
    await new Promise((resolve) => {
      api.fetchChatAsk('000858', { question: 'q' }, {
        onError: (e) => calls.push(e.message),
        onStreamEnd: resolve,
      })
    })

    expect(calls).toEqual(['失败啦'])
  })
})
```

- [ ] **Step 2: 跑测试验证失败**

```bash
cd d:/karensAgent/frontend && npx vitest run src/api/index.test.js
```
Expected: FAIL —— `phase:understand` 未出现在 calls 中（现实现不解析 phase/tool_start）

- [ ] **Step 3: 实现解析扩展**

修改 `frontend/src/api/index.js` 的 `fetchChatAsk`，在 [index.js:235](frontend/src/api/index.js#L235) 的事件分发处新增两个分支、移除 thinking 分支：

```javascript
if (data.type === 'phase') callbacks.onPhase?.(data)
else if (data.type === 'tool_start') callbacks.onToolStart?.(data)
else if (data.type === 'tool_done') callbacks.onToolDone?.(data)
else if (data.type === 'delta') callbacks.onDelta?.(data)
else if (data.type === 'done') callbacks.onDone?.(data)
else if (data.type === 'error') callbacks.onError?.(new Error(data.message || '未知错误'))
```

（原 `if (data.type === 'thinking') callbacks.onThinking?.(data)` 删除）

- [ ] **Step 4: 跑测试验证通过**

```bash
cd d:/karensAgent/frontend && npx vitest run src/api/index.test.js
```
Expected: PASS（3 个用例全绿）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/index.js frontend/src/api/index.test.js
git commit -m "feat(agent): fetchChatAsk 解析 phase/tool_start 事件"
```

---

### Task 4: 前端 store 状态改造（chatSteps）

**Files:**
- Modify: `frontend/src/stores/stock.js`
- Test: `frontend/src/stores/chat-steps.test.js`（新建）

**Interfaces:**
- Consumes:
  - `api.fetchChatAsk(stockCode, body, callbacks)`（Task 3 产出，含 `onPhase` / `onToolStart`）
  - 现有 `chatMessages` / `chatSession` / `chatAsking`
- Produces:
  - state 新增 `chatSteps: []`，数组元素 `{ type: 'understand'|'tool'|'answer', label: string, status: 'running'|'done'|'error' }`
  - state 删除 `chatThinking`、`chatToolSteps`
  - `askChat(stockCode, { question, report_id, stock_name })` 事件映射：
    - `onPhase`：understand → push `{understand, '理解问题', running}`；answer → push `{answer, '生成回答', running}`
    - `onToolStart`：push `{tool, label, running}`
    - `onToolDone`：把同 label 的最后一个 tool 行 → `done` / `error`
    - `onDelta`：`chatSteps = []`（首个 delta 闭合）后追加回答
    - `onError` / `onStreamEnd`：`chatSteps = []`

- [ ] **Step 1: 写失败测试**

创建 `frontend/src/stores/chat-steps.test.js`：

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('../api/index.js', () => ({
  fetchChatAsk: vi.fn(),
  getChatSession: vi.fn(),
  getChatMessages: vi.fn(),
  getStockReports: vi.fn(),
}))

import { useStockStore } from './stock.js'
import * as api from '../api/index.js'

/* 捕获 fetchChatAsk 的回调，模拟后端 SSE 事件 */
function captureCallbacks() {
  let cb = null
  api.fetchChatAsk.mockImplementation((code, body, callbacks) => {
    cb = callbacks
    return { abort: vi.fn() }
  })
  return () => cb
}

describe('askChat 思考过程面板状态', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useStockStore()
    vi.clearAllMocks()
    store.chatSession = { stock_code: '000858' }
  })

  it('phase understand 推入理解行', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    getCb().onPhase({ phase: 'understand' })

    expect(store.chatSteps).toHaveLength(1)
    expect(store.chatSteps[0]).toMatchObject({ type: 'understand', label: '理解问题', status: 'running' })
  })

  it('tool_start 追加工具行，tool_done 更新为 done', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    const cb = getCb()

    cb.onToolStart({ name: 'search_news', label: '查询近期新闻' })
    expect(store.chatSteps).toHaveLength(1)
    expect(store.chatSteps[0]).toMatchObject({ type: 'tool', label: '查询近期新闻', status: 'running' })

    cb.onToolDone({ name: 'search_news', label: '查询近期新闻', ok: true })
    expect(store.chatSteps[0].status).toBe('done')
  })

  it('tool_done ok=false 更新为 error', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    const cb = getCb()

    cb.onToolStart({ name: 'search_news', label: '查询近期新闻' })
    cb.onToolDone({ name: 'search_news', label: '查询近期新闻', ok: false })
    expect(store.chatSteps[0].status).toBe('error')
  })

  it('phase answer 推入生成行', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    getCb().onPhase({ phase: 'answer' })

    expect(store.chatSteps[store.chatSteps.length - 1])
      .toMatchObject({ type: 'answer', label: '生成回答', status: 'running' })
  })

  it('首个 delta 清空 chatSteps（卡片闭合）并追加回答', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    const cb = getCb()

    cb.onPhase({ phase: 'understand' })
    cb.onDelta({ text: '你好' })

    expect(store.chatSteps).toEqual([])
    expect(store.chatMessages[store.chatMessages.length - 1])
      .toMatchObject({ role: 'assistant', content: '你好' })
  })

  it('onError 清空 chatSteps', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    const cb = getCb()

    cb.onPhase({ phase: 'understand' })
    cb.onError(new Error('失败'))
    expect(store.chatSteps).toEqual([])
    expect(store.chatAsking).toBe(false)
  })

  it('onStreamEnd 清空 chatSteps（防卡死兜底）', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    getCb().onStreamEnd()

    expect(store.chatSteps).toEqual([])
    expect(store.chatAsking).toBe(false)
  })

  it('新一轮提问重置 chatSteps', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    getCb().onPhase({ phase: 'understand' })
    expect(store.chatSteps).toHaveLength(1)

    // 新一轮提问
    api.fetchChatAsk.mockClear()
    store.askChat('000858', { question: 'q2', report_id: null, stock_name: '五粮液' })
    expect(store.chatSteps).toEqual([])
  })
})
```

- [ ] **Step 2: 跑测试验证失败**

```bash
cd d:/karensAgent/frontend && npx vitest run src/stores/chat-steps.test.js
```
Expected: FAIL —— `store.chatSteps` 为 undefined（state 尚未定义）

- [ ] **Step 3: 实现 store 改造**

修改 `frontend/src/stores/stock.js`：

1. state 中替换 [stock.js:45-46](frontend/src/stores/stock.js#L45-L46)：
```javascript
    chatAsking: false,      // 是否正在请求
    chatSteps: [],          // [{ type:'understand'|'tool'|'answer', label, status }] 三行思考面板
```

2. 重写 `askChat`（[stock.js:440-499](frontend/src/stores/stock.js#L440-L499)），移除全部 `chatThinking`/`chatToolSteps` 引用，新增事件映射：
```javascript
    askChat(stockCode, { question, report_id, stock_name }) {
      const reqCode = stockCode
      // 归属校验：会话未加载时视为当前（尚无可污染对象）；会话已知后必须与本次请求代码一致
      const isCurrent = () => !this.chatSession || this.chatSession.stock_code === reqCode

      this.chatAsking = true
      this.chatSteps = []
      /* created_at 为前端发送时刻，供消息行元信息展示（历史消息用后端落库时间） */
      this.chatMessages.push({ role: 'user', content: question, tool_calls: null, created_at: new Date().toISOString() })

      const controller = api.fetchChatAsk(stockCode, {
        question, report_id, stock_name,
      }, {
        onPhase: (d) => {
          if (!isCurrent()) return
          if (d.phase === 'understand') this.chatSteps.push({ type: 'understand', label: '理解问题', status: 'running' })
          else if (d.phase === 'answer') this.chatSteps.push({ type: 'answer', label: '生成回答', status: 'running' })
        },
        onToolStart: (d) => {
          if (!isCurrent()) return
          this.chatSteps.push({ type: 'tool', label: d.label || d.name, status: 'running' })
        },
        onToolDone: (d) => {
          if (!isCurrent()) return
          const label = d.label || d.name
          // 从后往前匹配同 label 的进行中工具行，更新为完成/失败
          const step = [...this.chatSteps].reverse().find(s => s.type === 'tool' && s.label === label)
          if (step) step.status = d.ok ? 'done' : 'error'
        },
        onDelta: (d) => {
          if (!isCurrent()) return
          this.chatSteps = []  // 首个 delta：思考过程闭合，卡片消失
          const last = this.chatMessages[this.chatMessages.length - 1]
          if (last && last.role === 'assistant') last.content += d.text
          else this.chatMessages.push({ role: 'assistant', content: d.text, tool_calls: null, created_at: new Date().toISOString() })
        },
        onDone: (d) => {
          if (isCurrent()) {
            const last = this.chatMessages[this.chatMessages.length - 1]
            if (last && last.role === 'assistant') last.content = d.full
            else this.chatMessages.push({ role: 'assistant', content: d.full, tool_calls: null, created_at: new Date().toISOString() })
          }
          // 无论归属如何都重置状态，避免旧请求卡死新会话的输入
          this.chatSteps = []
          this.chatAsking = false
        },
        onError: (e) => {
          if (isCurrent()) this.showToast(e.message || '回答失败')
          this.chatSteps = []
          this.chatAsking = false
        },
        /* 流结束兜底：SSE 干净关闭但未 emit done/error 时，防止 chatAsking 永久卡住 */
        onStreamEnd: () => {
          this.chatSteps = []
          this.chatAsking = false
        },
      })
      return controller
    },
```

3. 删除 `fetchChatSession`/`fetchChatMessages` 之外无其他引用 `chatThinking`/`chatToolSteps` —— 全局搜一遍确认（AiChatPanel 的引用在 Task 5 处理，Task 5 前前端编译会有临时报错，属预期，Task 4 的测试只跑 store 不受影响）。

- [ ] **Step 4: 跑测试验证通过**

```bash
cd d:/karensAgent/frontend && npx vitest run src/stores/chat-steps.test.js
```
Expected: PASS（8 个用例全绿）

- [ ] **Step 5: 回归现有 store 测试**

```bash
cd d:/karensAgent/frontend && npx vitest run src/stores/stock.test.js
```
Expected: PASS（现有用例不触碰 askChat/chatSteps，不受影响）

- [ ] **Step 6: Commit**

```bash
git add frontend/src/stores/stock.js frontend/src/stores/chat-steps.test.js
git commit -m "feat(agent): askChat 接入 chatSteps 三行面板状态"
```

---

### Task 5: 前端 ThinkingStepsCard 组件 + AiChatPanel 接入

**Files:**
- Create: `frontend/src/components/report/ThinkingStepsCard.vue`
- Modify: `frontend/src/components/report/AiChatPanel.vue`
- Delete: `frontend/src/components/report/AiStepsCard.vue`

**Interfaces:**
- Consumes: `store.chatSteps`（Task 4 产出，元素 `{type, label, status}`）
- Produces: `ThinkingStepsCard` 为纯展示组件，props `{ steps: Array }`，无事件、无交互元素

> 说明：项目无 `@vue/test-utils` 组件测试基建，本任务组件渲染不做自动测试（不新增依赖，符合项目约束），以 `vite build` 编译通过 + Task 6 人工联调验证为准。

- [ ] **Step 1: 新增 ThinkingStepsCard.vue**

创建 `frontend/src/components/report/ThinkingStepsCard.vue`：

```vue
<!-- AI 问答思考过程面板：理解行 / 工具行（动态）/ 生成行，无任何交互元素，最终回答出现时由父组件卸载 -->
<script setup>
defineProps({
  steps: { type: Array, default: () => [] },
})

/* 状态图标：running=◐（旋转）/ done=✓ / error=✕ / 其余 pending=○ */
function iconOf(status) {
  if (status === 'done') return '✓'
  if (status === 'error') return '✕'
  if (status === 'running') return '◐'
  return '○'
}
</script>

<template>
  <div class="thinking-steps">
    <div v-for="(s, i) in steps" :key="i" class="ts-row" :class="`is-${s.status}`">
      <span class="ts-icon">{{ iconOf(s.status) }}</span>
      <span class="ts-label">{{ s.label }}</span>
    </div>
  </div>
</template>

<style scoped>
/* 思考过程面板：浅色卡片，行间紧凑，整体随内容微缩，首个 delta 时被父组件卸载 */
.thinking-steps {
  display: flex; flex-direction: column; gap: 5px;
  background: var(--sent-bg); border: 1px solid var(--border-color);
  border-radius: var(--radius-md); padding: 8px 12px;
  transition: max-height 0.25s ease, opacity 0.25s ease, padding 0.25s ease;
  overflow: hidden;
}
/* 行：状态图标 + 文案，浅灰小字 */
.ts-row {
  display: flex; align-items: center; gap: 8px;
  font-size: 0.76rem; color: var(--sent-mid); line-height: 1.5;
}
.ts-icon { width: 14px; text-align: center; flex-shrink: 0; }
/* 进行中：图标旋转；完成：绿色；失败：红色 */
.ts-row.is-running .ts-icon { animation: ts-spin 1.2s linear infinite; color: var(--accent); }
.ts-row.is-done .ts-icon { color: var(--success, #2e7d32); }
.ts-row.is-error .ts-icon { color: var(--red, #c62828); }
@keyframes ts-spin { to { transform: rotate(360deg); } }
</style>
```

- [ ] **Step 2: 改造 AiChatPanel.vue**

修改 `frontend/src/components/report/AiChatPanel.vue`：

1. 移除 `AiStepsCard` import，换 `ThinkingStepsCard`（[AiChatPanel.vue:5-6](frontend/src/components/report/AiChatPanel.vue#L5-L6)）：
```vue
import ThinkingStepsCard from './ThinkingStepsCard.vue'
import ChatMessageItem from './ChatMessageItem.vue'
```

2. 删除 `thinking` / `toolSteps` 两个 computed（[AiChatPanel.vue:17-18](frontend/src/components/report/AiChatPanel.vue#L17-L18)）。

3. 模板中删除"思考中"块（`.ai-thinking`）和 `AiStepsCard`，替换为 ThinkingStepsCard（原 [AiChatPanel.vue:59-66](frontend/src/components/report/AiChatPanel.vue#L59-L66)）：
```vue
      <!-- 思考过程面板（三行：理解/工具/生成），首个 delta 时 chatSteps 清空即卸载 -->
      <ThinkingStepsCard v-if="store.chatSteps.length" :steps="store.chatSteps" />
```

4. 删除样式块中 `.ai-thinking` / `.ai-dots` 相关 CSS（原 [AiChatPanel.vue:119-133](frontend/src/components/report/AiChatPanel.vue#L119-L133)）。

- [ ] **Step 3: 删除旧组件**

```bash
git rm frontend/src/components/report/AiStepsCard.vue
```

- [ ] **Step 4: 编译验证**

```bash
cd d:/karensAgent/frontend && npx vite build
```
Expected: BUILD SUCCESS（无 `AiStepsCard` / `chatThinking` / `chatToolSteps` 残留引用报错）

- [ ] **Step 5: 回归前端全量测试**

```bash
cd d:/karensAgent/frontend && npx vitest run
```
Expected: 全绿（含现有 stock.test.js / api/index.test.js / chat-steps.test.js）

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/report/ThinkingStepsCard.vue frontend/src/components/report/AiChatPanel.vue
git commit -m "feat(agent): ThinkingStepsCard 三行面板替换 AiStepsCard"
```

---

### Task 6: 联调与边界态走查

**Files:**
- 无代码改动（验证性质）

- [ ] **Step 1: 启动后端**

```bash
cd d:/karensAgent/backend && python main.py
```
Expected: 正常启动，`/api/chat/...` 路由挂载

- [ ] **Step 2: 启动前端**

```bash
cd d:/karensAgent/frontend && npm run dev
```
Expected: 开发服务器启动，打开投研报告页右栏可见问答面板

- [ ] **Step 3: 人工走查边界态（对照 spec 边界态表）**

| # | 操作 | 预期 |
|---|---|---|
| B1 | 问"今天天气如何" | ① 理解行 ✓ → 直接出兜底回答，②③ 不出现 |
| B2 | 问报告内问题（如"报告结论是什么"） | ① → ③，② 不出现 |
| B3 | 问需查数的（如"近期估值如何"） | ① ✓ → ②"正在核对财务数据…"◐ → 完成 ✓ → ③"正在生成回答…" |
| B4 | 触发多工具问题 | ② 依次点亮多行 |
| B5 | 断网/后端异常 | 卡片闭合，错误 toast |
| B6 | 快速连续提问 | 旧卡片清空，无残留 |
| B7 | 切换股票后旧请求回流 | 归属校验丢弃，不污染新会话 |
| B8 | 刷新页面看历史 | 只显示问题+回答，无思考面板 |

- [ ] **Step 4: 后端全量测试**

```bash
cd d:/karensAgent/backend && python -m pytest tests/ -q --ignore=tests/probe_results
```
Expected: 无新增失败

- [ ] **Step 5: 前端全量测试**

```bash
cd d:/karensAgent/frontend && npx vitest run
```
Expected: 全绿

- [ ] **Step 6: 收尾（若联调发现小修，单独提交）**

```bash
# 如有必要，修正后按项目规范提交，并在回复中说明
```

---

## Self-Review 记录

- **Spec 覆盖**：三行面板形态→Task 5；动态工具文案→Task 1（label 查 TOOL_FRIENDLY_NAMES）；SSE 协议扩展→Task 2+3；闭合（首个 delta）→Task 4；完全不留痕→Task 5（ChatMessageItem 不渲染，AiStepsCard 删除）；边界态 B1-B8→Task 6 走查清单；测试 T1-T12→Task 1-4 的用例映射
- **占位符**：全部步骤含具体代码与命令，无 TBD/TODO
- **类型一致**：`on_event` 参数在 Task 1 定义、Task 2 消费，签名一致；`chatSteps` 元素结构 `{type,label,status}` 在 Task 4 定义、Task 5 消费，一致；事件类型名 `phase/tool_start/tool_done/delta/done/error` 全程一致
