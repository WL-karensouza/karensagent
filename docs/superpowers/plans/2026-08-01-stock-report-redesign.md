# 投研报告页改版（变体 A 卡片模块式） Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Commit 约定（覆盖本计划所有 commit 步骤）：** 本项目 commit message 用**中文**、conventional 前缀、一句话、不暴露 AI 痕迹（例：`feat(stock_report): 新增方向色助手与中性 token`）。执行时若用户未明确授权提交，则**只暂存/不提交**，把 commit 步骤留给用户确认。
>
> **不要污染他页：** `scoreColor(score)` 与 `decisionBadge(d)` 仍被 `StockDashboard.vue` 使用，二者**签名与语义保持不变**，其既有测试 `src/utils/stock.test.js` **不改**。报告页一律用本计划新增的方向色助手。

**Goal:** 把投研报告页由居中单列改为「左报告 + 右满高 sticky AI 助理」两列，去除装饰彩色背景，对方向/多空/利好利空/估值信号统一「涨红跌绿」、风险等级保持中性灰，落地形态取原型变体 A（卡片模块式）。

**Architecture:** 纯前端 Vue3 SFC + scoped CSS 改版，无新依赖。新增中性灰阶 token 与一组方向色纯函数助手（`utils/stock.js`，带 vitest 单测）；新建满高 `AiChatPanel.vue`；`StockReport.vue` 重构为两列并删除底部追问框；9 个报告模块 + 评分簇按契约去色/上色。实现以已定稿原型 `frontend/src/views/prototype/`（变体 A）为**逐字参照**。

**Tech Stack:** Vue 3.5、Vue Router 4（hash 路由）、Vite 8、vitest + happy-dom、原生 scoped CSS（CSS 变量）。

**Reference（实现前必读）：** 设计规格 `docs/superpowers/specs/2026-08-01-stock-report-redesign.md`；原型变体 A `frontend/src/views/prototype/variants/VariantA.vue`、AI 面板 `frontend/src/views/prototype/AiPanel.vue`、色彩助手 `frontend/src/views/prototype/mockReport.js`。

## Global Constraints

- 不引入任何新依赖。
- 不修改 `StockDashboard.vue` / `AiNews*` 等其他页面；全局 `--green`/`--red`/`--accent` 变量**不改值**。
- `scoreColor`/`decisionBadge` 既有签名与 `src/utils/stock.test.js` 既有测试**保持不变**。
- 方向色所在 CSS 选择器**不得**用 `color: … !important`（会压过内联 `:style` 绑定，致 M3/M4/M5 箭头变黑）。
- 命名：JS 函数/变量 `camelCase`，CSS 类 `kebab-case`，CSS 变量 `--kebab-case`；样式块顶部加中文注释。
- 每个 `.vue` 任务**至多 3 个 .vue 文件**（用户规矩）。
- 组件视觉改动以 `npm run build` 零 error + 浏览器对照变体 A 为验收门（仓库组件层无既有测试，不为本次视觉改版新增组件单测，遵循 YAGNI；纯函数助手走 TDD）。

---

### Task 1: 方向色助手（TDD）+ 中性 Token

**Files:**
- Modify: `frontend/src/utils/stock.js`（追加助手，**不改**既有 `scoreColor`/`decisionBadge`）
- Modify: `frontend/src/utils/stock.test.js`（**追加** describe 块，**不改**既有块）
- Modify: `frontend/src/style.css`（`:root` 追加 4 个中性 token）

**Interfaces（本任务产出，供 Task 3–8 消费）：**
- `dirOf(text): 'up'|'down'|'flat'` — `/看多|偏多/→up`、`/看空|偏空/→down`、否则 `flat`；空值 `flat`
- `verdictColor(text): string` — 决策文本→`var(--red)|var(--green)|var(--sent-mid)`
- `verdictSym(text): string` — 决策文本→`▲|▼|●`
- `trendColor(t): string` / `trendSym(t): string` — `'up'→var(--red)/'↑'`、`'down'→var(--green)/'↓'`、`'flat'→var(--sent-mid)/'·'`，未知键回落灰/`'·'`
- `attrColor(d): string` — `偏多→var(--red)`、`偏空→var(--green)`、`中性→var(--sent-mid)`
- `valSym(v): string` / `valColor(v): string` — `低→↑/var(--red)`、`偏高→↓/var(--green)`、`极高→↓↓/var(--green)`、`合理`等→`·/var(--sent-mid)`

- [ ] **Step 1: 追加失败测试**

在 `src/utils/stock.test.js` 的 import 行扩展并文件末尾追加（既有 `describe('scoreColor')`/`describe('decisionBadge')` 两块**不动**）：

```js
import {
  scoreColor, decisionBadge,
  dirOf, verdictColor, verdictSym,
  trendColor, trendSym, attrColor, valSym, valColor,
} from './stock.js'

// ……既有两块保持原样……

describe('dirOf', () => {
  it('看多/偏多 → up', () => {
    expect(dirOf('谨慎看多')).toBe('up')
    expect(dirOf('强烈看多')).toBe('up')
    expect(dirOf('偏多')).toBe('up')
  })
  it('看空/偏空 → down', () => {
    expect(dirOf('看空')).toBe('down')
    expect(dirOf('谨慎看空')).toBe('down')
  })
  it('中性/空值 → flat', () => {
    expect(dirOf('观望')).toBe('flat')
    expect(dirOf('中性')).toBe('flat')
    expect(dirOf('')).toBe('flat')
    expect(dirOf(null)).toBe('flat')
  })
})

describe('verdictColor / verdictSym（涨红跌绿，灰中性）', () => {
  it('看多 → 红 + ▲', () => {
    expect(verdictColor('谨慎看多')).toBe('var(--red)')
    expect(verdictSym('谨慎看多')).toBe('▲')
  })
  it('看空 → 绿 + ▼', () => {
    expect(verdictColor('看空')).toBe('var(--green)')
    expect(verdictSym('看空')).toBe('▼')
  })
  it('中性 → 灰 + ●', () => {
    expect(verdictColor('观望')).toBe('var(--sent-mid)')
    expect(verdictSym('观望')).toBe('●')
  })
})

describe('trendColor / trendSym', () => {
  it('up → 红 + ↑', () => {
    expect(trendColor('up')).toBe('var(--red)')
    expect(trendSym('up')).toBe('↑')
  })
  it('down → 绿 + ↓', () => {
    expect(trendColor('down')).toBe('var(--green)')
    expect(trendSym('down')).toBe('↓')
  })
  it('flat/未知 → 灰 + ·', () => {
    expect(trendColor('flat')).toBe('var(--sent-mid)')
    expect(trendSym('flat')).toBe('·')
    expect(trendSym('xxx')).toBe('·')
  })
})

describe('attrColor', () => {
  it('偏多红 / 偏空绿 / 中性灰', () => {
    expect(attrColor('偏多')).toBe('var(--red)')
    expect(attrColor('偏空')).toBe('var(--green)')
    expect(attrColor('中性')).toBe('var(--sent-mid)')
  })
})

describe('valSym / valColor（估值：低好红↑、高坏绿↓、合理灰·）', () => {
  it('低 → ↑ 红', () => {
    expect(valSym('低')).toBe('↑')
    expect(valColor('低')).toBe('var(--red)')
  })
  it('合理 → · 灰', () => {
    expect(valSym('合理')).toBe('·')
    expect(valColor('合理')).toBe('var(--sent-mid)')
  })
  it('偏高 → ↓ 绿；极高 → ↓↓ 绿', () => {
    expect(valSym('偏高')).toBe('↓')
    expect(valColor('偏高')).toBe('var(--green)')
    expect(valSym('极高')).toBe('↓↓')
    expect(valColor('极高')).toBe('var(--green)')
  })
})
```

- [ ] **Step 2: 跑测试确认新块失败**

Run: `npm test`
Expected: FAIL —— 新增助手未定义（既有 `scoreColor`/`decisionBadge` 块仍 PASS）。

- [ ] **Step 3: 在 `src/utils/stock.js` 末尾追加实现**

```js
/* ── 报告页方向色助手：涨红跌绿，灰中性（仅报告页使用，不动 scoreColor/decisionBadge） ── */
export function dirOf(text) {
  if (!text) return 'flat'
  if (/看多|偏多/.test(text)) return 'up'
  if (/看空|偏空/.test(text)) return 'down'
  return 'flat'
}
/* 决策方向 → 颜色 / 符号 */
export const verdictColor = t => ({ up: 'var(--red)', down: 'var(--green)', flat: 'var(--sent-mid)' })[dirOf(t)]
export const verdictSym = t => ({ up: '▲', down: '▼', flat: '●' })[dirOf(t)]
/* 趋势方向 up/down/flat → 颜色 / 箭头 */
export const trendColor = t => ({ up: 'var(--red)', down: 'var(--green)', flat: 'var(--sent-mid)' })[t] || 'var(--sent-mid)'
export const trendSym = t => ({ up: '↑', down: '↓', flat: '·' })[t] || '·'
/* 归因方向 偏多/偏空/中性 → 颜色 */
export const attrColor = d => ({ 偏多: 'var(--red)', 偏空: 'var(--green)', 中性: 'var(--sent-mid)' })[d] || 'var(--sent-mid)'
/* 估值水平 → 符号 / 颜色 */
export function valSym(v) {
  return ({ 低: '↑', 偏高: '↓', 极高: '↓↓' })[v] || '·'
}
export function valColor(v) {
  return ({ 低: 'var(--red)', 偏高: 'var(--green)', 极高: 'var(--green)' })[v] || 'var(--sent-mid)'
}
```

- [ ] **Step 4: 跑测试确认全绿**

Run: `npm test`
Expected: PASS（新旧全部通过）。

- [ ] **Step 5: 在 `src/style.css` 的 `:root { … }` 块内追加 4 个中性 token**

在 `:root` 既有变量之后追加（**不删改**既有 `--green`/`--red`/`--accent` 等）：

```css
  /* 报告页中性灰阶语义 token：去装饰彩色后的层级用色 */
  --sent-strong: #2D2A26; /* 强调：近黑，同 --text-primary */
  --sent-mid:    #8B857B; /* 中间：暖中灰 */
  --sent-soft:   #B9B2A6; /* 弱化：暖浅灰 */
  --sent-bg:     #F4F1EB; /* 中性块底：替代原各色背景块 */
```

- [ ] **Step 6: 构建确认无回归**

Run: `npm run build`
Expected: `✓ built`，无 error。

- [ ] **Step 7: Commit**

```bash
git add src/utils/stock.js src/utils/stock.test.js src/style.css
git commit -m "feat(stock_report): 新增报告方向色助手与中性灰阶 token"
```

---

### Task 2: 新建 AiChatPanel.vue（满高聊天占位面板）

**Files:**
- Create: `frontend/src/components/report/AiChatPanel.vue`

**Interfaces:** 无 props / emits（占位态自包含）。被 Task 3 的 `StockReport.vue` 以 `<AiChatPanel />` 引入，置于右列 `.report-side`。

- [ ] **Step 1: 创建组件**（逐字取自原型 `AiPanel.vue` 并加中文注释；结构 = 顶栏 + 会话区`flex:1`可滚 + 钉底输入；外形满高）

```vue
<!-- AI 问答助理占位面板：满高聊天结构，未来直接升级为会话容器 -->
<script setup>
/* 占位期内容：助理标识 + 即将上线徽章 + 说明 + 示例问题 + 禁用输入框 */
</script>

<template>
  <aside class="ai-panel">
    <!-- 头部：标识 + 徽章（固定） -->
    <header class="ai-head">
      <div class="ai-id">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
        </svg>
        <strong>AI 问答助理</strong>
      </div>
      <span class="ai-badge">即将上线</span>
    </header>

    <!-- 会话区：占位态放说明 + 呼吸点 + 示例问题；上线后此处滚动承载消息 -->
    <div class="ai-body">
      <p class="ai-desc">对报告内容追问、解读数据、厘清结论逻辑。</p>
      <div class="ai-dots" aria-hidden="true"><i></i><i></i><i></i></div>
      <div class="ai-examples">
        <p class="ai-ex-title">你可以这样问：</p>
        <ul>
          <li>估值判断的依据是什么？</li>
          <li>主要风险点有哪些？</li>
          <li>北向资金动向稳定吗？</li>
        </ul>
      </div>
    </div>

    <!-- 输入区（原底部 followup-box 移入，禁用占位；钉底） -->
    <footer class="ai-input">
      <input type="text" disabled placeholder="即将上线，敬请期待" />
      <button type="button" disabled>发送</button>
    </footer>
  </aside>
</template>

<style scoped>
/* 满高聊天面板：顶栏 + 会话区(可滚) + 钉底输入，外形不随内容跳动 */
.ai-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: calc(100vh - var(--topnav-height, 64px) - 48px);
  min-height: 520px;
  box-sizing: border-box;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.ai-panel:hover {
  border-color: var(--sent-soft);
  box-shadow: 0 4px 16px rgba(45, 42, 38, 0.06);
}
/* 会话区占满中间，溢出内部滚动 */
.ai-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
/* 头部 */
.ai-head { display: flex; align-items: center; justify-content: space-between; }
.ai-id { display: flex; align-items: center; gap: 8px; color: var(--sent-strong); font-size: 0.92rem; }
.ai-badge {
  font-size: 0.7rem; padding: 3px 10px; border-radius: 999px;
  background: var(--sent-bg); color: var(--sent-mid); border: 1px solid var(--border-color);
}
.ai-desc { margin: 0; font-size: 0.8rem; color: var(--sent-mid); line-height: 1.6; }
/* 呼吸三点：灰阶、缓慢、错峰，唯一"活"元素 */
.ai-dots { display: flex; gap: 6px; }
.ai-dots i {
  width: 5px; height: 5px; border-radius: 50%; background: var(--sent-soft);
  animation: ai-breathe 1.8s ease-in-out infinite;
}
.ai-dots i:nth-child(2) { animation-delay: 0.3s; }
.ai-dots i:nth-child(3) { animation-delay: 0.6s; }
@keyframes ai-breathe {
  0%, 100% { opacity: 0.3; transform: scale(0.85); }
  50% { opacity: 1; transform: scale(1); }
}
/* 示例问题块 */
.ai-examples {
  background: var(--sent-bg); border: 1px solid var(--border-color);
  border-radius: var(--radius-md); padding: 12px 14px;
}
.ai-ex-title { margin: 0 0 6px; font-size: 0.74rem; color: var(--sent-mid); }
.ai-examples ul { margin: 0; padding-left: 16px; display: flex; flex-direction: column; gap: 4px; }
.ai-examples li { font-size: 0.78rem; color: var(--sent-strong); line-height: 1.5; }
/* 输入区钉底 */
.ai-input {
  display: flex; gap: 8px; flex-shrink: 0;
  padding-top: 14px; border-top: 1px solid var(--border-color);
}
.ai-input input {
  flex: 1; min-width: 0; border: 1px solid var(--border-color); border-radius: var(--radius-md);
  padding: 9px 12px; font-size: 0.8rem; font-family: inherit; color: var(--sent-mid);
  background: var(--bg-subtle); outline: none; cursor: not-allowed;
}
.ai-input button {
  height: 36px; padding: 0 16px; border: 1px solid var(--border-color); border-radius: var(--radius-md);
  background: var(--bg-card); font-size: 0.78rem; font-family: inherit; color: var(--sent-mid);
  cursor: not-allowed; opacity: 0.6;
}
</style>
```

- [ ] **Step 2: 构建确认编译通过**

Run: `npm run build`
Expected: `✓ built`，无 error。

- [ ] **Step 3: Commit**

```bash
git add src/components/report/AiChatPanel.vue
git commit -m "feat(stock_report): 新增满高 AI 问答助理占位面板"
```

---

### Task 3: StockReport.vue 两列重构 + 删追问框 + 评分号改决策色

**Files:**
- Modify: `frontend/src/views/agent/StockReport.vue`

**Interfaces:** 消费 Task 1 `verdictColor`、Task 2 `AiChatPanel`。本任务不改对外路由/props。

- [ ] **Step 1: 改 import**（第 5 行追加 `verdictColor`；第 18 行后追加 `AiChatPanel`）

```js
import { scoreColor, verdictColor } from '../../utils/stock.js'
// ……既有模块 import 保持……
import ReportMeta from '../../components/report/ReportMeta.vue'
import AiChatPanel from '../../components/report/AiChatPanel.vue'
```

> 注：`scoreColor` 此页将不再使用，但保留 import 不报错；若 lint 报未使用，可从该行移除 `scoreColor`（**不要**动 `utils/stock.js` 的 `scoreColor` 定义）。

- [ ] **Step 2: 模板包两列 + 评分号改决策色 + 删 followup-box**

把 `<template v-else-if="reportData">` 内的 `<div class="score-card">…</div>` 到 `<ReportMeta …/>` 整段用 `<div class="report-main"> … </div>` 包裹；在其后、`</template>` 之前加右列；把第 91 行 `scoreColor(reportData.score)` 改为 `verdictColor(reportData.decision)`；**删除**第 133–142 行 `<!-- 追问输入框（v2 功能占位） -->` 整个 `<div class="followup-box">…</div>`。结果骨架：

```vue
    <template v-else-if="reportData">
      <div class="report-main">
        <!-- 评分概览区 -->
        <div class="score-card">
          <ScoreGauge :score="reportData.score" :size="130" />
          <div class="score-info">
            <DecisionBadge :decision="reportData.decision" />
            <p class="score-desc">
              综合评分 <strong :style="{ color: verdictColor(reportData.decision) }">{{ reportData.score }}</strong> / 100
            </p>
            <button class="btn-search" @click="handlePush">📤 推送飞书</button>
          </div>
        </div>

        <Module1CoreConclusion :data="reportData.module_1_核心结论" />
        <!-- ……Module2 ~ SignalAttribution + ReportMeta 原样保留于此 div 内…… -->
        <ReportMeta :created-at="store.currentReport.created_at" :token-used="store.currentReport.token_used" />
      </div>

      <!-- 右列：AI 助理（sticky 吸附） -->
      <aside class="report-side">
        <AiChatPanel />
      </aside>
    </template>
```

- [ ] **Step 3: 替换 scoped CSS 的 `.report-page` 规则 + 删 followup CSS + 追加两列规则**

把现有

```css
.report-page {
  max-width: 860px;
  margin: 0 auto;
  padding: 32px 0 60px;
}
```

改为

```css
/* 报告页：去除居中限宽，改由两列布局控制 */
.report-page {
  padding: 32px 0 60px;
}
/* 两列骨架：左报告 + 右 360 sticky AI 面板 */
.report-layout { display: flex; gap: 32px; align-items: flex-start; }
.report-main { flex: 1; min-width: 0; max-width: 792px; }
.report-side {
  width: 360px; flex-shrink: 0;
  position: sticky;
  top: calc(var(--topnav-height, 64px) + 24px);
  max-height: calc(100vh - var(--topnav-height, 64px) - 48px);
  overflow: auto;
}
/* 窄屏堆叠：与全局 .main-content 1280 断点对齐 */
@media (max-width: 1280px) {
  .report-layout { flex-direction: column; }
  .report-main { max-width: 860px; }
  .report-side { width: 100%; max-width: 860px; position: static; max-height: none; }
}
```

并把 `.report-page` 开标签改为 `<div class="report-page"><div class="report-layout">`？——**注意**：两列容器 `.report-layout` 需包裹 `.report-main` 与 `.report-side`。即模板里在 `<template v-else-if="reportData">` 之外、返回按钮/标题之下，用一个 `<div class="report-layout">` 包住「`<template v-else-if="reportData">` 整块」。最终结构：

```vue
  <div class="report-page">
    <button class="btn-back" @click="router.push('/agent/stock')">← 返回仪表盘</button>
    <h1 v-if="store.currentReport" class="report-title">…</h1>
    <!-- 加载/错误/空态 三块保持原位（全宽） -->
    <div class="report-layout">
      <template v-else-if="reportData">
        <div class="report-main"> … </div>
        <aside class="report-side"><AiChatPanel /></aside>
      </template>
    </div>
  </div>
```

> 说明：`v-else-if` 仍需其前面的 `v-if/v-else-if` 兄弟节点（加载/错误/空态块）作为条件链，故 `.report-layout` 要放在条件链**之后**会断链。**正确做法**：把 `.report-layout` 放在条件链**之内**不可行（需包裹多分支）。因此采用：保留条件链原样，仅让 `reportData` 分支内部渲染 `.report-main`+`.report-side`，并把这两者外层再加 `<div class="report-layout">`。即 `reportData` 分支 = `<div class="report-layout"><div class="report-main">…</div><aside class="report-side">…</aside></div>`。加载/错误/空态分支不放进 layout（它们全宽居中显示即可）。**以本说明为准**，覆盖 Step 2 的骨架描述。

最后**删除** scoped CSS 里的 `.followup-box { … }`、`.followup-input { … }`、`.followup-input:disabled { … }` 三段。

- [ ] **Step 4: 浏览器验证**

Run: `npm run dev`，访问 `http://localhost:<port>/#/agent/stock`，点开任一历史报告进入报告页。
Expected: 报告左移成两列；右侧 AI 面板满高且滚动时吸附；综合评分数字按决策着色（看多报告为红）；底部不再有追问输入框；窗口收窄到 <1280px 时上下堆叠。

- [ ] **Step 5: Commit**

```bash
git add src/views/agent/StockReport.vue
git commit -m "refactor(stock_report): 报告页改两列布局并移除底部追问框"
```

---

### Task 4: 评分簇（ScoreGauge + DecisionBadge + Module1）

**Files:**
- Modify: `frontend/src/components/report/ScoreGauge.vue`
- Modify: `frontend/src/components/report/DecisionBadge.vue`
- Modify: `frontend/src/components/report/Module1CoreConclusion.vue`

**Interfaces:** 消费 Task 1 `verdictColor`/`verdictSym`。ScoreGauge 新增 prop `decision`。

- [ ] **Step 1: ScoreGauge.vue —— 环与中心数字改按决策着色**

`<script setup>` 的 props 追加 `decision`，并改颜色计算（替换原 `gaugeColor` 的红黄绿逻辑）：

```js
import { computed } from 'vue'
import { verdictColor } from '../../utils/stock.js'

const props = defineProps({
  score: { type: Number, required: true },
  size: { type: Number, default: 140 },
  decision: { type: String, default: '' },
})
// ……radius / circumference / offset / center / transformStr 保持……
/* 环与数字颜色：按决策方向涨红跌绿（替代原红黄绿渐变） */
const gaugeColor = computed(() => verdictColor(props.decision))
```

模板与 scoped CSS 不变（`gaugeColor` 仍绑定 `:stroke` 与 `:style`）。

- [ ] **Step 2: StockReport.vue 给 ScoreGauge 传 decision**（同一逻辑链，1 行）

把 `<ScoreGauge :score="reportData.score" :size="130" />` 改为：

```vue
<ScoreGauge :score="reportData.score" :size="130" :decision="reportData.decision" />
```

- [ ] **Step 3: DecisionBadge.vue —— 去 emoji、中性底 + 方向符号**

`decisionBadge` 的 emoji 前缀在**此组件内**不再使用；改为渲染中性 chip + 方向符号。把模板改为：

```vue
<template>
  <span v-if="decision" class="dec-badge">
    <span class="dec-sym" :style="{ color: verdictColor(decision) }">{{ verdictSym(decision) }}</span>
    {{ decision }}
  </span>
</template>

<script setup>
import { verdictColor, verdictSym } from '../../utils/stock.js'
defineProps({ decision: { type: String, default: '' } })
</script>
```

scoped CSS 把原 `.badge-long/.badge-short/.badge-neutral` 等彩色背景规则**全部替换**为：

```css
/* 决策徽章：中性底 + 边框，方向由符号颜色承担 */
.dec-badge {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 0.82rem; font-weight: 700;
  padding: 5px 14px; border-radius: 999px;
  background: var(--sent-bg); border: 1px solid var(--border-color); color: var(--sent-strong);
}
.dec-sym { font-weight: 700; }
```

> 若原组件用 `decisionBadge()` 拼字符串再渲染，需改为上面的「符号 span + 文本」结构；以最终不出现 🟢🟡 为准。

- [ ] **Step 4: Module1CoreConclusion.vue —— 去左竖杠 + 支撑/压力箭头着色**

(a) 评分句 `.m1-rating`：去掉 `border-left: 3px solid …`，`border-radius` 由 `0 … 0` 改四角 `var(--radius-sm, 8px)`，背景保留 `var(--sent-bg)`（中性）。
(b) 支撑/压力 chip 去 emoji、箭头着色。模板改为：

```vue
    <div v-if="data.reference_prices" class="m1-prices">
      <span v-if="data.reference_prices.support" class="m1-price">
        <span style="color: var(--red)">↑</span> 支撑位：{{ data.reference_prices.support }}
      </span>
      <span v-if="data.reference_prices.resistance" class="m1-price">
        <span style="color: var(--green)">↓</span> 压力位：{{ data.reference_prices.resistance }}
      </span>
    </div>
```

(c) scoped CSS：`.m1-price` 统一中性（删 `.m1-price.support`/`.m1-price.resistance` 的绿/红底与字色）：

```css
.m1-price {
  font-size: 0.82rem; padding: 6px 14px; border-radius: var(--radius-md);
  font-weight: 500; background: var(--bg-card); border: 1px solid var(--border-color); color: var(--sent-strong);
}
```

- [ ] **Step 5: 浏览器验证**

Run: `npm run dev` 报告页。
Expected: 评分环与中心数字随决策着色（看多=红）；决策徽章无 emoji、▲ 红；M1 评分句无左竖杠；支撑位 ↑ 红、压力位 ↓ 绿，chip 为中性底。

- [ ] **Step 6: Commit**

```bash
git add src/components/report/ScoreGauge.vue src/components/report/DecisionBadge.vue src/components/report/Module1CoreConclusion.vue src/views/agent/StockReport.vue
git commit -m "feat(stock_report): 评分簇改决策方向色并去 emoji 与左竖杠"
```

---

### Task 5: M2 / M3 / M4（估值方向色 + 财务趋势色 + 股价标签中性化）

**Files:**
- Modify: `frontend/src/components/report/Module2CompanyProfile.vue`
- Modify: `frontend/src/components/report/Module3FinancialHealth.vue`
- Modify: `frontend/src/components/report/Module4PriceTrend.vue`

**Interfaces:** 消费 Task 1 `valSym`/`valColor`/`trendColor`/`trendSym`。

- [ ] **Step 1: Module2 —— 估值水平加方向符号 + 着色**

`<script setup>` 引入：`import { valSym, valColor } from '../../utils/stock.js'`
估值那一项（原 `<span class="tag-…">{{ valuation_level }}</span>` 或纯文本）改为：

```vue
      <span class="m2-level" :style="{ color: valColor(data.valuation_level) }">
        {{ valSym(data.valuation_level) }} {{ data.valuation_level }}
      </span>
```

scoped CSS：删除 `.tag-low/.tag-fair/.tag-high/.tag-extreme` 的彩色底/字色规则；`.m2-level { font-weight: 600; }`（颜色由内联 style 给，**不加** `!important`）。其余键值保持中性。

- [ ] **Step 2: Module3 —— 趋势箭头 + 数值按方向着色**

`<script setup>` 引入：`import { trendColor, trendSym } from '../../utils/stock.js'`
趋势行模板改为（数值与箭头同色）：

```vue
        <td class="m3-value" :style="{ color: trendColor(item.trend) }">{{ item.value }}</td>
        <td class="m3-trend" :style="{ color: trendColor(item.trend) }">{{ trendSym(item.trend) }}</td>
```

scoped CSS：删除 `.trend-up`/`.trend-down` 的绿/红底与字色；`.m3-value`/`.m3-trend` 保留等宽/字重，**不得**带 `color … !important`（否则压过内联色，箭头变黑）。警示块若有红底，改 `var(--sent-bg)` + 中性字。

- [ ] **Step 3: Module4 —— 涨跌幅着色 + 两融/主力标签中性化**

`<script setup>` 引入：`import { trendColor, trendSym } from '../../utils/stock.js'`
(a) 20 日涨跌幅值按 `data.direction` 着色：`:style="{ color: trendColor(data.direction) }"`，箭头用 `{{ trendSym(data.direction) }}`。
(b) 删除 `.margin .m4-flow-label { background:#dbeafe; color:#1e40af }` 与 `.force .m4-flow-label { background:#ede9fe; color:#6b21a8 }` 的蓝/紫底与字色，统一 `background: var(--sent-bg); color: var(--sent-strong)`，两融/主力靠**字重/标题文字**区分。`.m4-flow-label` 的 `#eff6ff`/`#f3e8ff` 背景块亦改 `var(--sent-bg)`。

- [ ] **Step 4: 构建 + 浏览器验证**

Run: `npm run build`（须 `✓ built`）；`npm run dev` 报告页。
Expected: M2 估值 `· 合理` 灰；M3 ↑ 行红、↓ 行绿、· 行灰（数值+箭头同色，**非黑**）；M4 涨跌幅按方向着色、资金标签中性。

- [ ] **Step 5: Commit**

```bash
git add src/components/report/Module2CompanyProfile.vue src/components/report/Module3FinancialHealth.vue src/components/report/Module4PriceTrend.vue
git commit -m "feat(stock_report): M2-M4 估值与趋势方向色、股价标签中性化"
```

---

### Task 6: M5 / M7 / M8（北向趋势色 + 利好利空整列色 + 风险中性灰）

**Files:**
- Modify: `frontend/src/components/report/Module5Northbound.vue`
- Modify: `frontend/src/components/report/CatalystList.vue`
- Modify: `frontend/src/components/report/RiskWarningList.vue`

**Interfaces:** 消费 Task 1 `trendColor`/`trendSym`。M7/M8 用 CSS 类，无需新助手。

- [ ] **Step 1: Module5 —— 5 日变化着色**

`<script setup>` 引入：`import { trendColor, trendSym } from '../../utils/stock.js'`
5 日变化值按 `data.direction` 着色并加箭头：

```vue
        <strong :style="{ color: trendColor(data.direction) }">{{ data.change_5d }} {{ trendSym(data.direction) }}</strong>
```

其余（持仓占比、comment）保持中性；`var(--bg-hover)` 背景不动。

- [ ] **Step 2: CatalystList —— 利好/利空整列按涨红跌绿**

模板给两栏加语义类：利好栏 `<div class="m7-col positive">`、利空栏 `<div class="m7-col negative">`（类名以文件实际为准，关键是 positive/negative 二选一）。
scoped CSS：删除 `.sent-positive/.sent-cautious/.sent-neutral` 情绪 chip 的彩色底/字色（改中性底 + 边框）；删除 `.positive .m7-col-title`/`.negative .m7-col-title` 的红/绿字与 `.positive li`/`.negative li` 的绿/红字、`.positive`/`.negative` 的 `#ecfdf5`/`#fef2f2` 背景，**替换**为：

```css
/* 利好/利空整列涨红跌绿：标题 + 列表项 */
.m7-col { background: var(--sent-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); }
.m7-col.positive .m7-col-title, .m7-col.positive li { color: var(--red); }
.m7-col.negative .m7-col-title, .m7-col.negative li { color: var(--green); }
```

> 选择器按文件实际类名对齐（如 `.m7-col-title`/`li`），保证整列标题与条目同色。

- [ ] **Step 3: RiskWarningList —— 风险等级中性三档灰**

删除 `.level-low/.level-mid/.level-high` 与 `.badge-low/.badge-mid/.badge-high` 的绿/黄/红底与字色，统一徽章底 `var(--sent-bg)` + 边框，**文字**按等级三档灰：

```css
.level-badge, .esg-badge { background: var(--sent-bg); border: 1px solid var(--border-color); }
.lv-strong { color: var(--sent-strong); } /* 高 */
.lv-mid    { color: var(--sent-mid); }    /* 中 */
.lv-soft   { color: var(--sent-soft); }   /* 低 */
```

模板按等级绑定类：`高→lv-strong`、`中→lv-mid`、`低→lv-soft`（可在模板内联三元，或加小映射 `levelCls`）。风险行/ESG 块的 `#fef2f2`/`var(--bg-subtle)` 等彩色底改中性。

- [ ] **Step 4: 构建 + 浏览器验证**

Run: `npm run build`；`npm run dev`。
Expected: M5 5 日变化 ↑ 红；M7 利好整列红、利空整列绿；M8 风险等级为黑/中灰/浅灰三档，**无红绿黄**。

- [ ] **Step 5: Commit**

```bash
git add src/components/report/Module5Northbound.vue src/components/report/CatalystList.vue src/components/report/RiskWarningList.vue
git commit -m "feat(stock_report): M5 趋势色、M7 利好利空整列色、M8 风险中性灰"
```

---

### Task 7: M9 / 信号归因（操作指南中性化 + 归因方向色）

**Files:**
- Modify: `frontend/src/components/report/HoldingAdviceCard.vue`
- Modify: `frontend/src/components/report/SignalAttribution.vue`

**Interfaces:** 消费 Task 1 `attrColor`。

- [ ] **Step 1: HoldingAdviceCard —— 三栏 + 提示块中性化**

scoped CSS：删除 `.m9-col.buy`/`.stop`/`.profit` 的蓝/红/绿底与边框，统一 `background: var(--sent-bg); border: 1px solid var(--border-color)`；删除 `.buy .m9-col-label`/`.stop .…`/`.profit .…` 的蓝/红/绿字色（标签改 `color: var(--sent-strong)`）；提示块 `.m9-tip` 的 `#fffbeb` 底 / `#92400e` 字 / `#fef3c7` 改 `background: var(--sent-bg); color: var(--sent-mid)`。模板无需加助手。

- [ ] **Step 2: SignalAttribution —— 横条 + 方向文字按方向着色**

`<script setup>` 引入：`import { attrColor } from '../../utils/stock.js'`
(a) 内联圆点（模板里 `:style="{ background: item.direction === '偏多' ? '#10B981' : … }"` 的三元）**替换**为 `:style="{ background: attrColor(item.direction) }"`。
(b) 横条填充 `:class="dirCls(...)"` 改为内联：`:style="{ width: item.weight + '%', background: attrColor(item.direction) }"`。
(c) 方向文字加色：`:style="{ color: attrColor(item.direction) }"`。
(d) 删除 `.dir-up/.dir-down/.dir-flat` 的绿/红/灰底规则（已改内联）。

- [ ] **Step 3: 构建 + 浏览器验证**

Run: `npm run build`；`npm run dev`。
Expected: M9 买入/止损/止盈三栏中性、提示块中性；归因偏多横条+字红、偏空绿、中性灰。

- [ ] **Step 4: Commit**

```bash
git add src/components/report/HoldingAdviceCard.vue src/components/report/SignalAttribution.vue
git commit -m "feat(stock_report): M9 操作指南中性化、信号归因方向色"
```

---

### Task 8: 全量构建 + 对照变体 A 视觉回归

**Files:** 无代码改动（验证门）。

- [ ] **Step 1: 全量构建**

Run: `npm run build`
Expected: `✓ built`，无 error / 无未用变量告警（若有未用 import，回相应任务清理）。

- [ ] **Step 2: 全量单测**

Run: `npm test`
Expected: 全 PASS（含 Task 1 新增块与既有 `scoreColor`/`decisionBadge` 块）。

- [ ] **Step 3: 浏览器逐条对照验收（spec §11）**

Run: `npm run dev`，报告页 + 仪表盘页都看一遍。核对：
1. 两列布局；右 AI 面板滚动吸附；<1280px 堆叠。
2. 全模块**无彩色背景块**；M8 风险为中性灰。
3. 方向/多空/利好利空/估值**涨红跌绿**生效，M3/M4/M5 箭头确为红绿（**非黑**，验证无 `!important` 覆盖）。
4. AI 面板满高、顶栏/输入钉定、中间可滚、含呼吸点 + 示例问题；底部追问框已无。
5. 卡片 hover 反馈 + 错峰入场动效存在。
6. **仪表盘页 `StockDashboard` 无回归**（分数仍按 `scoreColor` 档位着色、徽章仍为 emoji）。

任一条不符 → 回对应任务修复，**不**进入 Task 9。

- [ ] **Step 4: （无 commit；纯验证）**

---

### Task 9: 清理一次性原型

**Files:**
- Delete: `frontend/src/views/prototype/`（整目录：`ReportRedesignPrototype.vue`、`AiPanel.vue`、`mockReport.js`、`variants/VariantA.vue`、`variants/VariantB.vue`、`variants/VariantC.vue`）
- Delete: `frontend/src/components/PrototypeSwitcher.vue`
- Modify: `frontend/src/router/index.js`（移除 `/prototype/report-redesign` 路由块）

- [ ] **Step 1: 删路由块**

在 `src/router/index.js` 删除整段：

```js
  /* ── PROTOTYPE（一次性）：投研报告页改版，验证完即删 ── */
  {
    path: '/prototype/report-redesign',
    component: () => import('../views/prototype/ReportRedesignPrototype.vue'),
    meta: { title: '原型 · 报告改版' },
  },
```

- [ ] **Step 2: 删原型文件**

```bash
rm -rf src/views/prototype
rm -f src/components/PrototypeSwitcher.vue
```

- [ ] **Step 3: 构建确认无悬挂引用**

Run: `npm run build`
Expected: `✓ built`，无 “Failed to resolve import …/prototype/…” 或 `PrototypeSwitcher` 报错。

- [ ] **Step 4: 浏览器确认原型路由已失效、报告页正常**

Run: `npm run dev`。
Expected: `/#/prototype/report-redesign` 不再渲染原型（落到默认/404 行为）；`/#/agent/stock/report/:id` 正常。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore(stock_report): 移除报告改版一次性原型"
```

---

## 自审记录

- **Spec 覆盖：** §1 三目标→T3/T4–7；§4 布局→T3；§5 色彩（含 M8 中性、逐模块表）→T1+T4–7；§6 AI 面板→T2；§7 卡片式→T4–7（卡片骨架在各模块既有 `.m*-block` 容器上以中性底+边框呈现，错峰动效可视需要在 T4–7 各模块 scoped CSS 加 `animation` + `animation-delay`，参照 VariantA `.va-card`）；§8 文件清单→T1–7 全覆盖，Module6/ReportMeta 确认不动；§9 响应式→T3；§10 边界（不动仪表盘/全局变量）→头部约束 + T8 验证；§11 验收→T8。
- **占位扫描：** 无 TBD/TODO/“补错误处理”/“类似 Task N”；每步含确切代码或确切命令。
- **类型一致：** 助手名 `dirOf/verdictColor/verdictSym/trendColor/trendSym/attrColor/valSym/valColor` 在 T1 定义、T3–7 消费完全一致；ScoreGauge 新 prop `decision` 在 T4 定义并由 T3 模板传入（`reportData.decision`）一致。
- **关键风险已规避：** `scoreColor`/`decisionBadge` 不动（保护仪表盘）；方向色选择器禁用 `!important`（防 M3/M4/M5 黑箭头）。
