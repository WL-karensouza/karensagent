# 交接文档：iFind 股票分析前后端 Code Review

**日期**：2026-07-16
**项目目录**：`d:\karensAgent\.claude\worktrees\ifind-refactor`
**Review 主题**：前后端数据流转、按钮交互准确性、边界条件

---

## 背景

StockSettings.vue 已完成从 HTML 原型到 Vue3 的转换，"精密纸媒交易台"设计系统的 4 个页面全部就位：
- StockDashboard.vue（仪表盘）
- StockSettings.vue（系统设置）
- StockHistory.vue（历史报告）
- StockReport.vue（报告详情）

本次 Review 检查了全部 4 个前端页面 + store + api 层 + 后端路由 + ORM + SKILL 层之间的完整数据链路。

---

## 发现的问题（按严重度排序）

### 🔴 严重 Bug × 2

#### B1. 飞书自动推送开关完全无效

**现象**：用户在 Settings 页打开"自动推送飞书"开关后，分析完成时不会自动推送。

**根因**：飞书开关仅写入 `localStorage['stock_settings_feishu_push']`，但整个前端（Dashboard、store、api）没有任何地方读取它来触发自动推送。`pushToFeishu()` 只在 History 和 Report 页手动调用。

**涉及文件**：
- `frontend/src/views/agent/StockSettings.vue:84-86` — 写入 localStorage ✅
- `frontend/src/views/agent/StockDashboard.vue:75-79` — `handleInvestReport` 不读开关 ❌
- `frontend/src/stores/stock.js:135-165` — `_onSseComplete` 不读开关 ❌

#### B2. 默认分析维度选择完全不影响报告

**现象**：用户在 Settings 页勾选/取消维度后，生成的报告始终包含全部 10 个维度。

**根因**：维度选择仅写入 `localStorage['stock_settings_dimensions']`，但：
1. 前端 API 调用时从不传 dimensions 参数
2. 后端 `report.py` 的 `DIMENSIONS` 是模块级常量，永远处理全部 10 个
3. 后端 API 端点（`/api/stock/skill-report`、`/api/stock/skill-report/invest`）的请求体只有 `stock_code`

**涉及文件**：
- `frontend/src/views/agent/StockSettings.vue:88-93` — 写入 localStorage ✅
- `frontend/src/api/index.js:101-110` — `fetchSkillReport`/`fetchInvestReport` 不传 dimensions ❌
- `backend/stock_agent/skill/report.py:17-28` — `DIMENSIONS` 硬编码常量 ❌
- `backend/routers/stock_api.py:323-341` — 端点不接收维度参数 ❌

---

### 🟡 中等问题 × 4

#### M1. delete/update 自选股失败时无 toast 反馈

**文件**：`frontend/src/stores/stock.js:277-293`
deleteWatchlist 和 updateWatchlist 仅在 `res.code === 0` 时 toast，网络异常 catch 块无提示。对比 addWatchlist 则成功/失败都有 toast。

#### M2. toggleEnabled 存在竞态条件

**文件**：`frontend/src/views/agent/StockSettings.vue:134-138`
快速双击启停按钮时，第二次 `item.enabled` 可能是旧值（第一次 `fetchWatchlist()` 还未完成），导致状态翻转错误。

#### M3. Dashboard 两个分析入口走不同路径

| 入口 | 机制 | 进度展示 |
|------|------|---------|
| 搜索栏"投研报告" | SSE 流式 | ✅ 进度条 |
| 自选股"开始分析" | 轮询(旧) | ❌ 只有 spinner |

**文件**：`frontend/src/views/agent/StockDashboard.vue:277` 调用 `handleAnalyze()` 而非 `handleInvestReport()`

#### M4. iFind 连接检测不真实

**文件**：
- `frontend/src/views/agent/StockSettings.vue:73-78` — 调 `/api/health`
- `backend/main.py:80-82` — 只返回固定 `{"status":"ok"}`，不检测 iFinD MCP 真实可用性

---

### 🟢 低风险 × 3

#### L1. 前端残留旧版 5 维度常量

**文件**：`frontend/src/utils/stock.js:4-9`
`DIMENSIONS` 常量是旧版 market/finance/news/risk/env，与当前 10 维度不一致。经确认未被任何文件导入，但保留会造成混淆。

#### L2. Dashboard 日期硬编码

**文件**：`frontend/src/views/agent/StockDashboard.vue:173`
`MARKET INTELLIGENCE · 2026.07.11` 硬编码，应改为动态 `todayStr`。

#### L3. SSE AbortController 未使用

**文件**：`frontend/src/views/agent/StockDashboard.vue:15`
`sseController` 赋值后从未 `.abort()`，触发新分析时旧 SSE 连接不被取消，可能引发竞态。

---

## 关键文件索引

| 层 | 文件 | 说明 |
|-----|------|------|
| 前端页面 | `frontend/src/views/agent/StockDashboard.vue` | 仪表盘 |
| 前端页面 | `frontend/src/views/agent/StockSettings.vue` | 设置页 |
| 前端页面 | `frontend/src/views/agent/StockHistory.vue` | 历史报告 |
| 前端页面 | `frontend/src/views/agent/StockReport.vue` | 报告详情 |
| Store | `frontend/src/stores/stock.js` | Pinia store，轮询/SSE/CRUD |
| API | `frontend/src/api/index.js` | axios + SSE fetch 封装 |
| 工具 | `frontend/src/utils/stock.js` | 含废弃旧维度常量 |
| 后端路由 | `backend/routers/stock_api.py` | 所有股票 API 端点 |
| 后端 ORM | `backend/database.py` | SQLAlchemy 数据库操作 |
| 后端模型 | `backend/models.py` | ORM 模型定义 |
| SKILL 报告 | `backend/stock_agent/skill/report.py` | 10 维度 DIMENSIONS 常量 |
| SKILL 入口 | `backend/stock_agent/skill/__init__.py` | iFinD call 封装 |
| LLM 分析 | `backend/stock_agent/analyze.py` | DeepSeek prompt + 分析 |
| 渲染 | `backend/stock_agent/render.py` | Markdown 渲染 |
| 入口 | `backend/main.py` | FastAPI 应用入口 |

---

## 🔧 详细修复方案

### B1 飞书自动推送断链 🔴

**改 1 个文件**：`frontend/src/stores/stock.js`

在 `_onSseComplete(mode, data)` 末尾（第 164 行 `this.showToast(...)` 之前），新增飞书自动推送逻辑：

```js
// 飞书自动推送（仅投研报告模式）
if (mode === 'invest' && data.report_id) {
  try {
    const autoPush = localStorage.getItem('stock_settings_feishu_push')
    if (autoPush === 'true') {
      await this.pushToFeishu(data.report_id)
    }
  } catch (_) {}
}
```

注意：`_onSseComplete` 当前不是 async 函数，需加 `async`。

---

### B2 分析维度选择断链 🔴

**涉及 4 个文件，按调用链从底向上改**：

#### B2-1 后端 `report.py`：DIMENSIONS 过滤

`generate_report_stream()` 和 `generate_report_sync()` 各新增可选参数 `dimensions: list[str] | None = None`。

```python
def generate_report_stream(stock_code: str, dimensions: list[str] | None = None):
    # 如果传了 dimensions，只处理指定的维度
    active_dims = [d for d in DIMENSIONS if dimensions is None or d["key"] in dimensions]
    for dim in active_dims:
        ...
```

#### B2-2 后端 `stock_api.py`：端点接收维度参数

`AnalyzeRequest` 新增字段：
```python
class AnalyzeRequest(BaseModel):
    stock_code: str
    dimensions: list[str] | None = None
```

`skill_report` 和 `skill_report_invest` 端点将 `req.dimensions` 透传给 `generate_report_stream()`。

#### B2-3 前端 `api/index.js`：传递维度参数

```js
export function fetchInvestReport(stockCode, callbacks, dimensions = null) {
  const body = { stock_code: stockCode }
  if (dimensions && dimensions.length) body.dimensions = dimensions
  return fetchSSE('/api/stock/skill-report/invest', body, callbacks)
}
```

#### B2-4 前端 `stores/stock.js`：读取 localStorage 维度配置

`triggerInvestReport()` 中：
```js
triggerInvestReport(stockCode) {
  this._startSse('invest')
  // 读取用户维度配置
  let dimensions = null
  try {
    const raw = localStorage.getItem('stock_settings_dimensions')
    if (raw) dimensions = JSON.parse(raw)
  } catch (_) {}
  return api.fetchInvestReport(stockCode, {
    onProgress: (data) => { this._onSseProgress(data) },
    onComplete: (data) => { this._onSseComplete('invest', data) },
    onError: (err) => { this._onSseError(err) },
  }, dimensions)
},
```

---

### M1 delete/update 无失败 toast 🟡

**改 1 个文件**：`frontend/src/stores/stock.js:277-293`

```js
async deleteWatchlist(stockCode) {
  try {
    const res = await api.deleteStockWatchlist(stockCode)
    if (res.code === 0) {
      this.showToast(res.message)
      await this.fetchWatchlist()
    } else {
      this.showToast(res.message || '删除失败')
    }
  } catch (e) {
    this.showToast('删除失败: ' + (e.message || '网络错误'))
  }
  return res
},
```

`updateWatchlist` 同理。

---

### M2 toggleEnabled 竞态 🟡

**改 1 个文件**：`frontend/src/views/agent/StockSettings.vue:134-138`

用局部变量快照当前值，避免快速双击读到旧值：

```js
async function toggleEnabled(item) {
  const next = item.enabled ? 0 : 1  // 快照当前值
  await store.updateWatchlist(item.stock_code, { enabled: next })
}
```

---

### M3 自选股轮播按钮走旧分析路径 🟡

**改 1 个文件**：`frontend/src/views/agent/StockDashboard.vue:277`

```html
<!-- 改前 -->
<button @click="stockCode = item.stock_code; handleAnalyze()">开始分析</button>
<!-- 改后 -->
<button @click="stockCode = item.stock_code; handleInvestReport()">投研报告</button>
```

---

### M4 iFind 连接检测不真实 🟡

**改 1 个文件**：`backend/main.py:80-82`

```python
@app.get("/api/health")
def health_check():
    """健康检查 — 含 iFinD MCP 连通性探测"""
    ifind_ok = False
    try:
        from stock_agent.skill import call_skill
        call_skill("stock/basic", stock_code="600519")  # 轻量探测
        ifind_ok = True
    except Exception:
        pass
    return {"status": "ok", "ifind": ifind_ok}
```

前端 `StockSettings.vue:73-78` 的检测逻辑对应的也改为检查 `res.ifind` 字段。

---

### L1 删除旧版 5 维度常量 🟢

**改 1 个文件**：`frontend/src/utils/stock.js:4-9`

删除整个 `DIMENSIONS` 导出（确认无任何文件导入后）。

---

### L2 Dashboard 硬编码日期 🟢

**改 1 个文件**：`frontend/src/views/agent/StockDashboard.vue:173`

```html
<!-- 改前 -->
<span class="issue-tag">MARKET INTELLIGENCE · 2026.07.11</span>
<!-- 改后 -->
<span class="issue-tag">MARKET INTELLIGENCE · {{ todayStr }}</span>
```

在 `<script>` 中新增 `todayStr` 计算属性。

---

### L3 SSE AbortController 未清理 🟢

**改 1 个文件**：`frontend/src/views/agent/StockDashboard.vue:15,75-79`

在 `handleInvestReport()` 开头先 abort 旧连接：

```js
function handleInvestReport() {
  if (sseController) sseController.abort()  // 取消旧 SSE
  const code = validateCode()
  if (!code) return
  sseController = store.triggerInvestReport(code)
}
```

---

## 执行顺序

| 轮次 | Bug | 文件数 | 预计改动量 |
|------|-----|--------|-----------|
| 第一轮 | B1 飞书自动推送 | 1 | ~10 行 |
| 第二轮 | B2 维度选择 | 4 | ~50 行 |
| 第三轮 | M1+M2+M3+L1+L2+L3 | 4 | ~30 行 |
| 第四轮 | M4 健康检查 | 1 | ~15 行 |

**建议先修 B1（最快见效），再修 B2（链路最长），最后批量修 M 和 L。**

---

## 当前约束

- 前后端一体部署，Vite dev server proxy 到 FastAPI :8900
- 本地开发用 SQLite，生产用 MySQL
- iFinD MCP 免费版限 2 QPS，当前 10 维度串行约 20-30s
- 不修改导航栏（TopNav.vue）
- 不可硬编码数据
- 遵循"精密纸媒交易台"设计系统

---

## 建议技能

- `/code-review` — 修复后重新验证
- `ifind-finance-data` — iFinD SKILL 文档参考
- `verification-before-completion` — 修复完成后验证
