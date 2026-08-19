# karens 意图理解改文本行解析设计

> **日期：** 2026-08-19
> **状态：** 设计已获用户确认，待写实施计划
> **范围：** `chat_agent` 的意图理解（`understand_node` + `UNDERSTAND_PROMPT`）及对应测试；**只影响这一个节点**，下游零改动

## 1. 背景

karens 问答助理的意图理解 `understand_node` 目前要求 LLM 输出**严格 JSON**（`UNDERSTAND_PROMPT` 指定 4 个字段），代码用 `json.loads` 解析，并做 ```` ```json ```` 包裹剥离。

用户偏好：**不要严格 JSON**，向 `ai_news_agent` 的轻量风格靠拢——"标签：值"文本行 + 代码 split 解析（宽松、容错、不依赖 JSON 结构）。

## 2. 目标

| 项 | 说明 |
|---|---|
| 输出格式 | LLM 输出"标签：[值]"文本行（AI 新闻同款风格） |
| 解析方式 | 宽松逐行前缀匹配 + split，兼容全/半角冒号 |
| 影响面 | **只改 `understand_node` 解析 + `UNDERSTAND_PROMPT`**；产出结构不变，下游节点/图/前端/事件协议零改动 |
| 容错 | 字段级兜底（单字段缺失不影响其他字段），宽松哲学对齐 AI 新闻 |

## 3. 输出格式（`UNDERSTAND_PROMPT` 改写）

```
是否股票相关：[是/否]
目标股票代码：[如 000858，默认填"当前股票"]
需要实时查数：[是/否]
数据方向：[如 财务、估值、新闻，最多3个，不需要填"无"]
```

规则说明（写入 prompt）：
1. 每行一个字段，标签与取值之间用全角冒号。
2. `是否股票相关`：问题与股票/金融投资完全无关（如"今天天气如何"）填"是"。
3. `目标股票代码`：若问题提到其他股票（如"五粮液怎么样"）填其代码格式提示；否则填"当前股票"。
4. `需要实时查数`：需要实时查数填"是"；仅解读报告填"否"。
5. `数据方向`：大致需要的方向（估值/财务/行情/股东/新闻/风险/ESG/公告），最多 3 个。

**不再要求输出 JSON、不再处理 markdown 包裹**（删除 code fence 剥离逻辑）。

## 4. 解析逻辑（`understand_node` 改写）

新增辅助函数 + 改写节点内解析段：

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
```

节点内解析（替换 `json.loads` 段，删除 code fence 剥离）：

```python
# 意图理解（文本行宽松解析，2026-08-19 改造，对齐 ai_news 风格）
is_off_topic = _parse_line(text, "是否股票相关") in ("是", "true", "True")
needs_tools = _parse_line(text, "需要实时查数") in ("是", "true", "True")

code_text = _parse_line(text, "目标股票代码")
target_code = state["stock_code"]
if code_text and "当前股票" not in code_text:
    target_code = code_text

hints_text = _parse_line(text, "数据方向") or ""
# 兼容顿号/逗号分隔，过滤空项与"无"
tool_hints = [h.strip() for h in hints_text.replace("、", ",").split(",") if h.strip() and h.strip() != "无"]
```

**字段级兜底**：任何字段缺失/解析失败 → 该项取默认（`is_off_topic=False`、`needs_tools=False`、`target_code=stock_code`、`tool_hints=[]`），不影响其他字段。整段解析异常 → 沿用现有 `except` 整体兜底（is_off_topic=False, needs_tools=False, target_code=stock_code, tool_hints=[]）。

**产出结构不变**：`{"is_off_topic": bool, "needs_tools": bool, "target_code": str, "tool_hints": list}` —— 与改造前一致，下游零改动。

## 5. 影响范围

| 文件 | 改动 |
|---|---|
| `backend/chat_agent/prompts.py` | `UNDERSTAND_PROMPT` 改写（文本行格式）；其余模板不动 |
| `backend/chat_agent/graph.py` | `understand_node` 解析段改写 + 新增 `_parse_line`；**删除 code fence 剥离**；其余节点/图不动 |
| `backend/tests/test_chat_agent_graph.py` | `TestUnderstandNode` 改写（mock 响应 JSON→文本行）+ 新增字段级兜底用例；`TestWorkflow` 等 understand mock 响应同步改文本行 |
| `backend/tests/test_chat_agent_chat.py` | understand LLM mock 响应改文本行 |
| 前端 / 事件协议 / `routers/chat.py` | 零改动 |

## 6. 测试用例

- 正常解析：4 字段文本行 → 各字段正确
- 半角冒号兼容：LLM 输出 `:` 而非 `：` 也能解析
- 缺失字段兜底：少某行 → 该字段默认值，其他字段正常
- "目标股票代码：当前股票" → 用会话 stock_code
- 数据方向含"无" → 空列表
- 数据方向逗号分隔（`财务,估值`）→ 解析为列表
- 完全乱输出 → 整体兜底（except 分支）
- LLM 调用异常 → 兜底（现有逻辑，测试保留）

## 7. 验证记录

- 解析逻辑基于 ai_news `understand_query_node`（[graph.py:75-139](d:/karensAgent/backend/ai_news_agent/graph.py#L75-L139)）的宽松风格扩展（字段级 + 全半角冒号兼容）
- 实施计划阶段将对 `_parse_line` 做 TDD 实测
