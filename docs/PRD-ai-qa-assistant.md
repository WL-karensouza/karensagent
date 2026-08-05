# 产品需求文档：投研 AI 问答助理（karens）

**作者**：王磊
**日期**：2026-08-04
**状态**：方案评审中
(PRD-stock-agent.md)（投研报告主功能）、[AiChatPanel.vue](../frontend/src/components/report/AiChatPanel.vue)（前端占位）

---

## 1. 执行摘要

投研报告详情页右侧已存在一个「AI 问答助理」占位面板（[AiChatPanel.vue](../frontend/src/components/report/AiChatPanel.vue)），本次将该占位落地为真实可用的问答智能体。

助理名为 **karens**。用户在报告页针对该股票提问，karens 通过 **LangGraph 工作流 + DeepSeek Function Calling + iFinD 全工具层**：理解问题 → 按需实时调用 iFinD 接口取数 → 结合当前投研报告 → 流式生成有来源依据的回答。

**核心价值**：把"死报告"变成"活数据"。既解读报告内容，又能对报告未覆盖的细节实时查数（如"北向资金今天净流入多少"），回答有真实数据锚点。

---

## 2. 背景与目标

### 2.1 目标

| # | 目标 |
|---|------|
| G1 | 报告页右侧问答面板从占位升级为可用聊天，回答"对报告追问 / 实时查数"两类问题 |
| G2 | 回答基于实时 iFinD 数据 + 当前报告，可核查、不编造 |
| G3 | 多轮会话持久化，刷新 / 重进不丢失 |
| G4 | 调用过程与进度**优美地**实时展示，不是黑盒等待 |
| G5 | 复用现有基建：LangGraph 先例、SSE 流式、DeepSeek 调用、iFinD SKILL 封装 |

### 2.2 非目标

| # | 内容 | 原因 |
|---|------|------|
| N1 | 盘中实时监控 / 自动交易 | 法律风险高，只做分析问答 |
| N2 | 全局会话列表 / 多会话切换 | 会话绑定股票，无需列表管理（见 5.4） |
| N3 | 保存 10 维原始数据建表 | 实时调用 iFinD 已覆盖，省存储成本（见 4.1） |
| N4 | 标注数据来源 | 决策：全称删除来源标注，避免信息噪音 |
| N5 | Token 成本精细控制 | 只做上下文滑动窗口（见 6.2），不管 token 计费 |

---

## 3. 核心决策总览（评审重点）

本次需求前已完成多方调研与实测，关键决策如下：

| # | 决策项 | 选择 | 依据 |
|---|--------|------|------|
| D1 | 回答数据范围 | 当前报告 + **实时调用 iFinD**（不存原始数据） | 实时/覆盖度全面胜出，省建表成本 |
| D2 | 工具层 | **全 iFinD 工具层**（非仅 10 维） | 6 接口实测全部可用；query 自然语言参数为主 |
| D3 | 架构范式 | **LangGraph 图**（understand→tool_loop→answer） | 复用 ai_news_agent 先例，可扩展 |
| D4 | Prompt 范式 | **Function Calling**（DeepSeek 原生）+ 意图理解 + 约束回答 | 实测与思考模式兼容，不写 ReAct |
| D5 | 会话记忆 | **后端持久化到 DB** | 刷新/重进不丢 |
| D6 | 会话归属 | **绑定股票共享**（非报告专属、非全局） | 避免上下文污染 + 语义错位 + 锚点混乱 |
| D7 | 跨股票提问 | **允许**（问别的股票也能查） | 工具层天然支持，价值更高 |
| D8 | 输出方式 | **SSE 流式** | 复用现有基建，体验好 |
| D9 | 调用过程展示 | **思考动画 + 步骤卡片 + 流式回答** | 见第 7 节精心设计 |
| D10 | 免责声明 | **后端统一拼接固定文案**（不占 LLM 生成） | 省 token、文案可控 |
| D11 | 数据来源标注 | **不标注** | 用户决策 |

---

## 4. 系统架构

### 4.1 数据策略：为什么"实时调 iFinD"而非"存原始数据"

初始方案曾考虑保存 10 维原始数据（sections）供问答检索，但实测后放弃：

- **数据时效**：存的是报告生成时刻的快照，用户问"今天最新价"会过时
- **建表成本**：需改 `stock_reports` 表 + 迁移存量报告
- **覆盖度**：只覆盖 10 维，无法问 iFinD 支持的其他数据

改用**实时调用 iFinD 工具层**：LLM 按问题动态选工具查数。好处：

| 维度 | 存原始数据 | 实时调 iFinD |
|---|---|---|
| 时效 | 快照 | **实时** |
| 建表 | 要迁移存量 | **零** |
| 覆盖度 | 10 维 | **任意 iFinD 工具** |

> 已实测 6 个 iFinD 接口：get_stock_summary / get_stock_financials / get_risk_indicators / stock_highfreq_quotes / search_news 全部返回正常。含 query 自然语言参数与结构化参数两种形态。

### 4.2 LangGraph 工作流

```
┌─────────┐    ┌──────────────┐    ┌────────────┐
│START    │───▶│ understand   │───▶│ tool_loop  │───▶ answer ──▶ END
└─────────┘    └──────────────┘    └────────────┘
                    │                    │
                    │  无关问题/无工具    │
                    └───────▶ answer（无工具回答）◀────┘
```

**State（LangGraph 状态）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `question` | str | 用户本轮问题 |
| `stock_code` | str | 目标股票（默认取会话绑定股票） |
| `tool_calls` | list[dict] | 本轮调用的工具记录（名称/状态/耗时） |
| `tool_results` | list[str] | 各工具返回的数据文本 |
| `report_context` | str | 注入的当前报告结论摘要（固定锚点） |
| `history` | list[dict] | 滑动窗口内的历史问答 |
| `answer` | str | 最终回答 |
| `needs_tools` | bool | understand 判断是否需要调工具 |
| `is_off_topic` | bool | 是否无关问题（短路） |
| `error` | str | 错误信息（空=无错误） |

**节点职责**：

| 节点 | 职责 |
|------|------|
| **understand** | ① 判断是否股票相关，无关→`is_off_topic=True` 短路；② 提取目标股票代码；③ 决定是否需要工具、大致涉及哪些 iFinD 工具；④ 是否需要报告片段注入 |
| **tool_loop** | Function Calling 循环（最多 3-5 轮）：LLM 输出 tool_call → 映射到 `call_skill` 执行 → 回填结果 → 直到 LLM 不再请求工具或超轮数 |
| **answer** | 基于工具结果 + 报告上下文 + 历史，生成最终回答；后端拼接免责声明 |

### 4.3 Function Calling 循环（核心）

```
1. LLM 请求: tools=[全部 iFinD 工具描述] + 用户问题
2. 模型返回 tool_call: {name: "get_stock_financials", arguments: {query: "贵州茅台 ROE"}}
3. 后端 _execute_tool_call(tool_call) → call_skill(server, tool, params)
4. 工具结果回填给模型（role=tool）
5. 重复 2-4，直到模型不再请求工具
```

- **工具描述**：从 iFinD `tools/list` 拉取（含中文描述 + JSON Schema），缓存到后端；少量人工备注（news 需 time_start、高频行情用中文指标名）
- **思考模式兼容**：已实测开启 `extra_body={"thinking":{"type":"enabled"}}` 时 function calling 正常返回，`reasoning_content` 与 `content` 分离
- **失败重试**：复用 collect.py 的 `_call_dim_with_retry` 思路（iFinD 间歇性拒绝/限速）

---

## 5. 会话与数据库设计

### 5.1 表结构

```sql
-- 会话表：每只股票一个活跃会话（绑定股票共享）
CREATE TABLE chat_sessions (
    id            INT PRIMARY KEY AUTO_INCREMENT,
    stock_code    VARCHAR(20)  NOT NULL COMMENT '股票代码',
    stock_name    VARCHAR(64)  NOT NULL COMMENT '股票名称',
    report_id     INT          NULL     COMMENT '最近锚定的报告 ID（股票共享，随进入报告页更新）',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_code (stock_code)
) COMMENT 'AI 问答会话';

-- 消息表：每轮问答
CREATE TABLE chat_messages (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    session_id  INT          NOT NULL COMMENT '所属会话',
    role        VARCHAR(16)  NOT NULL COMMENT 'user / assistant',
    content     TEXT         NOT NULL COMMENT '用户问题 或 助手最终回答',
    tool_calls  TEXT         NULL     COMMENT '该轮调用的工具记录 JSON 数组（名称/状态/耗时）',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_session (session_id)
) COMMENT 'AI 问答消息';
```

### 5.2 会话归属逻辑（D6）

- 会话**绑定股票**：进入某股票报告页时，按 `stock_code` 查 `chat_sessions`；无则创建，有则复用
- `report_id` 更新为当前进入的报告 ID（仅作锚点记录，不影响会话连续性）
- 同一股票的多份报告共享一个会话 → 刷新/重进/切换报告都在

### 5.3 会话与消息 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/chat/session/{stock_code}` | 获取会话 + 历史消息 |
| GET | `/api/chat/session/{stock_code}/messages` | 分页拉历史消息 |
| POST | `/api/chat/{stock_code}/ask` | SSE 流式提问（见 6.1） |

### 5.4 为什么不是"全局共享"

用户曾提出"既然能问别的股票，全局共享岂不更好"。否决理由（已达成共识）：

1. **上下文污染**：全局窗口装不下多只股票的话题，LLM 易答串
2. **语义错位**：报告页聊天看到所有股票历史，与"正在看这只股票"矛盾
3. **锚点混乱**：当前报告结论固定注入失去意义

跨股票提问仍允许（D7），但作为"离题一笔"不污染主线：会话锚点是当前股票，问别的股票只实时查数回答，不进会话记忆主线。

---

## 6. SSE 流式协议与上下文控制

### 6.1 SSE 事件流

提问接口返回 `text/event-stream`，事件类型：

| 事件 | 载荷 | 说明 |
|------|------|------|
| `thinking` | `{}` | 助手开始理解问题（前端显示思考动画） |
| `tool_start` | `{name, label}` | 某工具开始调用（label 为友好名） |
| `tool_done` | `{name, label, ok}` | 工具完成 |
| `tool_error` | `{name, label, error}` | 工具失败（带理由） |
| `delta` | `{text}` | 回答增量（流式 Markdown） |
| `done` | `{full}` | 回答完成（含免责声明） |
| `error` | `{message}` | 整体失败 |

### 6.2 上下文滑动窗口（D10）

- 保留最近 **8 轮**（用户问题 + 助手回答）进 LLM 上下文
- **工具调用结果不存历史**（只留最终回答）——避免工具返回的大段数据污染后续轮次
- **当前报告结论摘要固定注入**：低成本锚点，让助手始终知道在聊哪只股票
- Token 计费不做精细控制，只做窗口控制

---

## 7. 前端界面设计（重点：调用过程展示必须优美）

### 7.1 面板结构升级

现有 [AiChatPanel.vue](../frontend/src/components/report/AiChatPanel.vue) 已是"顶栏 + 会话区(可滚) + 钉底输入"结构，直接复用，将占位态替换为真实会话。

### 7.2 三类状态展示（精心设计）

**① 思考阶段**
- 原占位的"呼吸三点"动画复用，旁加文案"karens 正在理解你的问题…"
- 浅色、缓动，与现有 `ai-breathe` 动画一致

**② 工具调用阶段 —— 步骤卡片（核心设计）**

每次调用一个 iFinD 工具，渲染一张**步骤卡片**：

```
┌──────────────────────────────────────┐
│    正在获取估值数据                  │  ← 友好名（非接口名）
│      ● 理解问题          ✓ 完成       │
│      ● 查询实时行情      ◐ 进行中...   │
│      ● 核对财务数据      ○ 等待       │
└──────────────────────────────────────┘
```

- **友好名映射**：`get_stock_financials` → "核对财务数据"，`stock_highfreq_quotes` → "查询实时行情"（不暴露接口名，符合 D11 不标注来源）
- **状态图标**：等待=灰点 / 进行=呼吸动画 / 完成=绿勾淡入 / 失败=红叉 + 原因
- **优雅动效**：卡片随状态推进**轻微过渡**（高度/透明度），完成后卡片可**淡出收拢**，保持会话区清爽
- 遵循项目浅色系、无渐变、简约国际配色（对应现有 CSS 变量 `--sent-*`）

**③ 回答阶段**
- SSE 增量逐字渲染（复用现有 `marked` Markdown 渲染）
- 回答末尾自动附免责声明（后端拼接）

### 7.3 消息气泡

- 用户问题右对齐（现有 `--sent-*` 色系）
- 助手回答左对齐，Markdown 渲染
- 历史消息从 DB 加载，渲染 `tool_calls` JSON 为已完成的步骤卡片（只读）

### 7.4 边界态

| 场景 | 展示 |
|------|------|
| 无关问题 | 助手回复"karens暂时无法回答您这个问题哦？"（D12） |
| iFinD 失败 | 步骤卡片标红 + 理由，按投研报告内容降级解释（C） |
| 输入中 | 发送按钮禁用态 + 防重复提交 |

---

## 8. Prompt 范式设计

已实测确认 DeepSeek 原生支持 function calling 且与思考模式兼容，**不手写 ReAct**。三个 prompt 分属两种范式：

### 8.1 意图理解 prompt（understand 节点）

```
分析用户问题：{question}
上下文：当前股票 {stock_code}（{stock_name}）
输出 JSON：
  is_off_topic: 是否与股票/金融投资无关（bool）
  stock_code: 目标股票（默认当前股票）
  needs_tools: 是否需要实时查数（bool）
  tool_hints: 大致需要的 iFinD 工具方向（如 估值/行情/财务/新闻）
```

作用：控制 token 成本，避免每次全量注入工具 + 无关问题短路。

### 8.2 Function Calling（tool_loop 节点，模型原生）

- DeepSeek `tools` 参数声明全部 iFinD 工具（描述 + schema 从 `tools/list` 拉取缓存）
- 模型自主决定调哪些、传什么 query
- 代码只写 `_execute_tool_call` 映射到 `call_skill`，循环 3-5 轮

### 8.3 约束回答 prompt（answer 节点）

```
基于以下实时工具数据回答：{tool_results}
结合当前报告：{report_context}
历史对话：{history}
要求：
1. 优先依据实时工具数据回答，不得编造
2. 数据不足时明确说明
3. 结合投研报告给出解读
4. 无关问题统一回复："karens暂时无法回答您哦？"
```

---

## 9. 技术要点

| 项 | 选择 |
|----|------|
| 工作流 | LangGraph（参照 ai_news_agent/graph.py） |
| 模型 | DeepSeek（OpenAI 兼容，Function Calling + 思考模式） |
| 工具层 | iFinD SKILL 全工具（复用 call_skill / extract / collect.py 重试） |
| 传输 | SSE 流式（事件：thinking/tool_start/tool_done/delta/done） |
| 存储 | chat_sessions + chat_messages 两表 |
| 前端 | 复用 AiChatPanel 结构 + marked 渲染 + 步骤卡片组件 |
| 免责声明 | 后端固定拼接，不占 LLM 生成 |

---

## 10. 成功指标

| 指标 | 目标 |
|------|------|
| 工具调用成功率 | ≥ 90%（失败时降级解释） |
| 单轮问答响应 | 流式可见，首 token 3 秒内 |
| 多轮会话持久化 | 刷新/重进不丢历史 |
| 无关问题识别 | 准确返回兜底文案，不瞎答 |
| 回答锚定性 | 关键数值与 iFinD 返回一致（防幻觉） |

---

## 11. 实施步骤（拆分）

1. **后端 DB**：建 `chat_sessions` + `chat_messages` 两表 + ORM 模型 + DAO
2. **工具层**：拉取 iFinD tools/list 缓存 + 友好名映射表 + `_execute_tool_call`
3. **LangGraph 图**：understand / tool_loop / answer 三节点 + State
4. **SSE 接口**：`/api/chat/{stock_code}/ask` 流式 + 事件定义
5. **前端面板**：AiChatPanel 占位升级 + 步骤卡片组件 + SSE 消费
6. **联调**：全链路 + 边界态（无关/失败/限速）

---

## 12. 开放问题

| # | 问题 | 状态 |
|---|------|------|
| Q1 | 工具友好名映射表初始覆盖哪些工具？ | 待定（默认覆盖 10 维 + 新闻/公告） |
| Q2 | 8 轮滑动窗口是否需要用户可调？ | 待定（默认 8 轮） |
| Q3 | 港股（global_stock）工具是否一并接入？ | 待定（建议接入，成本低） |
