# 03 · 页面模板全清单（57 个）

> 2026-10-29 用 `template --list` 实测。原始输出见 `raw/astryx-templates.txt`。

---

## ⚠️ 先看：四个名不副实的 slug

| slug 字面以为 | 实际是 |
|---|---|
| `dashboard` | Analytics Dashboard —— 最普通的仪表盘 |
| `table-page` | **Searchable** Table（可搜索表格） |
| `table-filter` | **Filterable** Table（渐进式筛选，比 table-page 复杂） |
| `library` | **Card Grid**（卡片网格，跟「库」无关） |

**选模板一律看 `name` 和 `description`，别按 slug 猜。**

---

## 全清单

| # | slug | 名称 |
|---|---|---|
| 1 | `ai-chat` | AI Chat Conversation |
| 2 | `ai-chat-landing` | AI Chat Landing |
| 3 | `blank` | Blank（空白骨架） |
| 4 | `canvas-editor` | Canvas Editor |
| 5 | `centered-hero` | Centered Hero |
| 6 | `checkout-wizard` | Checkout Wizard |
| 7 | `classic-gallery` | Classic Gallery |
| 8 | `contact-form` | Contact Form |
| 9 | `dashboard` | Analytics Dashboard |
| 10 | `dashboard-alert-rail` | Service Monitoring Dashboard |
| 11 | `dashboard-cohort-funnel` | Funnel & Cohort Dashboard |
| 12 | `dashboard-comparison` | Data Dashboard |
| 13 | `dashboard-composition` | Portfolio Dashboard |
| 14 | `dashboard-progress` | Project Status Dashboard |
| 15 | `dashboard-scorecard` | Executive Summary Dashboard |
| 16 | `detail-page` | Order Detail |
| 17 | `documentation` | Documentation Catalog |
| 18 | `documentation-design` | Documentation Design |
| 19 | `documentation-technical` | Documentation Technical |
| 20 | `editor` | Page Editor |
| 21 | `file-explorer` | File Explorer |
| 22 | `form-two-column` | Two-column Form |
| 23 | `form-wizard` | Form Wizard |
| 24 | `form-wizard-dialog` | Dialog Wizard |
| 25 | `form-wizard-inline` | Inline Wizard |
| 26 | `form-wizard-vertical` | Vertical Wizard |
| 27 | `gallery-hero` | Gallery Hero |
| 28 | `ide` | IDE |
| 29 | `incident-console` | Incident Console（WIP） |
| 30 | `kanban-board` | Kanban Board |
| 31 | `library` | Card Grid |
| 32 | `login` | Basic Login |
| 33 | `login-card` | Login Card |
| 34 | `login-split` | Login Split |
| 35 | `login-sso` | Login SSO |
| 36 | `messaging-shell` | Messaging Shell（WIP） |
| 37 | `mixed-gallery` | Mixed Gallery |
| 38 | `payment-form` | Checkout Form |
| 39 | `product-detail` | Product Detail |
| 40 | `product-gallery` | Product Gallery |
| 41 | `settings` | Settings Form |
| 42 | `settings-dialog` | Settings Dialog |
| 43 | `settings-sidebar` | Settings Panels |
| 44 | `shell-nav` | Shell Nav |
| 45 | `shell-side-nav` | Side Nav |
| 46 | `shell-top-nav` | Top Nav |
| 47 | `side-gallery` | Side Gallery |
| 48 | `table` | Simple Table（WIP） |
| 49 | `table-collapsible` | Collapsible Table |
| 50 | `table-comparison` | Comparison Table |
| 51 | `table-filter` | Filterable Table |
| 52 | `table-grouped` | Grouped Table |
| 53 | `table-inbox` | Inbox Table |
| 54 | `table-page` | Searchable Table |
| 55 | `table-tree` | Tree Table |
| 56 | `theme-showcase` | Theme Showcase |
| 57 | `work-item-detail` | Work Item Detail |

> 标 **WIP** 的 3 个（`incident-console`、`messaging-shell`、`table`）官方自己标了未完成，**别用**。

---

## 做对话/Agent 界面时最有用的几个

| 需求 | 模板 |
|---|---|
| 完整对话 + 侧边产物面板 | `ai-chat` |
| 首屏空态（中央输入框 + 推荐词） | `ai-chat-landing` |
| 左右分栏工作台 | `shell-side-nav` / `shell-nav` |
| 表格（可搜索/可折叠/可分组/对比矩阵/树形） | `table-page` `table-collapsible` `table-grouped` `table-comparison` `table-tree` |
| 报告/仪表盘（文字栏 + 评分卡） | `dashboard-scorecard` |
| 设置页 | `settings` / `settings-sidebar` |
| 登录 | `login-card` / `login-split` / `login-sso` |

---

## 区块模板（Block Templates）669 个

`template --list` 的第二段叫 Block Templates，**实际是「按组件归类的区块示例」**，不是页面。

命名规律 `<组件名><变体名>`，例如 `ChatComposerFullFeatured`、`TableSortableTable`。

**用途是抄用法**：想知道某个组件某个状态怎么写，直接生成对应区块看源码，或去 `raw/astryx-templates.txt` 里 grep。

统计（实测）：

| 组件族 | 区块示例数 |
|---|---|
| `Chat*` | **60**（覆盖 15 个组件） |
| `Table*` | **19** |
