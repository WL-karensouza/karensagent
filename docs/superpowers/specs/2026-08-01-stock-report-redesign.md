# 投研报告页改版设计（StockReport Redesign）

> 日期：2026-08-01
> 范围：`frontend/src/views/agent/StockReport.vue` 及其 13 个报告子组件
> 落地基准：原型变体 **A（卡片模块式）**；色彩规则 / 两列布局 / AI 面板为三变体共通，已完整记录
> 关联原型：`frontend/src/views/prototype/`（一次性，实现完成即删）
> 状态：设计定稿，待实现规划

---

## 1. 概述

现状 `StockReport.vue` 的 `.report-page` 为 `max-width: 860px; margin: 0 auto` **单列居中**；各报告模块大量使用硬编码彩色背景与彩色文字（绿/红/黄/蓝/紫）；页面**底部**有一个禁用的"追问 AI"输入框（v2 占位）。

本次改版做三件事：

1. **整体左移**：报告由居中单列改为「左报告 + 右 AI 助理」两列布局。
2. **去除装饰彩色**：删除所有模块的彩色**背景块**，统一为中性底 + 边框。
3. **右侧引入 AI 问答助理**：将原底部追问框移入右侧 sticky 面板，作为即将上线的占位入口。

---

## 2. 设计原则

- **简约中性为底**：页面以暖白/暖灰中性色为主，去除装饰性彩色背景，模块靠留白、边框、字重建立层级。
- **方向语义保留红绿（涨红跌绿）**：经原型评估，纯黑白灰使财经方向信息失去辨识度，故对**方向 / 多空 / 利好利空 / 估值**类信号恢复 A 股习惯配色——**红 = 涨 / 看多 / 利好 / 低估值**，**绿 = 跌 / 看空 / 利空 / 高估值**，**灰 = 中性 / 持平 / 合理**。这是对"全中性化"的唯一例外，且仅限于语义信号。
- **风险等级保持中性**：M8 的高/中/低是"严重程度"而非多空方向，不上红绿，用三档灰阶区分，避免语义混淆。
- **不污染他页**：全局 `--green / --red` 变量保留原值供仪表盘等其他页面使用；改动仅限报告页作用域。

---

## 3. 原型探索与变体选定

为回答"模块视觉形态选哪种"，构建了三个结构不同的变体（中性色 + 两列 + sticky AI 面板三者锁定，仅模块形态不同），经 `?variant=` 切换评估：

| 变体 | 形态 | 结论 |
|---|---|---|
| **A 卡片模块式** | 每模块独立白卡 + 130px 环形评分 | ✅ **选定**：模块边界清晰，最接近最终落地形态 |
| B 长文档式 | 无卡片，章节编号 + 发丝线，评分做排版 hero | 备选（阅读沉浸，但信息扫描弱） |
| C 高密度财报式 | 表格主导 + 等宽数字 + 双栏网格 | 备选（密度高，但留白与节奏逊于 A） |

**选定 A**。B / C 的可用片段（如评分 hero、紧凑表格）可在实现阶段酌情借鉴，但骨架以 A 为准。

---

## 4. 页面布局

### 4.1 结构

```
<div class="report-page">                 ← 删除原 860px 居中
  <button class="btn-back">← 返回仪表盘</button>     ┐ 整页顶部，全宽
  <h1 class="report-title">名称（代码）投研报告</h1>  ┘
  <div class="report-layout">             ← 两列容器
    <div class="report-main">             ← 左列：加载/错误/空态 + 评分卡 + M1~M9 + 信号归因 + 元信息
    <aside class="report-side">           ← 右列：<AiChatPanel />
  </div>
</div>
```

- **返回按钮 + 标题**置于整页顶部全宽（不塞进左列）：标题是整页标题，右栏仅为辅助工具，层级更清晰。

### 4.2 关键样式

```css
.report-layout { display: flex; gap: 32px; align-items: flex-start; }
.report-main   { flex: 1; min-width: 0; max-width: 792px; }   /* 1184 - 360 - 32 ≈ 792，接近原 860 阅读宽 */
.report-side   {
  width: 360px; flex-shrink: 0;
  position: sticky;
  top: calc(var(--topnav-height, 64px) + 24px);
  max-height: calc(100vh - var(--topnav-height, 64px) - 48px);
  overflow: auto;                          /* 兜底；正常由面板内部滚动 */
}
```

外壳约束：`.main-content` 全局限宽 1280px、内边距 48px，报告页可用内容宽约 **1184px**，故左列 792px + 间距 32px + 右列 360px 恰好铺满。

---

## 5. 色彩系统

### 5.1 中性 Token（新增于 `style.css :root`）

```css
--sent-strong: #2D2A26;   /* 强调：近黑，同 --text-primary */
--sent-mid:    #8B857B;   /* 中间：暖中灰 */
--sent-soft:   #B9B2A6;   /* 弱化：暖浅灰 */
--sent-bg:     #F4F1EB;   /* 中性块底：替代原各色背景块 */
```

### 5.2 方向语义色（涨红跌绿，复用项目全局变量）

```css
/* 红涨 / 绿跌 / 灰中性，直接用现有 --red #DC2626 / --green #166534 / --sent-mid */
```

### 5.3 逐模块上色契约

| 模块 | 元素 | 颜色规则 |
|---|---|---|
| 评分区 | 环形仪表盘 + 中心数字 + 决策符号 ▲▼● | 按决策方向：看多=红 / 看空=绿 / 中性=灰 |
| M1 | 支撑位 `↑` / 压力位 `↓` | 支撑=红 / 压力=绿（仅箭头符号着色，文字中性） |
| M2 | 估值水平 | 低=`↑`红 / 合理=`·`灰 / 偏高=`↓`绿 / 极高=`↓↓`绿 |
| M3 | 财务趋势箭头 + 数值 | up=红 / down=绿 / flat=灰（数值与箭头同色） |
| M4 | 20 日涨跌幅 | 按 direction 红/绿/灰 |
| M5 | 北向 5 日变化 | 按 direction 红/绿/灰 |
| M7 | 利好整列 / 利空整列 | 利好（标题+列表项）=红 / 利空=绿 |
| M8 | 风险等级 高/中/低 | **中性三档灰**（strong/mid/soft），不上红绿 |
| M9 | 买入/止损/止盈三栏 | 中性底 + 边框（操作档位非多空信号） |
| 信号归因 | 因子横条 + 方向文字 | 偏多=红 / 偏空=绿 / 中性=灰 |

> 实现建议：在 `mockReport.js`/对应 util 中以方向映射集中维护符号与颜色（`▲▼●`、`↑↓·`、红/绿/灰），各组件引用，避免硬编码散落。

---

## 6. AI 问答助理面板（AiChatPanel.vue 新建）

满高聊天面板，**外形固定占满视口、内部会话区滚动**（不随消息把整页撑长，输入框始终可见）。

```
┌──────────────────────────────┐
│  ◎ AI 问答助理      [即将上线] │  ← 顶栏（固定）
│──────────────────────────────│
│  对报告内容追问、解读数据、     │
│  厘清结论逻辑                 │  ┐
│          · · ·  (灰阶呼吸)    │  │ 会话区 flex:1，溢出内部滚动
│  你可以这样问：                │  │ （占位态：说明+呼吸点+示例问题）
│  · 估值判断的依据是什么？      │  │ （上线后：承载消息列表）
│  · 主要风险点有哪些？          │  ┘
│  · 北向资金动向稳定吗？        │
│──────────────────────────────│
│ [ 即将上线，敬请期待     ] [发送] │  ← 输入区（钉底，顶部分隔线）
└──────────────────────────────┘
```

- 关键样式：`.ai-panel { display:flex; flex-direction:column; height: calc(100vh - var(--topnav-height,64px) - 48px); min-height: 520px; }`；`.ai-body { flex:1 1 auto; min-height:0; overflow-y:auto; }`；`.ai-input { flex-shrink:0; border-top:1px solid var(--border-color); }`
- **示例问题**取自报告语境（估值 / 风险 / 资金），而非泛泛问候，建立使用预期。
- **呼吸三点**为唯一"活"元素，灰阶缓慢错峰动画，暗示"AI 正在路上"。
- 圆角 / 边框 / 背景全部复用现有 token；hover 边框微深 + 轻阴影过渡。
- 原 `StockReport.vue` 底部 `followup-box` **删除**，职责完整移交本组件；未来接入会话时此组件直接升级为聊天容器。

---

## 7. 报告组件改造规则（卡片模块式 / 变体 A）

- **每模块一张白卡**：`background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 24px 28px; margin-bottom: 20px;`
- **卡片头**：模块编号徽章（`M1`…`SA`，等宽小字 + 中性底描边）+ 模块标题。
- **微交互**：卡片 hover 边框微深 + 轻阴影；卡片错峰淡入上移（纯 CSS `animation-delay`，不引 JS 库）。
- **去色**：删除所有模块彩色背景块，统一 `--sent-bg` + 边框；语义信号按 §5.3 上红绿/灰。
- **评分卡**：环形仪表盘由"红黄绿渐变"改为按决策方向着色（§5.3）；决策徽章去 emoji（🟢🔴 → ▲▼●）+ 中性底。

---

## 8. 文件改动清单

| 文件 | 改动 |
|---|---|
| `style.css` | `:root` 新增 4 个中性 token（§5.1） |
| `views/agent/StockReport.vue` | 两列布局重构（§4）；删 `followup-box`；引入 `AiChatPanel` |
| `components/report/AiChatPanel.vue` | **新建**（§6） |
| `components/report/ScoreGauge.vue` | 环色 + 中心数字 → 决策方向色 |
| `utils/stock.js` | `scoreColor()` → 方向色；`decisionBadge()` 🟢🔴 → ▲▼● |
| `components/report/DecisionBadge.vue` | 彩色 chip → 中性底 + 符号 + 字重 |
| `components/report/Module1CoreConclusion.vue` | 去 M1 评分句左竖杠；支撑/压力箭头按 §5.3 着色；去 🟢 emoji |
| `components/report/Module2CompanyProfile.vue` | 估值水平按 §5.3 加方向符号 + 着色；其余键值中性 |
| `components/report/Module3FinancialHealth.vue` | trend up/down 箭头 + 数值按 §5.3 着色 |
| `components/report/Module4PriceTrend.vue` | 涨跌幅按 direction 着色；资金标签中性化 |
| `components/report/Module5Northbound.vue` | 5 日变化按 direction 着色 |
| `components/report/CatalystList.vue` | 利好整列=红 / 利空整列=绿（§5.3） |
| `components/report/RiskWarningList.vue` | 风险等级 → 中性三档灰（§5.3） |
| `components/report/HoldingAdviceCard.vue` | 三栏底色中性化；提示块去黄 |
| `components/report/SignalAttribution.vue` | 内联圆点 + 横条 + 方向文字按 §5.3 着色 |
| `Module6Shareholders.vue` / `ReportMeta.vue` | 已用中性变量，**不动** |

> 注意 CSS 优先级坑：若某选择器以 `color: … !important` 设默认色，会压过内联 `:style` 绑定，导致方向色失效；实现时方向色所在选择器**不得**加 `!important`。

---

## 9. 响应式

- `@media (max-width: 1280px)`（与全局 `.main-content` 断点对齐）：`.report-layout { flex-direction: column; }`；`.report-main { max-width: 860px; }`（堆叠后恢复原单列阅读宽）；`.report-side { width: 100%; max-width: 860px; position: static; max-height: none; }`（面板落至报告下方，仍满高）。

---

## 10. 边界与非目标

- 数据表格、图表组件内部不动（局部修改原则）。
- 其他页面（StockDashboard、AiNews 等）不受影响；全局 `--green / --red` 不改值。
- 不引入新依赖；动效纯 CSS。
- 不保留任何渐变 / 彩色背景 / emoji 圆点（除方向语义红绿外）。

---

## 11. 验收标准

1. 报告左移成两列；右 AI 面板滚动时 sticky 吸附，窄屏（<1280px）堆叠。
2. 所有模块**无彩色背景块**；M8 风险等级为中性灰。
3. 方向/多空/利好利空/估值信号**涨红跌绿**生效，且不被 `!important` 覆盖（M3/M4/M5 箭头确为红绿，非黑）。
4. AI 面板满高、顶栏/输入钉定、中间可滚、含呼吸点与示例问题；底部 `followup-box` 已移除。
5. 卡片 hover 反馈 + 错峰入场动效存在。
6. 其他页面无回归。
