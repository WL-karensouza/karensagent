# karens 问答助理编排层 LangGraph 迁移设计

> **日期：** 2026-08-19
> **状态：** 设计已获用户确认，待写实施计划
> **范围：** 仅 `chat_agent`（投研 AI 问答）编排层；`ai_news_agent` 已是 LangGraph，不动

## 1. 背景

`backend/chat_agent/graph.py` 虽名为 "LangGraph 工作流"（注释沿用），实际实现是**手写命令式流程**：

- `run_qa_agent()` 顺序调用 `_understand` → `_tool_loop` → `_answer`
- `_tool_loop` 是手写 `for _ in range(MAX_TOOL_ROUNDS)` 循环 + OpenAI SDK 原生 Function Calling
- 没有任何 `from langgraph` 导入

用户决策：**必须迁移到纯 LangGraph 框架**，目标是编排层由 LangGraph 图表达（状态、节点、条件边循环），替换手写控制流。

## 2. 目标与收益

| 期望 | 说明 |
|---|---|
| 更稳定 | 工具循环用条件边表达，`rounds` 计数在 state 中显式可见，循环边界由框架保证，死循环被条件边兜住 |
| bug 易修 | 状态显式 `TypedDict`，任意节点异常不影响图结构，可用 `draw_graph()` 可视化 |
| 易加新需求 | 加节点 = `add_node` + 改一条边（如未来加资料核验节点、并行查询财务+新闻+行情） |

**预期校正**：此前修过的 bug（财报回答空、工具假成功、面板半截）根因在工具层校验/提示词/参数/CSS，**不属于本次迁移解决范围**；迁移不回归这些修复。

## 3. 设计决策（已与用户确认）

1. **编排 LangGraph + LLM 调用层保留原生 OpenAI SDK**：节点内继续用 `chat.completions.create` + `extra_body={"thinking": ...}`，DeepSeek 思考模式能力完整保留；不引入 langchain 模型适配器（thinking 透传有兼容性风险）。与 `ai_news_agent` 同款做法。
2. **事件流式用 LangGraph `StreamWriter` + `stream_mode="custom"`**：节点内声明 `writer: StreamWriter` 参数推送自定义事件，`_stream_events` 改为异步驱动图，**去掉手写的线程 + `asyncio.Queue` 桥接**（`routers/chat.py` 现 `run_in_executor` 模式）。已实测 langgraph 1.2.9 支持。
3. **外部契约不变**：`run_qa_agent` 保留为同步薄封装；前端事件协议（`phase` / `tool_start` / `tool_done` / `delta` / `done` / `error`）零改动；`routers/chat.py` 仅重写 `_stream_events` 内部实现。

## 4. 图结构（4 节点）

```
START
  │
  ▼
┌──────────┐
│understand│─── 条件边 ────────────────────────────┐
└──────────┘                                      │
   │ is_off_topic=True 或 needs_tools=False      ▼
   └───────────────────────────────────────→ ┌────────┐
   │ is_off_topic=False 且 needs_tools=True   │ answer │ ──→ END
   ▼                                         └────────┘
┌──────────┐   tool_calls 空 或 rounds≥MAX ─→ ┌────────┐
│ llm_round│ ──────────────────────────────→  │ answer │
└──────────┘                                  └────────┘
   │ tool_calls 非空 且 rounds<MAX
   ▼
┌──────────────┐
│execute_tools │ ─────────→（无条件边回 llm_round）
└──────────────┘
```

**边的定义：**

```python
def decide_after_understand(state):
    # is_off_topic 或不需要工具 → 直接 answer（拒绝或纯报告解读）
    return "answer" if (state["is_off_topic"] or not state["needs_tools"]) else "llm_round"

def decide_after_llm(state):
    # 本轮有工具调用 且 未达轮次上限 → 执行工具并回环；否则收尾去 answer
    last = state["messages"][-1]
    has_calls = bool(last.get("tool_calls")) and state["rounds"] < MAX_TOOL_ROUNDS
    return "execute_tools" if has_calls else "answer"
```

**图构建（对齐 `ai_news_agent` 模式）：**

```python
def create_qa_workflow() -> StateGraph:
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
```

**编译单例**（供 `_stream_events` / `run_qa_agent` 复用）：

```python
_compiled_workflow = None

def qa_workflow():
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = create_qa_workflow()
    return _compiled_workflow
```

## 5. 状态设计

```python
class QaState(TypedDict):
    # ── 输入（build_initial_state 一次注入）──
    question: str
    stock_code: str          # 会话绑定股票（报告锚点，始终保持）
    stock_name: str
    report_context: str
    history: list[dict]      # 最近 8 轮 [{role, content}]，供 answer 注入
    tool_hints: list[str]    # understand 失败兜底方向
    # ── understand 产出 ──
    is_off_topic: bool
    needs_tools: bool
    target_code: str         # 跨股票提问时与 stock_code 不同
    # ── tool 循环维护（llm_round / execute_tools 更新）──
    messages: list[dict]     # OpenAI 格式对话（首条为 user context，含工具结果回填）
    tool_results: str        # 拼接的工具文本（喂 answer）
    tool_calls: list[dict]   # records [{name, label, ok, duration_ms, arguments}]
    rounds: int              # 已执行工具轮数（替换 for 循环计数器）
    # ── answer 产出 ──
    answer_text: str
```

**`messages` 更新约定**：节点返回**完整新列表**（旧消息 + 本轮追加），不使用 reducer——LangGraph 节点返回部分 state 更新，list 字段默认整表替换，`execute_tools` 返回累积后的完整列表即可。

**初始 state 构建**：

```python
def build_initial_state(question, stock_code, stock_name, report_context,
                        tool_hints, history=None) -> dict:
    return {
        "question": question, "stock_code": stock_code, "stock_name": stock_name,
        "report_context": report_context, "history": history or [],
        "tool_hints": tool_hints,
        "is_off_topic": False, "needs_tools": False,
        "target_code": stock_code,
        # messages 初始仅含纯问题；目标股票上下文（含证券实体名）由 llm_round
        # 首轮注入——target_code 在 understand 节点之后才产出，跨股票提问时 ≠ stock_code，
        # 初始 state 构建时无法预知目标股票
        "messages": [{"role": "user", "content": question}],
        "tool_results": "", "tool_calls": [], "rounds": 0, "answer_text": "",
    }
```

## 6. 节点职责

### 6.1 `understand_node` — 意图理解

- 行为：`UNDERSTAND_PROMPT` 构建 → 原生 SDK 调用（`thinking` disabled, `max_tokens=500`）→ 剥离 ```json 包裹 → `json.loads` → 产出 `is_off_topic` / `target_code` / `needs_tools` / `tool_hints`
- 事件：`writer({"type": "phase", "phase": "understand"})`（节点起始即发）
- 异常兜底（现状保留）：解析失败 → `is_off_topic=False, needs_tools=False, target_code=stock_code, tool_hints=[]`
- 返回：`{"is_off_topic", "needs_tools", "target_code", "tool_hints"}`

### 6.2 `llm_round_node` — 单轮 Function Calling

- 行为：`_build_tools_for(tool_hints)` 构建 tools → 原生 SDK Function Calling（`thinking` enabled, `max_tokens=2048`, `temperature=1.0`）
- **首轮注入目标股票上下文**：`target_code` 由 understand 节点产出（跨股票提问时 ≠ stock_code），messages 初始仅含纯问题；`llm_round` 首轮（`rounds == 0`）把 `messages[0]` 替换为 `"当前对话股票目标：{target_code}（{stock_name}）。问题：{question}"`（保留 2026-08-19 根因修复：证券实体注入）
- `tool_calls` 非空 → 追加**干净 assistant 消息**（只保留 `role/content/tool_calls`，剔除 `reasoning_content`，防 token 浪费/400）；为空 → 追加收尾 assistant 消息
- 异常兜底：LLM 调用失败 → 追加收尾 assistant 消息（无工具调用），避免死循环
- 返回：`{"messages": <完整新列表>}`
- **不发事件**（工具事件在 execute_tools 发）

### 6.3 `execute_tools_node` — 执行本轮工具

- 行为：从 `messages[-1]["tool_calls"]` 取本轮全部调用，**逐个串行执行**（与现状一致）
- 每工具：`writer({"type": "tool_start", name, label})` → `execute_tool_call(name, args)` → `writer({"type": "tool_done", name, label, ok})`
- `arguments` 边界守卫保留：LLM 返回非 dict 时包成 `{"query": str(args)}`
- `records` 追加 `{name, label, ok, duration_ms, arguments}`；`tool_results` 拼接 `out["text"]`；`messages` 追加 `{"role": "tool", "tool_call_id", "content"}` tool 消息
- 返回：`{"messages", "tool_results", "tool_calls": <累积完整列表>, "rounds": rounds + 1}`

### 6.4 `answer_node` — 生成最终回答

- 行为：
  - `is_off_topic` → `answer_text = "karens暂时无法回答您这个问题哦？"`（**不发 phase answer 事件**）
  - 否则 `writer({"type": "phase", "phase": "answer"})` → `ANSWER_PROMPT`（有 `tool_results`）或 `REPORT_ONLY_PROMPT`（无）→ 原生 SDK（`thinking` enabled, `max_tokens=16000`, `temperature=1.0`）
  - `target_line` 逻辑保留（跨股票提问标注目标股票）
  - 空 content 兜底：`"抱歉，我未能获取到足够的实时数据来完成这次分析，请换个问法或稍后再试。"`
  - 返回 `answer_text = answer + DISCLAIMER`
- 返回：`{"answer_text"}`

## 7. 事件流式（`_stream_events` 重写）

`routers/chat.py` 的 `_stream_events` 从"线程 + `asyncio.Queue` 桥接"改为**直接异步驱动图**：

```python
async def _stream_events(session, req, stock_code, report_context, history):
    initial = build_initial_state(
        req.question, stock_code, req.stock_name or session["stock_name"],
        report_context, [], history,
    )
    final_answer = None
    tool_calls = []
    try:
        async for mode, chunk in qa_workflow().astream(initial, stream_mode=["custom", "updates"]):
            if mode == "custom":
                yield chunk            # phase / tool_start / tool_done 原样透传
            else:                      # updates：每节点结束后的 state 更新
                for node, upd in chunk.items():
                    if node == "answer" and upd.get("answer_text"):
                        final_answer = upd["answer_text"]
                    if node == "execute_tools":
                        tool_calls = upd.get("tool_calls", tool_calls)
    except Exception as e:
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

**已验证（原型实测 2026-08-19）**：
- `app.stream(initial, stream_mode=["custom", "updates"])` 产出 `(mode, chunk)` 元组
- `custom` 通道事件结构原样保留；`updates` 通道每节点结束返回其 state 更新
- 条件边循环 2 轮后正确收尾，事件序 `['phase', 'tool_start', 'tool_done', 'tool_start', 'tool_done', 'phase']` 与前端协议完全兼容
- 从 `updates` 中 `answer` 节点更新可拿到最终 `answer_text`

## 8. 外部契约

| 契约 | 处理 |
|---|---|
| `routers/chat.py` | `_stream_events` 重写（§7）；`ask()` / `_build_report_context` / `_chunk_text` / 落库逻辑保留 |
| `run_qa_agent` | 保留为同步薄封装（`app.invoke` 组装返回 dict），**移除 `on_event` 参数**（事件走 StreamWriter）；供测试/诊断 |
| 前端 | **零改动**（事件协议不变） |
| `requirements.txt` | 补 `langgraph>=1.2.9`（环境已装，当前未声明） |

`run_qa_agent` 同步入口：

```python
def run_qa_agent(question, stock_code, stock_name, report_context,
                 tool_hints, history=None) -> dict:
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
        return {
            "answer": f"karens 暂时遇到问题，请稍后重试。（{type(e).__name__}）",
            "is_off_topic": False, "tool_calls": [], "success": False, "error": str(e),
        }
```

## 9. 错误处理分层

| 层 | 兜底 |
|---|---|
| `understand_node` | LLM/解析失败 → 默认股票相关（`needs_tools=False`），走纯报告解读 |
| `llm_round_node` | LLM 调用失败 → 追加收尾消息（本轮无工具），图正常流转到 answer，**杜绝死循环** |
| `execute_tools_node` | `execute_tool_call` 已有 `ok=False` + `[无数据]/[错误]` 前缀兜底（保留 2026-08-19 假成功修复） |
| `answer_node` | LLM 调用异常由外层捕获；空 content → fallback 文案（保留） |
| `_stream_events` | 图级异常 → `error` 事件 + 落库失败消息（最后防线） |

## 10. 边界情况

| 场景 | 行为 |
|---|---|
| off_topic（如"今天天气"） | understand → answer（无工具），answer 不发 phase 事件，返回拒绝文案 |
| `needs_tools=False` | understand → answer，纯报告解读（`REPORT_ONLY_PROMPT`） |
| 工具全部失败 | tool_results 为 `[无数据]/[错误]` 文本 → answer 用 `ANSWER_PROMPT` → LLM 判断无效 → 空 content → fallback 文案（与现状一致） |
| rounds 达上限 | 条件边 `rounds >= MAX_TOOL_ROUNDS` → 强制 answer，不循环 |
| 单轮多工具调用 | execute_tools 逐个串行执行（与现状一致），工具事件按序发出 |
| 跨股票提问 | understand 产出 `target_code` ≠ `stock_code`，answer 用 `target_line` 标注（逻辑保留） |
| 历史消息 | `_format_history` 逻辑保留，注入 answer prompt |

## 11. 测试策略

### `backend/tests/test_chat_agent_graph.py`（重写）

**统一 mock 策略**：mock `graph._get_client()` 返回假 client（`side_effect` 控制 LLM 响应序列），**真图跑通所有节点**——验证的是真实图结构（条件边/循环/事件），不是 mock 掉的图。

- `TestUnderstandNode`：JSON 解析（含 ```json 包裹剥离）、异常兜底、字段映射
- `TestLlmRoundNode`：干净 assistant 消息（无 reasoning_content）、tool_calls 构造、LLM 失败兜底（本轮无工具）、messages 累积
- `TestExecuteToolsNode`：mock `graph.execute_tool_call`，断言工具执行、records（含 arguments）、ok 标记、rounds 递增、tool_start/tool_done 事件（mock writer）
- `TestAnswerNode`：off_topic 拒绝（不发 phase）、空 content fallback、DISCLAIMER、target_line、ANSWER/REPORT_ONLY 分支
- `TestWorkflow`（真图 + mock LLM client）：
  - 全流程事件序 = `[phase(understand), tool_start, tool_done, ..., phase(answer)]`
  - 多轮循环 + `MAX_TOOL_ROUNDS` 上限
  - off_topic 路径：仅 `phase(understand)`，无工具事件
  - 无工具路径：仅两个 phase
  - `stream_mode=["custom", "updates"]` 能取到最终 `answer_text`

### `backend/tests/test_chat_agent_chat.py`（适配）

- `_stream_events` **真图 + mock LLM client**（`patch` `graph._get_client`），断言：`custom` 事件透传、最终 `delta`×N + `done`、图异常 → `error` 事件 + 落库失败消息、落库调用参数（answer + tool_calls）

### 不变

- `test_chat_agent_tools.py`、`test_skill_extract.py`、前端测试

## 12. 文件改动清单

| 文件 | 改动 |
|---|---|
| `backend/chat_agent/graph.py` | **重写**：`QaState` / `build_initial_state` / 4 节点 / 条件边 / `create_qa_workflow` / `qa_workflow()`（编译单例） / `run_qa_agent` 薄封装；保留 `_format_history`、`_build_tools_for`、`MAX_TOOL_ROUNDS`、LLM 客户端单例 |
| `backend/chat_agent/routers/chat.py` | **重写 `_stream_events`**（§7），其余保留 |
| `backend/tests/test_chat_agent_graph.py` | **重写**（§11） |
| `backend/tests/test_chat_agent_chat.py` | **适配**（§11） |
| `backend/requirements.txt` | 补 `langgraph>=1.2.9` |
| 本文档 | 设计记录 |

## 13. 验证记录

- `StreamWriter + stream_mode="custom"`：langgraph 1.2.9 实测可用，自定义事件原样透传（`/d/tmp/test_lg_streamwriter.py`）
- 条件边循环 + 多模式 stream 完整骨架：实测事件序正确、可拿最终 answer_text（`/d/tmp/test_lg_loop.py`）
- 依赖版本：`langgraph 1.2.9`、`langchain-openai 1.4.1`（本迁移**不引入** langchain-openai）
