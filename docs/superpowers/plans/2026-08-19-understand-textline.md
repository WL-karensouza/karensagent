# karens 意图理解文本行解析实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `chat_agent` 意图理解从"严格 JSON 输出 + `json.loads` 解析"改造为"标签：值文本行输出 + 宽松逐行解析"（对齐 `ai_news_agent` 风格）。

**Architecture:** 改写 `UNDERSTAND_PROMPT` 要求 LLM 按固定"标签：[值]"格式逐行输出；`understand_node` 新增 `_parse_line` 辅助函数做宽松前缀匹配 + split 提取（兼容全/半角冒号、字段级兜底）；产出结构不变，下游节点与前端零改动。

**Tech Stack:** Python、OpenAI SDK、pytest。

## Global Constraints

（来自 `docs/superpowers/specs/2026-08-19-understand-textline-design.md`）

1. **只改** `understand_node` 节点解析 + `UNDERSTAND_PROMPT`；`llm_round_node`/`execute_tools_node`/`answer_node`/图结构/条件边/`routers/chat.py`/前端/**零改动**。
2. `understand_node` 产出结构不变：`{"is_off_topic": bool, "needs_tools": bool, "target_code": str, "tool_hints": list}`。
3. **删除** code fence 剥离逻辑（```` ```json ````/```` ``` ````），不再输出 JSON。
4. `_parse_line(text, label)`：逐行前缀匹配，兼容全角 `：` 与半角 `:`；找不到返回 `None`。
5. 字段级兜底：`is_off_topic`/`needs_tools` 取 `("是","true","True")` 布尔判断；`目标股票代码` 值含"当前股票"或缺失 → 用会话 `stock_code`；`数据方向` 用 `replace("、", ",").split(",")` 过滤空项与"无"。
6. `understand_node` 的 LLM 调用参数不变：`thinking` disabled、`max_tokens=500`；整段异常沿用现有 `except` 整体兜底。
7. 测试 mock 策略：`patch` `graph._get_client()` 返回假 client；understand mock 响应从 JSON 字符串改为文本行。
8. 中文注释；commit message 中文一句话。

---

### Task 1: understand_node 文本行解析改造（唯一任务，含全部测试适配）

**Files:**
- Modify: `backend/chat_agent/prompts.py`（`UNDERSTAND_PROMPT` 改写）
- Modify: `backend/chat_agent/graph.py`（`understand_node` 解析改写 + 新增 `_parse_line`；删除 code fence 剥离）
- Modify: `backend/tests/test_chat_agent_graph.py`（`TestUnderstandNode` 改写 + 新增用例；`TestWorkflow`/`TestRunQaAgent` 的 understand mock 响应改文本行）
- Modify: `backend/tests/test_chat_agent_chat.py`（understand LLM mock 响应改文本行）

**Interfaces:**
- Consumes: `state`（`question`/`stock_code`/`stock_name`）、`writer`、`_get_client()`、`UNDERSTAND_PROMPT`
- Produces: `understand_node` 产出结构不变（下游零感知）；新增模块级函数 `_parse_line(text: str, label: str) -> str | None`

- [ ] **Step 1: 改写测试文件（understand mock 响应改文本行 + 新增兜底用例）**

**`backend/tests/test_chat_agent_graph.py`** 的 `TestUnderstandNode` 整体替换为：

```python
class TestUnderstandNode:
    """understand 节点：文本行解析、全半角冒号兼容、字段级/整体兜底"""

    def test_parses_textlines_and_maps_fields(self, monkeypatch):
        writer = MagicMock()
        resp = _make_resp("是否股票相关：否\n"
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
        resp = _make_resp("是否股票相关:否\n需要实时查数:是\n数据方向:财务,估值")
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
        resp = _make_resp("是否股票相关：是")
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
        resp = _make_resp("是否股票相关：否\n目标股票代码：当前股票\n需要实时查数：是")
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = resp
        monkeypatch.setattr(graph, "_get_client", lambda: fake_client)
        state = graph.build_initial_state("问", "000858", "五粮液", "报告", [], None)
        out = graph.understand_node(state, writer)
        assert out["target_code"] == "000858"

    def test_no_hint_means_empty_list(self, monkeypatch):
        """数据方向填"无"→ 空列表"""
        writer = MagicMock()
        resp = _make_resp("是否股票相关：否\n需要实时查数：是\n数据方向：无")
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
```

**`backend/tests/test_chat_agent_graph.py`** 中其余 understand mock 响应**改为文本行**（其余断言不变）：

- `TestWorkflow.test_full_flow_event_sequence`：
  `_make_resp('{"is_off_topic": false, "needs_tools": true, "tool_hints": ["财务"]}')` →
  `_make_resp("是否股票相关：否\n需要实时查数：是\n数据方向：财务")`
- `TestWorkflow.test_rounds_capped_at_max`：
  `_make_resp('{"is_off_topic": false, "needs_tools": true}')` →
  `_make_resp("是否股票相关：否\n需要实时查数：是")`
- `TestWorkflow.test_off_topic_path_no_tool_events`：
  `_make_resp('{"is_off_topic": true}')` →
  `_make_resp("是否股票相关：是")`
- `TestWorkflow.test_no_tools_only_phase_events`：
  `_make_resp('{"is_off_topic": false, "needs_tools": false}')` →
  `_make_resp("是否股票相关：否\n需要实时查数：否")`
- `TestRunQaAgent.test_sync_wrapper_invokes_graph`：
  `_make_resp('{"is_off_topic": false, "needs_tools": false}')` →
  `_make_resp("是否股票相关：否\n需要实时查数：否")`

**`backend/tests/test_chat_agent_chat.py`** 的 understand 响应改为文本行（其余断言不变）：

- `test_success_emits_events_in_order`：
  `_make_resp('{"is_off_topic": false, "needs_tools": true, "tool_hints": []}')` →
  `_make_resp("是否股票相关：否\n需要实时查数：是")`
- `test_no_tools_produces_delta_and_done`：
  `_make_resp('{"is_off_topic": false, "needs_tools": false}')` →
  `_make_resp("是否股票相关：否\n需要实时查数：否")`
- `test_failure_emits_error_and_stops`：无 understand 响应（`side_effect=Exception`），不改。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd /d/karensAgent/backend && python -m pytest tests/test_chat_agent_graph.py tests/test_chat_agent_chat.py -q`
Expected: FAIL —— `understand_node` 仍是 JSON 解析，收到文本行后 `json.loads` 抛错走 except 兜底，`needs_tools=True` 的断言失败（如 `test_parses_textlines_and_maps_fields` 的 `out["needs_tools"] is True` 得到 `False`）。

- [ ] **Step 3: 实现——prompts.py + graph.py**

**`backend/chat_agent/prompts.py`** 的 `UNDERSTAND_PROMPT` 整体替换为：

```python
# 意图理解：判断是否股票相关、提取目标股票、决定是否需要工具（文本行输出，2026-08-19 改宽松风格对齐 ai_news）
UNDERSTAND_PROMPT = """分析用户的提问，按以下固定格式输出（每行一个字段，标签与取值之间用全角冒号：）。

是否股票相关：[是/否]
目标股票代码：[如 000858，默认填"当前股票"]
需要实时查数：[是/否]
数据方向：[如 财务、估值、新闻，最多3个，不需要填"无"]

用户问题：{question}
当前股票：{stock_code}（{stock_name}）
当前日期：{today_str}

规则：
1. 是否股票相关：问题与股票/金融投资完全无关时填"是"（如"今天天气如何"）。
2. 目标股票代码：若问题提到明确的其他股票（如"五粮液怎么样"），填那只股票的代码格式提示；否则填"当前股票"。
3. 需要实时查数：需要实时查数时填"是"；仅需解读报告内容时填"否"。
4. 数据方向：大致需要的数据方向，取值示例 估值、财务、行情、股东、新闻、风险、ESG、公告，最多 3 个。"""
```

**`backend/chat_agent/graph.py`**：在 `understand_node` 定义前新增 `_parse_line`，并重写 `understand_node`：

```python
def _parse_line(text: str, label: str) -> str | None:
    """在文本中找 label 所在行，返回冒号后的值；找不到返回 None

    逐行前缀匹配（不依赖行序/完整结构），兼容全角：与半角: 冒号。
    """
    for line in text.splitlines():
        if label in line:
            for sep in ("：", ":"):
                if sep in line:
                    return line.split(sep, 1)[-1].strip()
    return None


def understand_node(state: QaState, writer: StreamWriter) -> dict:
    """意图理解节点：发 phase understand 事件，产出意图分析结果

    宽松文本行解析（2026-08-19 改造，对齐 ai_news 风格）：LLM 按"标签：值"
    逐行输出，代码逐行前缀匹配 + split 提取；字段级兜底，不依赖 JSON 结构。
    """
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
        # 宽松文本行解析：字段级兜底，单字段缺失不影响其他字段
        is_off_topic = _parse_line(text, "是否股票相关") in ("是", "true", "True")
        needs_tools = _parse_line(text, "需要实时查数") in ("是", "true", "True")

        code_text = _parse_line(text, "目标股票代码")
        target_code = state["stock_code"]
        if code_text and "当前股票" not in code_text:
            target_code = code_text

        hints_text = _parse_line(text, "数据方向") or ""
        # 兼容顿号/逗号分隔，过滤空项与"无"
        tool_hints = [
            h.strip() for h in hints_text.replace("、", ",").split(",")
            if h.strip() and h.strip() != "无"
        ]
        return {
            "is_off_topic": is_off_topic,
            "needs_tools": needs_tools,
            "target_code": target_code,
            "tool_hints": tool_hints,
        }
    except Exception as e:
        print(f"[chat_agent] [警告] 意图理解失败，默认按股票相关处理: {e}")
        return {
            "is_off_topic": False,
            "needs_tools": False,
            "target_code": state["stock_code"],
            "tool_hints": [],
        }
```

（删除原 `understand_node` 中的 code fence 剥离段与 `json.loads` 段。）

- [ ] **Step 4: 跑测试确认通过**

Run: `cd /d/karensAgent/backend && python -m pytest tests/test_chat_agent_graph.py tests/test_chat_agent_chat.py -q`
Expected: PASS（TestUnderstandNode 6 个新用例 + 其余全部通过）

- [ ] **Step 5: 后端全量回归**

Run: `cd /d/karensAgent/backend && python -m pytest -q`
Expected: PASS（220+ passed，无新增失败；1 个既有 StarletteDeprecationWarning 忽略）

- [ ] **Step 6: 提交**

```bash
git add backend/chat_agent/prompts.py backend/chat_agent/graph.py backend/tests/test_chat_agent_graph.py backend/tests/test_chat_agent_chat.py
git commit -m "refactor(chat_agent): 意图理解改宽松文本行解析对齐 ai_news 风格"
```

---

## 实施后验证（非测试，手动）

重启后端后，浏览器实测：
1. 问"该公司的财报进行分析一下" → 正常走工具查询（understand 文本行解析生效）
2. 问"今天天气如何" → karens 拒绝回答（`是否股票相关：是` → off_topic 路径）
3. 跨股票提问（如"五粮液怎么样"）→ 工具查询五粮液（`目标股票代码` 解析生效）
