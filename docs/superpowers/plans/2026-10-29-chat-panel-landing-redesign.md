# 问答助理 Landing 形态重构 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把问答助理的收拢态重构成 astryx `ai-chat-landing` 的形态——大标题问候 + 悬浮巨型输入容器 + 工具行 + 圆形发送键，并让两态等高、只切内容。

**Architecture:** 抽出独立的 `ChatComposer.vue` 承载输入容器（托盘 + 白框 + textarea + 装饰工具行 + 发送键），用 `density` 区分收拢/展开两档密度；`AiChatPanel.vue` 只负责在两种内容布局之间切换，并保留既有的会话归属守卫与消息渲染。全部尺寸按 0.75 从模板等比缩放。

**Tech Stack:** Vue 3.5、Vite 8、Pinia、Vitest + @vue/test-utils + happy-dom

**Spec:** `docs/superpowers/specs/2026-10-29-chat-panel-landing-redesign.md`

## Global Constraints

- **禁止新增任何 npm 依赖**（图标一律手写内联 SVG 或纯 CSS）。
- 所有颜色/圆角/字号/阴影只能引用 `--ax-*` 变量，组件内不出现裸 hex。
- 面板宽度全程 540px 不变。
- **不得修改** `frontend/src/stores/`、`frontend/src/api/`、`frontend/src/utils/` 下任何文件。
- 装饰按钮必须是 `disabled` + `aria-hidden="true"`，且不进入 Tab 焦点链。
- 面板高度固定为 `calc(100vh - var(--topnav-height, 64px) - 193px)`，两态共用。

## Review Focus

1. **中文输入法回车**：拼音选词时按 Enter 不能误发送——必须靠 `isComposing` / `keyCode 229` 守卫拦住。
2. **首屏裁切**：面板在未滚动时就应完整可见；若高度公式或容器内边距算错，输入框会掉到视口外。
3. **收拢态发首条消息**：发送后面板必须立刻转成展开态并显示该消息，不能停留在收拢态。
4. **装饰按钮可达性**：`@`/Auto/Settings/🎤 必须真的不可点击、Tab 键不会停在上面，否则用户会反复戳一个没反应的按钮。
5. **两态切换高度一致**：切换时面板高度与报告正文宽度都不能有任何变化。

---

### Task 1: 扩充缩放后的设计 token

**Files:**
- Modify: `frontend/src/style.css`
- Test: 无独立测试（纯变量声明，由 Task 2/3 的行为测试间接覆盖）

**Interfaces:**
- Produces: `--ax-text-hi`(13px)、`--ax-text-display`(26px)、`--ax-radius-tray`(21px)、`--ax-radius-inner`(12px)、`--ax-pad-tray`(9px)、`--ax-pad-tray-compact`(6px)、`--ax-shadow-low`、`--ax-shadow-med`、`--ax-text-tool`(11px)

- [ ] **Step 1: 在 `style.css` 的 `:root` 内、已有 `--ax-*` 变量之后追加**

```css
  /* ── astryx landing 形态 token（0.75 等比缩放自模板 720px 宽）── */
  --ax-text-hi: 13px;
  --ax-text-display: 26px;
  --ax-radius-tray: 21px;
  --ax-radius-inner: 12px;
  --ax-pad-tray: 9px;
  --ax-pad-tray-compact: 6px;
  --ax-text-tool: 11px;
  --ax-shadow-low: 0px 1px 1px rgba(0, 0, 0, 0.1), 0px 2px 8px rgba(0, 0, 0, 0.1);
  --ax-shadow-med: 0px 1px 2px rgba(0, 0, 0, 0.1), 0px 2px 12px rgba(0, 0, 0, 0.1);
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/style.css
git commit -m "feat(chat_ui): 新增 landing 形态缩放 token"
```

---

### Task 2: 新建 ChatComposer 输入容器组件

**Files:**
- Create: `frontend/src/components/report/ChatComposer.vue`
- Test: `frontend/src/components/report/ChatComposer.test.js`（新建）

**Interfaces:**
- Props: `modelValue: String`、`density: 'landing' | 'compact'`（默认 `'landing'`）、`maxRows: Number`（默认 5）、`disabled: Boolean`（默认 false）
- Emits: `update:modelValue`、`send`
- Produces: 根元素类名 `composer-tray`，内部含 `.composer-inner`、`.composer-textarea`、`.composer-tools`、`.composer-send`

- [ ] **Step 1: 写失败测试**

新建 `frontend/src/components/report/ChatComposer.test.js`：

```js
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatComposer from './ChatComposer.vue'

function mountComposer(props = {}) {
  return mount(ChatComposer, { props: { modelValue: '', ...props } })
}

describe('ChatComposer 输入交互', () => {
  it('Enter 触发 send 事件', async () => {
    const w = mountComposer({ modelValue: '风险点？' })
    await w.find('.composer-textarea').trigger('keydown', { key: 'Enter' })
    expect(w.emitted('send')).toHaveLength(1)
  })

  it('Shift+Enter 不触发 send', async () => {
    const w = mountComposer({ modelValue: '第一行' })
    await w.find('.composer-textarea').trigger('keydown', { key: 'Enter', shiftKey: true })
    expect(w.emitted('send')).toBeUndefined()
  })

  it('中文输入法选词时 Enter 不触发 send', async () => {
    const w = mountComposer({ modelValue: '平安' })
    await w.find('.composer-textarea').trigger('keydown', { key: 'Enter', isComposing: true })
    expect(w.emitted('send')).toBeUndefined()
  })

  it('空输入时 Enter 不触发 send', async () => {
    const w = mountComposer({ modelValue: '   ' })
    await w.find('.composer-textarea').trigger('keydown', { key: 'Enter' })
    expect(w.emitted('send')).toBeUndefined()
  })

  it('点击发送键触发 send', async () => {
    const w = mountComposer({ modelValue: '评分依据' })
    await w.find('.composer-send').trigger('click')
    expect(w.emitted('send')).toHaveLength(1)
  })

  it('disabled 时发送键禁用且不触发 send', async () => {
    const w = mountComposer({ modelValue: '评分依据', disabled: true })
    expect(w.find('.composer-send').attributes('disabled')).toBeDefined()
    await w.find('.composer-send').trigger('click')
    expect(w.emitted('send')).toBeUndefined()
  })

  it('装饰按钮 disabled 且 aria-hidden，不进入焦点链', () => {
    const w = mountComposer()
    const decoratives = w.findAll('.composer-tools button:not(.composer-send)')
    expect(decoratives.length).toBeGreaterThan(0)
    for (const btn of decoratives) {
      expect(btn.attributes('disabled')).toBeDefined()
      expect(btn.attributes('aria-hidden')).toBe('true')
      expect(btn.attributes('tabindex')).toBe('-1')
    }
  })

  it('density 影响根元素类名', () => {
    expect(mountComposer({ density: 'compact' }).find('.composer-tray').classes()).toContain('is-compact')
    expect(mountComposer({ density: 'landing' }).find('.composer-tray').classes()).toContain('is-landing')
  })
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/components/report/ChatComposer.test.js`
Expected: FAIL —— 组件文件不存在，模块解析失败。

- [ ] **Step 3: 实现 `ChatComposer.vue`**

结构（`<script setup>` + `<template>` + `<style scoped>`）：

- `<script setup>`：定义 `defineProps`（`modelValue`、`density`、`maxRows`、`disabled`）与 `defineEmits(['update:modelValue', 'send'])`。
- 内部 `const text = ref(props.modelValue)`，`watch(() => props.modelValue, v => { text.value = v })`，`watch(text, v => emit('update:modelValue', v))`。
- `canSend = computed(() => !props.disabled && text.value.trim().length > 0)`。
- `doSend()`：`if (!canSend.value) return; emit('send'); text.value = ''`（发送后清空并复位高度）。
- `onKeydown(e)`：`if (e.key !== 'Enter') return; if (e.shiftKey) return; if (e.isComposing || e.keyCode === 229) return; e.preventDefault(); doSend()`。
- 高度自适应：`const taRef = ref(null)`，`onInput` 时 `ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, maxHeightPx) + 'px'`，其中 `maxHeightPx = props.maxRows * lineHeightPx`，行高按 22px 计算。

模板骨架：

```vue
<div class="composer-tray" :class="`is-${density}`">
  <div class="composer-inner">
    <span class="composer-at" aria-hidden="true">@</span>
    <textarea
      ref="taRef"
      class="composer-textarea"
      :value="text"
      :placeholder="placeholder"
      :disabled="disabled"
      rows="1"
      @input="onInput"
      @keydown="onKeydown"
    />
    <div class="composer-tools">
      <button class="composer-tool" type="button" disabled aria-hidden="true" tabindex="-1">Auto</button>
      <button class="composer-tool" type="button" disabled aria-hidden="true" tabindex="-1">Settings</button>
      <span class="composer-spacer" />
      <span class="composer-mic" aria-hidden="true">🎤</span>
      <button
        class="composer-send"
        type="button"
        :disabled="!canSend"
        aria-label="发送"
        @click="doSend"
      >→</button>
    </div>
  </div>
</div>
```

样式要点（全部走 `--ax-*` 变量）：

```css
.composer-tray {
  background: var(--ax-hover);
  border-radius: var(--ax-radius-tray);
  padding: var(--ax-pad-tray);
  box-shadow: var(--ax-shadow-low);
  transition: box-shadow 0.15s ease;
}
.composer-tray:focus-within { box-shadow: var(--ax-shadow-med); }
.composer-tray.is-compact { padding: var(--ax-pad-tray-compact); }
.composer-inner {
  background: var(--ax-surface);
  border-radius: var(--ax-radius-inner);
  padding: 9px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.composer-textarea {
  border: none; outline: none; resize: none; background: transparent;
  font-family: inherit; font-size: 0.82rem; line-height: 22px;
  color: var(--ax-text); max-height: 110px; overflow-y: auto;
}
.composer-tray.is-landing .composer-textarea { min-height: 63px; max-height: 110px; }
.composer-tray.is-compact .composer-textarea { min-height: 22px; max-height: 66px; }
.composer-tools { display: flex; align-items: center; gap: 10px; }
.composer-tool,
.composer-mic {
  font-size: 0.76rem; color: var(--ax-text-secondary);
  background: none; border: none; padding: 0; cursor: default;
}
.composer-tray.is-compact .composer-tool { font-size: var(--ax-text-tool); }
.composer-spacer { flex: 1; }
.composer-send {
  width: 30px; height: 30px; border-radius: 50%; border: none;
  background: var(--ax-accent); color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.composer-send:disabled { opacity: 0.45; cursor: not-allowed; }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/components/report/ChatComposer.test.js`
Expected: PASS（8 passed）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/report/ChatComposer.vue frontend/src/components/report/ChatComposer.test.js
git commit -m "feat(chat_ui): 新增 ChatComposer 悬浮输入容器组件"
```

---

### Task 3: 重构 AiChatPanel 为两套内容布局

**Files:**
- Modify: `frontend/src/components/report/AiChatPanel.vue`
- Modify: `frontend/src/components/report/AiChatPanel.test.js`（同步适配新结构）

**Interfaces:**
- Consumes: Task 2 的 `ChatComposer`（props `modelValue` / `density` / `maxRows` / `disabled`，事件 `send`）、Task 1 的 `--ax-*` 变量
- Produces: 面板根元素仍带 `ai-panel` + `is-collapsed` / `is-expanded`；新增 `.ai-hero`（收拢态标题组）

- [ ] **Step 1: 更新测试以适配新结构（先改测试，确认失败）**

把 `AiChatPanel.test.js` 中所有 `.ai-input input` 改为 `.composer-textarea`、`.ai-input button` 改为 `.composer-send`，并新增两条：

```js
  it('收拢态渲染大标题问候与悬浮输入容器', async () => {
    globalThis.__store = makeStore()
    const w = mount(AiChatPanel)
    await flushPromises()
    expect(w.find('.ai-hero').exists()).toBe(true)
    expect(w.text()).toContain('Hi, Karens')
    expect(w.text()).toContain('关于这支股票有什么可以帮你的吗？')
    expect(w.find('.composer-tray').classes()).toContain('is-landing')
    expect(w.find('.ai-head').exists()).toBe(false)   // 旧头部已删除
  })

  it('展开态使用紧凑密度且不渲染大标题', async () => {
    globalThis.__store = makeStore({
      chatMessages: [{ role: 'user', content: '评分依据？', created_at: '' }],
      chatSession: { stock_code: '000001' },
    })
    const w = mount(AiChatPanel)
    await flushPromises()
    expect(w.find('.composer-tray').classes()).toContain('is-compact')
    expect(w.find('.ai-hero').exists()).toBe(false)
  })
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/components/report/AiChatPanel.test.js`
Expected: FAIL —— `.ai-hero` 不存在、`.composer-tray` 不存在、`.ai-input` 选择器已失效。

- [ ] **Step 3: 重构 `AiChatPanel.vue`**

**保留不动**：`loadedFor` 会话归属守卫、`watch(stockCode)`、`messages` / `steps` / `isExpanded` 计算属性、`scrollToBottom` 与其三个 watch、`send()` 中把 `loadedFor` 置为当前股票的那行。

**改动**：

1. 删除模板里的整个 `<header class="ai-head">…</header>` 及对应样式。
2. 收拢态内容（`v-if="!isExpanded"`）：

```vue
<div class="ai-hero">
  <p class="ai-hero-hi"><span aria-hidden="true">✨</span> Hi, Karens</p>
  <h2 class="ai-hero-title">关于这支股票有什么可以帮你的吗？</h2>
</div>
<ChatComposer
  v-model="input"
  density="landing"
  :max-rows="5"
  :disabled="store.chatAsking"
  @send="send"
/>
```

3. 展开态内容（`v-else`）：现有 `.ai-body`（消息列表 + `ThinkingStepsCard`）+ 顶部大标题移除，底部换成：

```vue
<ChatComposer
  v-model="input"
  density="compact"
  :max-rows="3"
  :disabled="store.chatAsking"
  @send="send"
/>
```

4. `send()` 改为不再自己读 `input.value` 后清空——清空由 `ChatComposer` 内部完成，`send()` 只负责取当前值与调用 `askChat`：

```js
function send() {
  const q = input.value.trim()
  if (!q || store.chatAsking) return
  store.askChat(stockCode.value, {
    question: q,
    report_id: report.value?.id || null,
    stock_name: stockName.value,
  })
  loadedFor.value = stockCode.value
}
```

5. 面板样式：

```css
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
  height: calc(100vh - var(--topnav-height, 64px) - 193px);
  min-height: 420px;
}
/* 收拢态：内容垂直居中后向下偏移，视觉重心偏下 */
.ai-panel.is-collapsed {
  justify-content: center;
  padding-top: 20px;
}
.ai-panel.is-collapsed > .ai-hero { margin-bottom: 8px; }
.ai-panel.is-collapsed > * { transform: translateY(20px); }
/* 展开态：消息区撑满，输入区钉底 */
.ai-panel.is-expanded { justify-content: flex-start; }
```

`.ai-panel:hover` 规则整条删除（去掉变蓝效果）。

6. 大标题样式：

```css
.ai-hero { display: flex; flex-direction: column; gap: 6px; }
.ai-hero-hi { font-size: var(--ax-text-hi); color: var(--ax-text-secondary); margin: 0; }
.ai-hero-title {
  font-size: var(--ax-text-display);
  line-height: 1.26;
  font-weight: 400;
  color: var(--ax-text);
  margin: 0;
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/components/report/AiChatPanel.test.js`
Expected: PASS（9 passed：原 7 条适配 + 新增 2 条）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/report/AiChatPanel.vue frontend/src/components/report/AiChatPanel.test.js
git commit -m "feat(chat_ui): 问答面板改为 landing 形态双内容布局"
```

---

### Task 4: 报告页容器适配与浏览器目检

**Files:**
- Modify: `frontend/src/views/agent/StockReport.vue`（按目检结果微调 `.report-side`）
- Test: 无新增单测，靠全量套件 + 目检

**Interfaces:**
- Consumes: Task 3 的 `.ai-panel` 高度行为

- [ ] **Step 1: 运行全部测试**

Run: `cd frontend && npx vitest run`
Expected: 除既有 `src/stores/stock.test.js:223` 外全绿。

- [ ] **Step 2: 构建校验**

Run: `cd frontend && npm run build`
Expected: 构建成功。

- [ ] **Step 3: 浏览器目检**

Run: `cd frontend && npm run dev`，打开报告页，逐项确认：

1. **首屏未滚动时**，面板完整可见，底部不被视口裁切
2. 收拢态：`✨ Hi, Karens`（13px）+ 大标题（26px）+ 浅灰托盘内嵌白色输入框，托盘有悬浮阴影
3. 托盘圆角 21px、内边距 9px、内框圆角 12px（可用 DevTools 量）
4. 输入框多行：Enter 发送、Shift+Enter 换行、中文输入法选词回车不误发
5. `@`/Auto/Settings/🎤 点击无反应、Tab 键不会停在上面
6. 鼠标悬停面板边框不再变蓝
7. 发一条消息 → 立即转为展开态，大标题消失、输入区变紧凑
8. 两态切换时报告正文宽度无变化、面板高度无跳变
9. 消息气泡与思考步骤卡片外观与改前一致

- [ ] **Step 4: 按目检结果微调 `.report-side`**

若面板底部仍有裁切或对齐问题，在此步调整 `StockReport.vue` 中 `.report-side` 的 `top` / `max-height` / `position`，直到目检第 1 条通过。

- [ ] **Step 5: 提交（仅当 Step 4 确实改动了 `StockReport.vue`）**

```bash
git add frontend/src/views/agent/StockReport.vue
git commit -m "feat(chat_ui): 报告页侧栏适配 landing 面板高度"
```

若目检全部通过、`.report-side` 无需调整，则跳过本步——不要为了「有提交」而制造空改动。
