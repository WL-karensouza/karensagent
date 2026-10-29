# 问答助理 astryx 视觉改造 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把投研报告右侧的 Karens 问答助理改成 astryx 设计语言，并支持「收拢 240px ↔ 展开满高」双态。

**Architecture:** 用 Vue 组件复刻 astryx 的视觉规格（不引入 React）；全部颜色/圆角/间距落成 `--ax-` 前缀的 CSS 变量；面板状态由「当前股票的历史消息条数」派生，配合组件内的会话归属守卫避免切股票时串对话。内部逻辑（store / api / 流式 / markdown）零改动。

**Tech Stack:** Vue 3.5、Vite 8、Pinia、Vitest + @vue/test-utils + happy-dom

**Spec:** `docs/superpowers/specs/2026-10-29-chat-panel-astryx-ui-design.md`

## Global Constraints

- **禁止引入任何 npm 依赖**，特别是 React 相关（`react` / `@astryxdesign/*` / `@heroicons/react` / `@heroicons/vue`）。
- 新增 CSS 变量统一 `--ax-` 前缀，**不得修改** `src/style.css` 中已有的暖色 token 值。
- 侧栏宽度**全程 540px 不变**，只做高度动画。
- **不得修改** `frontend/src/stores/`、`frontend/src/api/`、`frontend/src/utils/` 下任何文件。
- 颜色值只允许出现在 `src/style.css` 的 token 定义里，组件样式一律引用变量。
- 「有历史会话」判据只能是**历史消息条数 > 0**，绝不能用 `chatSession` 是否存在判断。

## Review Focus

1. **切股票瞬间**：从有对话的 A 股切到 B 股，面板必须先收起、不残留 A 的对话，等 B 的数据回来再决定——错在此处用户会看到别人的对话。
2. **后端会话接口失败**：请求失败时必须按「无历史」收拢，而不是永远停在展开态或显示上一只股票的内容。
3. **收拢态发送第一条消息**：输入框在收拢态仍然可用，发出后必须立即展开，否则消息发出去却看不见。
4. **消息极少但存在**（1 条）：必须展开，不能因「条数少」被误判为无历史。
5. **1280px 以下窄屏**：走现有堆叠布局时收拢态仍应是 240px，不能撑满或塌成 0。

---

### Task 1: 设计 token 与消息气泡

**Files:**
- Modify: `frontend/src/style.css`（在 `:root` 内追加 token）
- Modify: `frontend/src/components/report/ChatMessageItem.vue`
- Test: `frontend/src/components/report/ChatMessageItem.test.js`（新建）

**Interfaces:**
- Produces: CSS 变量 `--ax-surface`、`--ax-neutral`、`--ax-text`、`--ax-text-secondary`、`--ax-accent`、`--ax-hover`、`--ax-radius-chat`、`--ax-pad-block`、`--ax-pad-inline`，后续 Task 全部引用它们。

- [ ] **Step 1: 写失败测试**

新建 `frontend/src/components/report/ChatMessageItem.test.js`：

```js
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatMessageItem from './ChatMessageItem.vue'

describe('ChatMessageItem 气泡结构', () => {
  it('用户消息渲染 user 类名且内容为 markdown 转 HTML', () => {
    const wrapper = mount(ChatMessageItem, {
      props: { message: { role: 'user', content: '**加粗**', created_at: '2026-10-29T10:00:00Z' } },
    })
    expect(wrapper.find('.chat-msg').classes()).toContain('user')
    expect(wrapper.find('.chat-bubble').html()).toContain('<strong>加粗</strong>')
  })

  it('助理消息渲染 assistant 类名', () => {
    const wrapper = mount(ChatMessageItem, {
      props: { message: { role: 'assistant', content: '你好', created_at: '2026-10-29T10:00:00Z' } },
    })
    expect(wrapper.find('.chat-msg').classes()).toContain('assistant')
  })
})
```

- [ ] **Step 2: 运行测试，确认基线**

Run: `cd frontend && npx vitest run src/components/report/ChatMessageItem.test.js`
Expected: **PASS**。这组测试守护的是「结构契约」（类名 + markdown 渲染），
改造前就应通过；若 FAIL 说明现有组件行为与文档不符，先停下来核对，不要为迁就测试去改组件。

- [ ] **Step 3: 在 `src/style.css` 的 `:root` 末尾追加 token**

```css
  /* ── astryx 设计 token（问答助理专用，勿与上方暖色体系混用）── */
  --ax-surface: #FFFFFF;
  --ax-neutral: rgba(5, 54, 89, 0.1);
  --ax-text: #0A1317;
  --ax-text-secondary: #4E606F;
  --ax-accent: #0064E0;
  --ax-hover: rgba(5, 54, 89, 0.05);
  --ax-radius-chat: 28px;
  --ax-pad-block: 12px;
  --ax-pad-inline: 16px;
```

- [ ] **Step 4: 改 `ChatMessageItem.vue` 的气泡样式**

模板不变。`<style scoped>` 中把 `.chat-msg.user .chat-bubble` 与 `.chat-msg.assistant .chat-bubble` 两块改为：

```css
/* 气泡：双方同一套排版，仅底色不同（astryx：助理透明、用户淡蓝灰） */
.chat-bubble {
  max-width: max(80%, 280px);
  padding: var(--ax-pad-block) var(--ax-pad-inline);
  border-radius: var(--ax-radius-chat);
  font-size: 0.82rem;
  line-height: 1.65;
  word-break: break-word;
  box-sizing: border-box;
  color: var(--ax-text);
}
.chat-msg.user .chat-bubble { background: var(--ax-neutral); }
.chat-msg.assistant .chat-bubble { background: transparent; }
.chat-meta { font-size: 0.72rem; color: var(--ax-text-secondary); line-height: 1.4; }
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/components/report/ChatMessageItem.test.js`
Expected: PASS（2 passed）

- [ ] **Step 6: Commit**

```bash
git add frontend/src/style.css frontend/src/components/report/ChatMessageItem.vue frontend/src/components/report/ChatMessageItem.test.js
git commit -m "feat(chat_ui): 气泡改用 astryx 配色与圆角"
```

---

### Task 2: 思考步骤卡片冷色化

**Files:**
- Modify: `frontend/src/components/report/ThinkingStepsCard.vue`
- Test: `frontend/src/components/report/ThinkingStepsCard.test.js`（新建）

**Interfaces:**
- Consumes: Task 1 的 `--ax-*` 变量
- Produces: 无对外接口变化（props `steps` 不变）

- [ ] **Step 1: 写失败测试**

新建 `frontend/src/components/report/ThinkingStepsCard.test.js`：

```js
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ThinkingStepsCard from './ThinkingStepsCard.vue'

describe('ThinkingStepsCard 状态渲染', () => {
  it('按 status 渲染对应中文标签与状态类名', () => {
    const wrapper = mount(ThinkingStepsCard, {
      props: { steps: [
        { label: '理解问题', status: 'done' },
        { label: '查询资金流', status: 'running' },
        { label: '生成回答', status: 'pending' },
      ] },
    })
    const rows = wrapper.findAll('.ts-row')
    expect(rows).toHaveLength(3)
    expect(rows[0].classes()).toContain('is-done')
    expect(rows[1].classes()).toContain('is-running')
    expect(rows[0].text()).toContain('理解问题')
  })
})
```

- [ ] **Step 2: 运行测试确认失败/基线**

Run: `cd frontend && npx vitest run src/components/report/ThinkingStepsCard.test.js`
Expected: 若组件行为与断言不符则 FAIL，据实际输出校正断言（本测试保护的是状态映射，不是样式）。

- [ ] **Step 3: 改 `ThinkingStepsCard.vue` 配色**

将 `.thinking-steps` 与 `.ts-row` 中的暖色引用替换为：

```css
.thinking-steps {
  flex-shrink: 0;
  display: flex; flex-direction: column; gap: 5px;
  background: var(--ax-hover); border: 1px solid var(--ax-neutral);
  border-radius: 12px; padding: 8px 12px;
  box-sizing: border-box;
}
.ts-row { display: flex; align-items: center; gap: 8px; font-size: 0.76rem; color: var(--ax-text-secondary); line-height: 1.5; }
.ts-row.is-running .ts-icon { animation: ts-spin 1.2s linear infinite; color: var(--ax-accent); }
```

`.ts-row.is-done` 与 `.is-error` 保留原有绿/红（语义色不随主题变）。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/components/report/ThinkingStepsCard.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/report/ThinkingStepsCard.vue frontend/src/components/report/ThinkingStepsCard.test.js
git commit -m "feat(chat_ui): 思考步骤卡片改用 astryx 冷色"
```

---

### Task 3: 面板双态切换与会话归属守卫

**Files:**
- Modify: `frontend/src/components/report/AiChatPanel.vue`
- Test: `frontend/src/components/report/AiChatPanel.test.js`（新建）

**Interfaces:**
- Consumes: store 的 `chatMessages`(Array)、`chatSession`({stock_code}|null)、`chatSteps`、`chatAsking`、`fetchChatSession(stockCode)`、`askChat(stockCode, payload)`、`currentReport`
- Produces: 组件根元素类名 `ai-panel`，并附带 `is-collapsed` / `is-expanded` 二选一

- [ ] **Step 1: 写失败测试**

新建 `frontend/src/components/report/AiChatPanel.test.js`：

```js
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('../../stores/stock.js', () => ({ useStockStore: () => globalThis.__store }))
vi.mock('../../api/index.js', () => ({}))

import AiChatPanel from './AiChatPanel.vue'

function makeStore(overrides = {}) {
  return {
    currentReport: { id: 1, stock_code: '000001', stock_name: '平安银行' },
    chatMessages: [], chatSession: null, chatSteps: [], chatAsking: false,
    fetchChatSession: vi.fn().mockResolvedValue(undefined),
    askChat: vi.fn(),
    ...overrides,
  }
}

beforeEach(() => { setActivePinia(createPinia()) })

describe('AiChatPanel 双态', () => {
  it('无历史消息时处于收拢态', async () => {
    globalThis.__store = makeStore()
    const w = mount(AiChatPanel)
    await flushPromises()
    expect(w.find('.ai-panel').classes()).toContain('is-collapsed')
  })

  it('有历史消息时处于展开态', async () => {
    globalThis.__store = makeStore({
      chatMessages: [{ role: 'user', content: '评分依据？', created_at: '' }],
      chatSession: { stock_code: '000001' },
    })
    const w = mount(AiChatPanel)
    await flushPromises()
    expect(w.find('.ai-panel').classes()).toContain('is-expanded')
  })

  it('会话归属不匹配时不展开也不渲染消息', async () => {
    globalThis.__store = makeStore({
      chatMessages: [{ role: 'user', content: '上一只股票的问题', created_at: '' }],
      chatSession: { stock_code: '600519' },   // 归属与当前 000001 不符
    })
    const w = mount(AiChatPanel)
    await flushPromises()
    expect(w.find('.ai-panel').classes()).toContain('is-collapsed')
    expect(w.text()).not.toContain('上一只股票的问题')
  })

  it('会话接口失败时按无历史收拢，不阻断页面', async () => {
    globalThis.__store = makeStore({
      fetchChatSession: vi.fn().mockRejectedValue(new Error('network down')),
    })
    const w = mount(AiChatPanel)
    await flushPromises()
    expect(w.find('.ai-panel').classes()).toContain('is-collapsed')
  })
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/components/report/AiChatPanel.test.js`
Expected: FAIL —— `.ai-panel` 上还没有 `is-collapsed` / `is-expanded` 类名。

- [ ] **Step 3: 在 `AiChatPanel.vue` 中加会话归属守卫与双态**

在 `<script setup>` 中新增（放在现有 `const report = computed(...)` 附近）：

```js
/* 会话归属守卫：store 的 chatMessages 是全局单份，切股票时必须丢弃上一只股票的内容，
   否则会按旧历史误展开。loadedFor 记录「当前展示的消息属于哪只股票」。 */
const loadedFor = ref(null)

watch(stockCode, async (code) => {
  loadedFor.value = null           // 立刻失效：切股票瞬间不渲染旧消息
  if (!code) return
  try {
    await store.fetchChatSession(code)
  } catch {
    return                          // 接口失败：保持收拢，不阻断页面
  }
  /* 只认「历史消息条数 > 0」；后端每次都会建会话，不能看 session 是否存在 */
  const sameStock = store.chatSession?.stock_code === code
  loadedFor.value = sameStock && store.chatMessages.length > 0 ? code : null
}, { immediate: true })

/* 仅当归属匹配时才把 store 的消息透给模板 */
const messages = computed(() =>
  loadedFor.value === stockCode.value ? store.chatMessages : []
)
const steps = computed(() =>
  loadedFor.value === stockCode.value ? store.chatSteps : []
)
const isExpanded = computed(() => messages.value.length > 0)
```

删除原有的 `onMounted(... fetchChatSession ...)` 与旧的 `const messages = computed(() => store.chatMessages)`（已由上面的 watch + computed 取代）。

模板根节点改为：

```vue
<aside class="ai-panel" :class="isExpanded ? 'is-expanded' : 'is-collapsed'">
```

把 `<ThinkingStepsCard v-if="store.chatSteps.length" :steps="store.chatSteps" />` 改为使用 `steps`：

```vue
<ThinkingStepsCard v-if="steps.length" :steps="steps" />
```

- [ ] **Step 4: 加双态样式（替换 `.ai-panel` 原规则）**

```css
/* 面板：宽度固定 540px（由父容器控制），高度在收拢/展开之间过渡 */
.ai-panel {
  background: var(--ax-surface);
  border: 1px solid var(--ax-neutral);
  border-radius: 20px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-sizing: border-box;
  overflow: hidden;
  transition: height 0.28s ease;
}
.ai-panel.is-collapsed {
  height: 240px;
  justify-content: center;
}
.ai-panel.is-expanded {
  height: calc(100vh - var(--topnav-height, 64px) - 48px);
  min-height: 520px;
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/components/report/AiChatPanel.test.js`
Expected: PASS（4 passed）

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/report/AiChatPanel.vue frontend/src/components/report/AiChatPanel.test.js
git commit -m "feat(chat_ui): 面板收拢/展开双态与会话归属守卫"
```

---

### Task 4: 输入区与报告页容器适配

**Files:**
- Modify: `frontend/src/components/report/AiChatPanel.vue`（输入区样式）
- Modify: `frontend/src/views/agent/StockReport.vue`（`.report-side` 容器）
- Test: `frontend/src/components/report/AiChatPanel.test.js`（追加用例）

**Interfaces:**
- Consumes: Task 3 的 `isExpanded` / `messages`
- Produces: 无新接口

- [ ] **Step 1: 追加失败测试（收拢态可发送）**

在 `AiChatPanel.test.js` 的 describe 内追加：

```js
it('收拢态下输入并发送会调用 askChat', async () => {
  const store = makeStore()
  globalThis.__store = store
  const w = mount(AiChatPanel)
  await flushPromises()
  await w.find('.ai-input input').setValue('这只票的风险点？')
  await w.find('.ai-input button').trigger('click')
  expect(store.askChat).toHaveBeenCalledWith('000001', expect.objectContaining({
    question: '这只票的风险点？',
  }))
})

it('发送中禁用发送按钮', async () => {
  globalThis.__store = makeStore({ chatAsking: true })
  const w = mount(AiChatPanel)
  await flushPromises()
  expect(w.find('.ai-input button').attributes('disabled')).toBeDefined()
})
```

- [ ] **Step 2: 运行测试确认通过或失败**

Run: `cd frontend && npx vitest run src/components/report/AiChatPanel.test.js`
Expected: 若发送逻辑未被破坏应 PASS；FAIL 则应修输入区逻辑而非改测试。

- [ ] **Step 3: 输入区改用 astryx 规格**

`.ai-input` 区块样式替换为：

```css
/* 输入区：钉底，发送键用 astryx 强调蓝 */
.ai-input { display: flex; gap: 8px; flex-shrink: 0; padding-top: 14px; border-top: 1px solid var(--ax-neutral); }
.ai-input input {
  flex: 1; min-width: 0; border: 1px solid var(--ax-neutral); border-radius: 12px;
  padding: 9px 12px; font-size: 0.8rem; font-family: inherit;
  color: var(--ax-text); background: var(--ax-surface); outline: none;
  transition: border-color 0.15s ease;
}
.ai-input input:focus { border-color: var(--ax-accent); }
.ai-input input::placeholder { color: var(--ax-text-secondary); }
.ai-input button {
  height: 36px; padding: 0 16px; border: none; border-radius: 12px;
  background: var(--ax-accent); color: #fff; font-size: 0.78rem; font-family: inherit;
  cursor: pointer; transition: opacity 0.15s ease;
}
.ai-input button:disabled { opacity: 0.45; cursor: not-allowed; }
```

同时把 `.ai-empty` 与 `.ai-id` 的 `--sent-*` 引用换成 `--ax-text-secondary` / `--ax-text`。

- [ ] **Step 4: 改 `StockReport.vue` 的 `.report-side`**

原规则限制了 `max-height` 且 `overflow:auto`，会把收拢态的 240px 撑成滚动容器，改为放出高度交给子组件：

```css
.report-side {
  width: 540px;
  flex-shrink: 0;
  position: sticky;
  top: calc(var(--topnav-height, 64px) + 24px);
  /* 高度交给 .ai-panel 自己按收拢/展开控制，这里不再限制 */
}
```

窄屏媒体查询中的 `.report-side { max-height: none; }` 保留。

- [ ] **Step 5: 运行全部测试**

Run: `cd frontend && npx vitest run`
Expected: 全部 PASS（含既有 7 个测试文件）

- [ ] **Step 6: 浏览器目检**

Run: `cd frontend && npm run dev`，打开报告页，逐项确认：
1. 无历史股票 → 面板约 240px 高，问候语与输入框垂直居中
2. 有历史股票 → 满高，消息内部滚动，输入框钉底
3. 用户气泡淡蓝灰、助理白底无边框、圆角明显更圆
4. 发送键与输入框焦点为 `#0064E0`
5. 拖动窗口到 <1280px，确认堆叠布局下收拢态仍为 240px

- [ ] **Step 7: 构建校验**

Run: `cd frontend && npm run build`
Expected: 构建成功，无报错

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/report/AiChatPanel.vue frontend/src/components/report/AiChatPanel.test.js frontend/src/views/agent/StockReport.vue
git commit -m "feat(chat_ui): 输入区与报告页容器适配双态"
```
