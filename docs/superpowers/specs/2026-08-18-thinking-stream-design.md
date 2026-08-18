# AI 问答思考过程三行面板设计

日期：2026-08-18
状态：已批准，待实施

## 背景

投研报告页右侧「karens 问答助理」当前处理提问时是**黑盒等待**：
后端 `run_qa_agent` 同步跑完整流程（understand → tool_loop → answer），
期间前端只有一个"正在理解你的问题…"三点动画；工具调用的过程感弱
（只有工具**完成后**的 `tool_done` 事件，且展示为独立的步骤卡片）。

需求：把"从分析用户问题到最后执行"的中间过程**实时展现**出来——
用一段可闭合的思考过程面板，展示阶段推进与工具调用，
最终回答出现时面板闭合消失，用户不可点击、不可回看。

## 已确认的需求决策（王磊哥哥拍板）

1. **思考内容 = 定制阶段文案**，不是模型 `reasoning_content` 原文
   （原文长、中英混杂、噪音多，且与紧凑形态冲突）
2. **展示形态 = 三行步骤面板**：理解行 / 工具行（动态多个）/ 生成行
3. **工具行文案跟随工具**：调财务工具就显示"正在核对财务数据…"，
   调新闻工具就显示"正在查询近期新闻…"，不写死（复用 `TOOL_FRIENDLY_NAMES`）
4. **闭合语义 = 完全不留痕**：最终回答流出时面板闭合消失，
   用户无法点击；历史会话重放只保留问题 + 最终回答，不显示思考过程
5. **实现方案 = 事件级流式（方案 A）**：不改造 LLM 真流式（`stream=True`），
   只把后端流程拆成"可插桩"的，各阶段真实发生时实时推事件

## 三行面板形态

助手回答气泡**上方**的紧凑卡片区（新组件 `ThinkingStepsCard.vue`，替代 `AiStepsCard.vue`）：

```
┌──────────────────────────────────────┐
│ ① 正在理解问题…                    ✓ │   ← 理解行（固定）
│ ② 正在核对财务数据…                ◐ │   ← 工具行（动态，跟随工具）
│ ③ 正在生成回答…                    ○ │   ← 生成行（固定）
└──────────────────────────────────────┘
   ↑ 首个回答增量到达时，卡片向上收拢淡出，无残留
```

| 行 | 职责 | 文案来源 | 状态 |
|---|---|---|---|
| ① 理解行 | understand 阶段 | 固定："正在理解问题…" | running → done ✓ |
| ② 工具行 | tool_loop 阶段 | **动态**："正在{友好名}…"，失败标 ✕ | 等待 ○ / 进行 ◐ / 完成 ✓ / 失败 ✕ |
| ③ 生成行 | answer 阶段 | 固定："正在生成回答…" | running → 回答出现时卡片闭合 |

**特殊分支**：
- 无工具调用（纯报告解读）→ 只有 ① 和 ③，② 不出现
- 无关问题短路 → ① 完成后直接出兜底回答，② ③ 不出现
- 工具失败 → ② 显示 "✕ {友好名}失败"，流程继续

## SSE 事件协议扩展

**现有协议**（[chat.py](../backend/chat_agent/routers/chat.py)）：`thinking` / `tool_done` / `delta` / `done` / `error`

**扩展后**（新增 `phase`、`tool_start`，保留 `tool_done`/`delta`/`done`/`error`）：

| 事件 | 载荷 | 触发时机 | 前端动作 |
|---|---|---|---|
| `phase` | `{phase: 'understand'}` | understand 节点开始 | ① 显示"正在理解问题…" |
| `tool_start` | `{name, label}` | 某工具**开始**调用 | ② 加一行"正在{label}…" ◐ |
| `tool_done` | `{name, label, ok}` | 工具完成 | ② 该行更新 ✓ / ✕ |
| `phase` | `{phase: 'answer'}` | answer 节点开始 | ③ 显示"正在生成回答…" |
| `delta` | `{text}` | 回答增量 | **首个 delta 到达 → 卡片闭合收拢**，回答文字原位流出 |
| `done` | `{full}` | 回答完成 | — |
| `error` | `{message}` | 整体失败 | 卡片收拢，显示错误文案 |

设计要点：
- `tool_start` 是新增关键——让"正在{label}…"在**工具真实耗时期间**出现
- 闭合时机锚定：**首个 `delta`**（回答开始 → 思考过程退出）
- `tool_done` 保留，前端已消费，兼容过渡

## 后端插桩（graph.py + chat.py 小改）

### graph.py

`run_qa_agent` 加 `on_event` 回调参数，在各阶段真实发生处插桩调用：

```
run_qa_agent(question, ..., on_event=emit)
  ├─ _understand 开始      → emit({type:'phase', phase:'understand'})
  ├─ 需要工具时 _tool_loop
  │    每轮循环:
  │      ├─ 调工具前        → emit({type:'tool_start', name, label})   ← 关键新增
  │      └─ 工具执行完      → emit({type:'tool_done', name, label, ok})
  ├─ _answer 开始          → emit({type:'phase', phase:'answer'})
  └─ 返回 result           → chat.py 沿用 delta/done
```

- `label` 从 `tools.py` 的 `TOOL_FRIENDLY_NAMES` 取（不存在时回退工具接口名）
- 插桩点不改变现有返回结构，`run_qa_agent` 对外契约不变（仍返回 `{answer, tool_calls, success, ...}`）

### chat.py

`ask()` 的 `gen()` 改造——用 `asyncio.Queue` 桥接后台线程与 SSE 协程：

1. 创建 `asyncio.Queue`
2. `emit = lambda evt: queue.put_nowait(evt)`（`put_nowait` 线程安全）
3. `run_in_executor` 跑 `run_qa_agent(..., on_event=emit)`
4. `gen()` 主协程循环 `queue.get()`，每拿到一个事件就 `yield` 一条 SSE；
   线程结束后照旧发 `delta` → `done` / `error`

- 工具执行是真实耗时，事件级推送让工具行**天然实时**
- 改动范围收敛：只动 `graph.py`（回调插桩）+ `chat.py`（队列桥接），
  `tools.py` / `database.py` / `models.py` 不动

## 前端改造

### 组件结构

```
frontend/src/components/report/
├── ThinkingStepsCard.vue   ← 新增：三行思考过程面板（替代 AiStepsCard）
├── AiChatPanel.vue         ← 改：接入 ThinkingStepsCard，移除旧 thinking 动画 + AiStepsCard
├── ChatMessageItem.vue     ← 不改（现状就不渲染 tool_calls，天然不留痕）
└── AiStepsCard.vue         ← 删除（被 ThinkingStepsCard 取代）
```

- `ThinkingStepsCard.vue` 无任何可交互元素，天然满足"用户无法点击"
- 渲染数据来自 store 的 `chatSteps` 数组

### 状态流转（stock.js）

现状：`chatThinking`（布尔）+ `chatToolSteps`（数组）。改造：新增 `chatSteps` 数组取代两者。

```
chatSteps = [
  { type: 'understand', label: '理解问题',    status: 'done' },     ← 理解行（固定 1 个）
  { type: 'tool',       label: '核对财务数据', status: 'running' }, ← 工具行（动态多个）
  { type: 'tool',       label: '查询近期新闻', status: 'pending' },
  { type: 'answer',     label: '生成回答',    status: 'pending' },  ← 生成行（固定 1 个）
]
```

| SSE 事件 | store 动作 |
|---|---|
| `phase: understand` | push `{understand, running}` |
| `tool_start` | push `{tool, label, running}` |
| `tool_done` | 对应工具行 → `done` / `error` |
| `phase: answer` | push `{answer, running}` |
| **首个 `delta`** | `chatSteps = []`（清空 → 卡片闭合消失）+ 回答开始累积 |
| `error` / `onStreamEnd` | `chatSteps = []`（清空，卡片闭合） |

- 每次 `askChat` 开头重置 `chatSteps`，保证连续提问不残留
- `onError` / `onStreamEnd` 同样清空 `chatSteps`，避免失败或流中断时卡片残留
- 归属校验（`isCurrent()`）沿用现状，旧请求事件丢弃

### API 层（api/index.js）

`fetchChatAsk` 新增 `phase`、`tool_start` 解析，回调透传：
- `phase` → `onPhase`
- `tool_start` → `onToolStart`
- `tool_done` / `delta` / `done` / `error` 保留解析
- `thinking` 事件**废弃**（由 `phase: understand` 取代），移除其解析

### 闭合动画

首个 `delta` → store 清空 `chatSteps` → Vue 卸载卡片，配**向上收拢 + 淡出**过渡
（`max-height` / `opacity` / `transform`，约 250ms）。回答气泡随即在原位出现。
闭合后无残留 DOM、无点击区域。

### 历史不留痕

- [ChatMessageItem.vue](../frontend/src/components/report/ChatMessageItem.vue) 只渲染头像 + 元信息 + Markdown 气泡，**不渲染 tool_calls 步骤卡片**，天然满足不留痕，无需改动
- 后端 `tool_calls` 继续落库（数据完整性冗余），但前端历史重放不渲染
- 思考面板只存在于"本次提问的实时过程"，由 store 状态驱动，历史加载不触发

## 边界态

| # | 场景 | 面板表现 | 说明 |
|---|---|---|---|
| B1 | 无关问题 | ① ✓ 后 ②③ 不出现，卡片直接闭合 | `is_off_topic` 短路 |
| B2 | 纯报告解读（不查数） | 只走 ① → ③，② 不出现 | `needs_tools=False` |
| B3 | 工具失败 | ② 该行 ✕ + "失败"，流程继续 | `tool_done ok=false` 不中断 |
| B4 | 一轮调多个工具 | ② 依次点亮多行 | 顺序执行，逐行推进 |
| B5 | 整体失败（LLM 异常） | 卡片闭合，显示错误文案 | 走现有 `error` 分支 |
| B6 | 连续快速提问 | 新一轮重置 `chatSteps` | `askChat` 开头清空 |
| B7 | 切换/跨股票提问 | 归属校验丢弃旧请求事件 | 复用 `isCurrent()` |
| B8 | SSE 流中断 | 卡片闭合，防 `chatAsking` 卡死 | 复用 `onStreamEnd` 兜底 |

## 测试清单

**后端（插桩 + 队列桥接）**
- T1 事件顺序：understand → tool_start → tool_done → answer → delta 全链路按序
- T2 无关问题：不发 `tool_start`，正常发兜底回答（delta/done），无卡片残留
- T3 纯报告：无 `tool_start`，有 understand + answer 两个 phase
- T4 工具失败：`tool_done ok=false` 且流程继续
- T5 多工具：`tool_start`/`tool_done` 交替成对出现
- T6 整体失败：`error` 事件且不卡死
- T7 队列桥接：线程内 `emit` 与协程 `get` 无死锁、无事件丢失

**前端（状态 + 渲染 + 动画）**
- T8 `chatSteps` 随事件正确累积/更新（✓/◐/✕ 状态）
- T9 首个 `delta` → 卡片闭合消失，回答正常流出
- T10 重提问题 → 旧卡片清空无残留
- T11 历史重放 → 只显示问题+回答，无思考面板
- T12 SSE 中断 → 状态兜底重置，可再次发送

## 改动清单

| 文件 | 改动 |
|---|---|
| backend/chat_agent/graph.py | `run_qa_agent` 加 `on_event`，插桩 phase/tool_start/tool_done |
| backend/chat_agent/routers/chat.py | `ask` 加 `asyncio.Queue` 桥接，`gen()` 实时消费事件 |
| frontend/src/components/report/ThinkingStepsCard.vue | 新增三行面板组件 |
| frontend/src/components/report/AiStepsCard.vue | 删除 |
| frontend/src/components/report/AiChatPanel.vue | 换用 ThinkingStepsCard，移除旧 thinking 动画 + AiStepsCard |
| frontend/src/stores/stock.js | 新增 `chatSteps`，`askChat` 事件映射改造 |
| frontend/src/api/index.js | `fetchChatAsk` 新增 phase/tool_start 解析 |

## 不做的事

- 不改造 LLM 真流式（`stream=True` / `reasoning_content` 流式输出）
- 不展示模型思考原文
- 不做可点击/可展开的思考过程（闭合即消失，不可回看）
- 历史消息不渲染工具步骤（不留痕）
- 不新增数据库字段（`chat_messages.tool_calls` 保留现状，前端不渲染）
