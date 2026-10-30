# OpenStock 独立站拆分 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 karensagent 的股票模块（含投研报告、自选股、karens 问答助理）复制到独立仓库 openstock，成为一个能在本机跑通的独立站点。

**Architecture:** 从 karensagent 克隆完整 git 历史到 `D:\openstock`，删除所有非股票文件，再改造前端外壳（路由扁平化 / 导航简化 / API 裁剪）与后端入口（去掉新闻路由与调度器）。数据库已就绪（`openstock` 库，4 张表，数据与结构均已核验一致）。

**Tech Stack:** Vue 3.5 + Vite 8 + Pinia + vue-router｜FastAPI + SQLAlchemy 2 + MySQL｜Vitest + pytest

**Spec:** `docs/superpowers/specs/2026-10-30-openstock-split-design.md`

## Global Constraints

- 工作目录：`D:\openstock`（全新克隆，不动 `D:\karensAgent`）
- 前端端口 **5174**，后端端口 **8901**，数据库 **openstock**（`localhost:3306`）
- 品牌名 **OpenStock**
- **绝不修改、绝不删除** `D:\karensAgent` 里的任何文件
- 所有新增/修改的代码保留中文注释风格；CSS 样式块顶部写明用途
- 前端变量/函数 camelCase，Vue 组件 PascalCase；Python 函数/变量 snake_case
- 后端 commit message 用中文，一句话说明改动
- `.env` 不进 git

## Review Focus

以下是设计文档隐含、但没有专门测试覆盖的失效场景，实施时逐个盯住：

1. **后端因残留的新闻 import 启动即崩** —— `main.py` / `database.py` / `conftest.py` 三处任一漏删，`python main.py` 直接 ImportError
2. **路由扁平化后旧链接失效** —— 任何残留的 `/agent/stock` 前缀会导致 404，且 `TopNav` 高亮态失灵
3. **API 裁剪后页面白屏** —— 某个组件仍调用已删除的 `getDashboardStats` / `getHistory`，运行时报 undefined
4. **构建配置残留 TresJS** —— `vite.config.js` 仍 import `@tresjs/core` 而 `package.json` 已删依赖，`npm run build` 直接失败
5. **测试环境依赖新闻模块** —— `conftest.py` 的 `import ai_news_agent.scheduler` 会让所有后端测试无法启动

---

### Task 1: 建立 openstock 工作区

**Files:**
- Create: `D:\openstock\`（整仓克隆）
- Delete: 见下方删除清单

**Interfaces:**
- Consumes: 无（起点）
- Produces: `D:\openstock` 一个只含股票相关文件的可运行骨架，`git log` 保留 karensagent 的完整历史

- [ ] **Step 1: 克隆 karensagent 到 D 盘**

```bash
cd /d
git clone https://github.com/WL-karensouza/karensagent.git openstock
cd /d/openstock
git log --oneline -3
```

Expected: 看到 `b8be0ec docs: 新增 OpenStock 独立站拆分设计` 等提交，历史完整。

- [ ] **Step 2: 删除前端非股票文件**

```bash
cd /d/openstock/frontend

# 页面
rm -f src/views/OfficeHome.vue
rm -f src/views/HomeLegacy.vue
rm -f src/views/Settings.vue
rm -f src/views/agent/AiNewsDashboard.vue
rm -f src/views/agent/AiNewsHistory.vue
rm -f src/views/agent/StockPlaceholder.vue

# 组件（3D 与无人引用）
rm -rf src/components/office
rm -f src/components/EmptyState.vue
rm -f src/components/SelectPicker.vue
rm -f src/components/DatePicker.vue
rm -f src/components/AnimatedClock.vue

# 3D 相关
rm -rf src/composables
rm -rf public/models
rm -f public/undraw_alarm-clock_zgtg.svg
rm -f public/undraw_cool-girl-avatar_fifz.svg
rm -f public/undraw_cool-guy-avatar_qjc4.svg
rm -f public/undraw_shy-guy-avatar_094a.svg
rm -f "public/sexy 1.svg"
rm -f public/icons.svg
```

Expected: 命令无报错。`public/favicon.svg` 保留。

- [ ] **Step 3: 删除后端非股票文件**

```bash
cd /d/openstock/backend
rm -rf ai_news_agent
rm -f routers/config_api.py
rm -f tests/test_ai_news_agent.py
rm -f karens_agent.db
rm -f deploy.sh
rm -rf stock_agent/reports/failures
mkdir -p stock_agent/reports/failures

# 原项目的 stock_agent 是隐式命名空间包（没有 __init__.py），
# 独立仓库里必须补上，否则打包/导入行为可能与原项目不同
touch stock_agent/__init__.py

# 清理本地临时目录
rm -rf /d/openstock/temp
```

Expected: `routers/` 下只剩 `__init__.py` 与 `stock_api.py`。

- [ ] **Step 4: 精简 docs 目录**

只保留对 OpenStock 有价值的文档：

```bash
cd /d/openstock/docs
ls
```

然后删除除以下之外的一切：`astryx/`、`PRD-stock-agent.md`、`PRD-ai-qa-assistant.md`、`superpowers/`。

Expected: `ls docs/` 只剩 `astryx  PRD-stock-agent.md  PRD-ai-qa-assistant.md  superpowers`。

- [ ] **Step 5: 验证剩余文件清单**

```bash
cd /d/openstock
echo "=== 前端 vue 文件 ===" && find frontend/src -name "*.vue" | sort
echo "=== 后端 py 顶层 ===" && ls backend/*.py
echo "=== 后端目录 ===" && ls backend/
```

Expected:
- 前端 `.vue` 只剩：`App.vue`、`TopNav.vue`、`DividerLine.vue`、`report/` 下 21 个、`views/agent/` 下 4 个 Stock 页面
- 后端顶层只剩：`config.py`、`database.py`、`main.py`、`models.py`、`requirements.txt`
- 后端目录只剩：`routers/`、`stock_agent/`、`chat_agent/`、`tests/`

- [ ] **Step 6: 提交**

```bash
cd /d/openstock
git add -A
git commit -m "refactor: 移除 AI 新闻与 3D 办公室，只保留股票模块"
```

---

### Task 2: 后端数据层拆分

**Files:**
- Modify: `backend/models.py`（删除 `PushHistory` 类）
- Modify: `backend/database.py:49-53`（删除 AiNewsReport import）
- Modify: `backend/tests/conftest.py`（删除第 ④ 步 scheduler 禁用）
- Test: `backend/tests/test_openstock_scope.py`（新建）

**Interfaces:**
- Consumes: Task 1 的骨架
- Produces: `init_db()` 只创建 4 张股票表；`models` 模块只暴露 `StockReport` / `StockWatchlist` / `ChatSession` / `ChatMessage`

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_openstock_scope.py`：

```python
"""OpenStock 拆分边界测试：确认新闻模块的痕迹已彻底清除"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_models_has_no_push_history():
    """models 模块不应再导出 AI 新闻专用的 PushHistory"""
    import models
    assert not hasattr(models, "PushHistory"), "PushHistory 应已删除"


def test_models_exposes_four_stock_tables():
    """models 模块必须保留 4 个股票相关 ORM 模型"""
    import models
    for name in ("StockReport", "StockWatchlist", "ChatSession", "ChatMessage"):
        assert hasattr(models, name), f"{name} 缺失"


def test_init_db_creates_only_stock_tables():
    """init_db 建表后，不应出现 ai_news_reports / push_history"""
    from database import init_db, engine
    from sqlalchemy import inspect

    init_db()
    tables = set(inspect(engine).get_table_names())
    assert "stock_reports" in tables
    assert "stock_watchlist" in tables
    assert "chat_sessions" in tables
    assert "chat_messages" in tables
    assert "ai_news_reports" not in tables
    assert "push_history" not in tables
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /d/openstock/backend
python -m pytest tests/test_openstock_scope.py -v
```

Expected: FAIL —— `test_models_has_no_push_history` 断言失败（PushHistory 仍存在）；`conftest.py` 可能直接 ImportError（因为 `import ai_news_agent.scheduler`）。

- [ ] **Step 3: 修复 conftest.py，让测试环境不再依赖新闻模块**

在 `backend/tests/conftest.py` 中删除第 ④ 步整段：

```python
# ④ 禁用 ai_news 后台调度器：main.py lifespan 会启动 APScheduler 定时任务，
#    测试环境不应启动真实调度器（否则后台线程在 pytest 关闭捕获后写 stdout，
#    触发 "I/O operation on closed file" 错误）
import ai_news_agent.scheduler as _sched
_sched.start_scheduler = lambda: None
_sched.stop_scheduler = lambda: None
```

同时把文件头部 docstring 里提到 ai_news 的说明一并删掉。

- [ ] **Step 4: 运行测试，确认推进到下一个失败**

```bash
cd /d/openstock/backend
python -m pytest tests/test_openstock_scope.py -v
```

Expected: `test_models_has_no_push_history` 仍 FAIL（PushHistory 还没删）。

- [ ] **Step 5: 从 models.py 删除 PushHistory**

删除 `backend/models.py` 中 `class PushHistory(Base)` 整个类定义（含 `__tablename__ = "push_history"` 及其全部字段）。

保留：`StockReport`、`StockWatchlist`、`ChatSession`、`ChatMessage` 四个类。

- [ ] **Step 6: 从 database.py 的 init_db 删除新闻 import**

把 `backend/database.py` 的 `init_db()` 改为：

```python
def init_db():
    """创建所有表"""
    from models import Base as ModelsBase
    ModelsBase.metadata.create_all(bind=engine)
```

（删掉 `from ai_news_agent.models import AiNewsReport` 这一行）

- [ ] **Step 7: 运行测试，确认全部通过**

```bash
cd /d/openstock/backend
python -m pytest tests/test_openstock_scope.py -v
```

Expected: 3 passed。

- [ ] **Step 8: 跑一遍现有数据层测试**

```bash
cd /d/openstock/backend
python -m pytest tests/test_models.py tests/test_history.py -v
```

Expected: 全部 PASS。若有因删除 PushHistory 导致的失败，按失败信息修正 —— 但 `test_models.py` 测的是 Pydantic 模型（`stock_agent.models`），不涉及 ORM，预期不受影响。

- [ ] **Step 9: 提交**

```bash
cd /d/openstock
git add backend/models.py backend/database.py backend/tests/conftest.py backend/tests/test_openstock_scope.py
git commit -m "refactor(backend): 移除新闻推送模型与调度器依赖"
```

---

### Task 3: 后端入口改造与启动验证

**Files:**
- Modify: `backend/main.py`（删除新闻路由与调度器）
- Modify: `backend/requirements.txt`（补 `requests`）
- Test: `backend/tests/test_openstock_scope.py`（追加路由断言）

**Interfaces:**
- Consumes: Task 2 的 `init_db()`（只建 4 张表）
- Produces: 一个只注册 `/api/stock/*`、`/api/chat/*`、`/api/health` 的 FastAPI 应用，可用 `python main.py` 在 8901 端口启动

- [ ] **Step 1: 追加失败测试**

在 `backend/tests/test_openstock_scope.py` 末尾追加：

```python
def test_main_registers_only_stock_and_chat_routes():
    """FastAPI 应用不应再注册新闻相关路由"""
    import main as app_module

    paths = {r.path for r in app_module.app.routes}
    assert "/api/stock/reports" in paths
    assert "/api/chat/session/{stock_code}" in paths
    assert "/api/health" in paths
    assert not any(p.startswith("/api/dashboard") for p in paths)
    assert not any(p.startswith("/api/history") for p in paths)
    assert not any(p.startswith("/api/trigger") for p in paths)
    assert not any(p.startswith("/api/config") for p in paths)
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /d/openstock/backend
python -m pytest tests/test_openstock_scope.py::test_main_registers_only_stock_and_chat_routes -v
```

Expected: FAIL —— `import main` 抛 ImportError（`ai_news_agent.routers.dashboard` 已删除）。

- [ ] **Step 3: 改造 main.py**

`backend/main.py` 做三处修改：

1. `lifespan` 里删除调度器启停：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭时的初始化与清理"""
    print("[main] 🚀 OpenStock 启动中...")
    init_db()
    print("[main] ✅ 数据库初始化完成")
    yield
    print("[main] 🛑 OpenStock 已关闭")
```

2. 路由注册区删除三个新闻 router 与 config router：

```python
# ── API 路由注册 ──
from routers.stock_api import router as stock_router
from chat_agent.routers.chat import router as chat_router

app.include_router(stock_router)
app.include_router(chat_router)
```

3. FastAPI 元信息与启动端口：

```python
app = FastAPI(
    title="OpenStock",
    description="投研报告与 AI 问答",
    version="1.0.0",
    lifespan=lifespan,
)
```

文件末尾：

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8901)
```

docstring 里的启动命令同步改为 `--port 8901`。

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd /d/openstock/backend
python -m pytest tests/test_openstock_scope.py -v
```

Expected: 4 passed。

- [ ] **Step 5: 补 requirements.txt**

`backend/requirements.txt` 中加入 `requests>=2.31.0`（`stock_agent/analyze.py` 与 `datasources/eastmoney.py` 实际 import 但原清单缺失）。

删除只有新闻用的三项：`feedparser`、`beautifulsoup4`、`lxml`（全仓无 import）。

保留：`fastapi`、`uvicorn[standard]`、`sqlalchemy`、`pymysql`、`openai`、`langgraph`、`pytest`。

**注意不要**加入 `anthropic` / `tavily-python`（新闻专用）。

- [ ] **Step 6: 创建 .env 并首次启动后端**

`.env` 不进 git，必须手工创建。最省事的做法是从 karensagent 拷一份，再改库名：

```bash
cp /d/karensAgent/backend/.env /d/openstock/backend/.env
# 用编辑器把 DATABASE_URL 里的 /karens_agent 改成 /openstock
grep -E '^DATABASE_URL' /d/openstock/backend/.env | sed -E 's|://[^@]*@|://***:***@|'
```

Expected: 输出 `DATABASE_URL=mysql+pymysql://***:***@localhost:3306/openstock`。

其余键（`DEEPSEEK_API_KEY`、`FEISHU_STOCK_WEBHOOK_URL`、`LLM_API_KEY`、`LLM_MODEL_ID`、`LLM_BASE_URL`、`IFIND_AUTH_TOKEN`）沿用拷贝来的值，不改。

然后启动：

```bash
cd /d/openstock/backend
python main.py
```

Expected: 日志显示 `🚀 OpenStock 启动中...` → `✅ 数据库初始化完成` → uvicorn 监听 `0.0.0.0:8901`，**无 ImportError**。

- [ ] **Step 7: 冒烟测试三个端点**

新开一个终端：

```bash
curl -s http://127.0.0.1:8901/api/health
curl -s "http://127.0.0.1:8901/api/stock/reports?limit=3"
curl -s http://127.0.0.1:8901/api/stock/watchlist
```

Expected:
- `/api/health` 返回 `{"status":"ok","ifind":true|false}`
- `/api/stock/reports` 返回包含 3 条报告的 JSON（数据来自 openstock 库，共 75 份）
- `/api/stock/watchlist` 返回 5 只自选股

若 `reports` 返回空 → 检查 `.env` 的 `DATABASE_URL` 是否指向 `openstock` 而不是 `karens_agent`。

- [ ] **Step 8: 停止后端并提交**

```bash
cd /d/openstock
git add backend/main.py backend/requirements.txt backend/tests/test_openstock_scope.py
git commit -m "refactor(backend): 入口只保留股票与问答路由，补齐缺失依赖"
```

---

### Task 4: 前端构建配置改造

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.js`
- Modify: `frontend/index.html`

**Interfaces:**
- Consumes: Task 1 的骨架
- Produces: 一个不含 3D 依赖、dev 端口 5174、代理指向 8901 的前端工程

- [ ] **Step 1: 修改 package.json 去掉 3D 依赖**

删除 `dependencies` 中的三行：`@tresjs/cientos`、`@tresjs/core`、`three`。

保留：`axios`、`echarts`、`marked`、`pinia`、`vue`、`vue-router`。

- [ ] **Step 2: 修改 vite.config.js**

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8901',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'happy-dom',
    include: ['src/**/*.test.js'],
  },
})
```

（删除 `import { templateCompilerOptions } from '@tresjs/core'` 与 `...templateCompilerOptions`；端口 5173→5174；代理 8900→8901）

- [ ] **Step 3: 修改 index.html**

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>OpenStock</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

- [ ] **Step 4: 重装依赖并验证构建**

```bash
cd /d/openstock/frontend
npm install
npm run build
```

Expected: `npm install` 无 3D 包；`npm run build` 成功产出 `dist/`，且**无** `@tresjs` / `three` 相关报错。

- [ ] **Step 5: 提交**

```bash
cd /d/openstock
git add frontend/package.json frontend/package-lock.json frontend/vite.config.js frontend/index.html
git commit -m "build(frontend): 移除 3D 依赖，端口调整为 5174"
```

---

### Task 5: 前端路由扁平化与外壳改造

**Files:**
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/components/TopNav.vue`
- Test: `frontend/src/router/index.test.js`（新建）

**Interfaces:**
- Consumes: Task 4 的构建配置
- Produces: 路由 `/`、`/report/:id`、`/history`、`/settings`；`TopNav` 不再依赖 `store.agents`

- [ ] **Step 1: 写失败测试**

新建 `frontend/src/router/index.test.js`：

```javascript
import { describe, it, expect } from 'vitest'
import router from './index.js'

describe('OpenStock 路由表', () => {
  const paths = () => router.getRoutes().map(r => r.path)

  it('根路径是股票仪表盘', () => {
    const root = router.getRoutes().find(r => r.path === '/')
    expect(root).toBeTruthy()
    expect(root.meta.title).toBe('股票分析 · 仪表盘')
  })

  it('包含扁平化的三个子页面', () => {
    const all = paths()
    expect(all).toContain('/report/:id')
    expect(all).toContain('/history')
    expect(all).toContain('/settings')
  })

  it('不再包含 /agent 前缀的旧路由', () => {
    expect(paths().every(p => !p.startsWith('/agent'))).toBe(true)
  })

  it('报告详情页标记为宽页', () => {
    const report = router.getRoutes().find(r => r.path === '/report/:id')
    expect(report.meta.wide).toBe(true)
  })
})
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /d/openstock/frontend
npx vitest run src/router/index.test.js
```

Expected: FAIL —— 旧路由仍是 `/agent/stock*`，`/` 指向已删除的 OfficeHome。

- [ ] **Step 3: 重写 router/index.js**

```javascript
import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('../views/agent/StockDashboard.vue'),
    meta: { title: '股票分析 · 仪表盘' },
  },
  {
    path: '/report/:id',
    component: () => import('../views/agent/StockReport.vue'),
    meta: { title: '股票分析 · 报告详情', wide: true },
  },
  {
    path: '/history',
    component: () => import('../views/agent/StockHistory.vue'),
    meta: { title: '股票分析 · 历史报告' },
  },
  {
    path: '/settings',
    component: () => import('../views/agent/StockSettings.vue'),
    meta: { title: '股票分析 · 配置管理' },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd /d/openstock/frontend
npx vitest run src/router/index.test.js
```

Expected: 4 passed。

- [ ] **Step 5: 改造 TopNav.vue**

`frontend/src/components/TopNav.vue` 的 `<script setup>` 重写为：

```javascript
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

/* 子导航项（只剩股票一个模块） */
const subNavItems = computed(() => [
  { label: '仪表盘', to: '/' },
  { label: '历史报告', to: '/history' },
  { label: '配置管理', to: '/settings' },
])

/* 动态设置主内容区顶部偏移量 */
const topnavMainHeight = 64
const topnavSubHeight = 44
function updateLayoutOffset() {
  const h = topnavMainHeight + 1 + topnavSubHeight
  document.documentElement.style.setProperty('--topnav-height', h + 'px')
}
onMounted(updateLayoutOffset)
watch(subNavItems, updateLayoutOffset, { immediate: true })
```

模板改动：
- 品牌文字 `Karens Agent` → `OpenStock`
- **删除**中间的 `<nav class="topnav-tabs">` 整块（含 Agent 标签循环与「添加新 Agent」按钮）
- 品牌区 `@click="goHome"` 改为 `<router-link to="/">`，删除 `goHome` / `goAgent` 函数
- 子导航 `<template v-if="...">` 改为无条件渲染

- [ ] **Step 6: 改造 App.vue**

`frontend/src/App.vue` 的 `<script setup>` 改为：

```javascript
import { useRoute } from 'vue-router'
import { useAgentStore } from './stores/agent.js'
import TopNav from './components/TopNav.vue'

const store = useAgentStore()
const route = useRoute()
```

模板中 `<main>` 的 class 绑定删除 `is-fullscreen`（3D 首页已不存在），保留 `is-wide`：

```html
<main class="main-content" :class="{ 'is-wide': route.meta.wide }">
```

`<style scoped>` 中删除 `.main-content.is-fullscreen` 规则。

- [ ] **Step 7: 提交**

```bash
cd /d/openstock
git add frontend/src/router frontend/src/App.vue frontend/src/components/TopNav.vue
git commit -m "refactor(frontend): 路由扁平化，导航简化为单模块"
```

---

### Task 6: 前端数据层裁剪

**Files:**
- Modify: `frontend/src/api/index.js`
- Modify: `frontend/src/stores/agent.js`
- Test: `frontend/src/api/index.test.js`（追加断言）

**Interfaces:**
- Consumes: Task 5 的外壳（TopNav 已不再读 `store.agents`）
- Produces: `api` 模块只导出股票与问答相关函数；`agent` store 只保留 `toast` / `showToast`

- [ ] **Step 1: 追加失败测试**

在 `frontend/src/api/index.test.js` 末尾追加：

```javascript
describe('OpenStock API 边界', () => {
  it('不再导出 AI 新闻相关函数', () => {
    expect(api.getDashboardStats).toBeUndefined()
    expect(api.getHistory).toBeUndefined()
    expect(api.getHistoryDetail).toBeUndefined()
    expect(api.triggerFull).toBeUndefined()
  })

  it('不再导出后端不存在的 triggerStockCollect', () => {
    expect(api.triggerStockCollect).toBeUndefined()
  })

  it('保留股票与问答核心函数', () => {
    for (const fn of [
      'getStockReports', 'getStockReportDetail', 'getStockWatchlist',
      'getWatchlistReports', 'addStockWatchlist', 'deleteStockWatchlist',
      'updateStockWatchlist', 'getStockTrend', 'pushStockReport',
      'fetchSkillReport', 'fetchInvestReport',
      'getChatSession', 'getChatMessages', 'fetchChatAsk', 'healthCheck',
    ]) {
      expect(typeof api[fn]).toBe('function')
    }
  })
})
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /d/openstock/frontend
npx vitest run src/api/index.test.js
```

Expected: FAIL —— news 函数与 `triggerStockCollect` 仍存在。

- [ ] **Step 3: 裁剪 api/index.js**

删除以下四个导出：

```javascript
export const getDashboardStats = () => api.get('/dashboard/stats')
export const getHistory = (limit = 30) => api.get('/history/list', { params: { limit } })
export const getHistoryDetail = (id) => api.get(`/history/detail/${id}`)
export const triggerFull = () => api.post('/trigger/full')
```

删除「仪表盘」「推送历史」「手动触发」三个注释分组（`/* ── 仪表盘 ── */` 等）。

删除：

```javascript
export const triggerStockCollect = (stockCode) =>
  api.post('/stock/collect', { stock_code: stockCode })
```

**保留** `healthCheck`（StockSettings 用它检测 iFinD 连接）。

文件顶部注释块同步改为只描述股票与问答。

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd /d/openstock/frontend
npx vitest run src/api/index.test.js
```

Expected: 6 passed（原有 3 条 SSE 测试 + 新增 3 条）。

- [ ] **Step 5: 精简 stores/agent.js**

重写为只保留 toast：

```javascript
import { defineStore } from 'pinia'

/* 全局轻提示 store —— 拆分后只承担 toast 职责 */
export const useAgentStore = defineStore('agent', {
  state: () => ({
    toast: null,
  }),

  actions: {
    showToast(message, duration = 3000) {
      this.toast = message
      setTimeout(() => { this.toast = null }, duration)
    },
  },
})
```

删除：`import * as api`、`agents` 注册表、`stats`、`loading`、`pushHistory`、`fetchStats`、`fetchHistory`、`triggerFull`。

- [ ] **Step 6: 验证没有遗漏的调用方**

```bash
cd /d/openstock/frontend/src
grep -rn "store.agents\|store.stats\|store.pushHistory\|fetchStats\|fetchHistory\|triggerFull\|getDashboardStats\|triggerStockCollect" --include=*.vue --include=*.js .
```

Expected: 只能命中 `api/index.test.js` 里的断言行（`toBeUndefined`），业务代码**零命中**。

- [ ] **Step 7: 提交**

```bash
cd /d/openstock
git add frontend/src/api frontend/src/stores/agent.js
git commit -m "refactor(frontend): API 与 store 收敛到股票与问答范围"
```

---

### Task 7: 前端测试全绿

**Files:**
- Modify: 视失败情况而定，可能涉及 `frontend/src/**/*.test.js`

**Interfaces:**
- Consumes: Task 4–6 的全部改动
- Produces: `npm test` 全绿的前端工程

- [ ] **Step 1: 跑完整前端测试**

```bash
cd /d/openstock/frontend
npm test 2>&1 | tail -40
```

Expected: 大部分通过。预期可能失败的只有与已删文件相关的用例。

- [ ] **Step 2: 修复失败用例**

常见原因与处理：
- 测试文件 import 了已删除的组件 → 删除该测试文件（对应组件已不存在）
- 断言 `store.agents` 内容 → 改为断言 `showToast` 行为
- 路由相关断言仍用 `/agent/stock` → 按 Task 5 的新路径修正

**不要**为了让测试通过而恢复已删除的业务代码。

- [ ] **Step 3: 确认全绿**

```bash
cd /d/openstock/frontend
npm test
```

Expected: `Test Files  N passed (N)` / `Tests  M passed (M)`，零失败。

- [ ] **Step 4: 提交（仅当有改动）**

```bash
cd /d/openstock
git add -A frontend/src
git commit -m "test(frontend): 清理随模块移除而失效的用例"
```

---

### Task 8: 端到端验收

**Files:** 无（纯验证，发现问题则回到对应任务修复）

**Interfaces:**
- Consumes: Task 1–7 的全部产出
- Produces: 通过设计文档「十一、验收标准」全部 13 条的确认

- [ ] **Step 1: 启动后端**

```bash
cd /d/openstock/backend
python main.py
```

Expected: 监听 8901，无报错。

- [ ] **Step 2: 启动前端**

新终端：

```bash
cd /d/openstock/frontend
npm run dev
```

Expected: 监听 5174，无编译错误。

- [ ] **Step 3: 逐条核对验收标准**

| # | 验收项 | 验证方式 | 通过 |
|---|---|---|---|
| 1 | 后端 8901 启动无 ImportError | Step 1 日志 | ☐ |
| 2 | 前端 5174 启动成功 | Step 2 日志 | ☐ |
| 3 | 打开 `http://localhost:5174` 直接是股票仪表盘，无 3D | 浏览器 | ☐ |
| 4 | 仪表盘显示 5 只自选股与最新报告摘要 | 浏览器 | ☐ |
| 5 | `/history` 列出历史报告，能打开旧报告 | 浏览器 | ☐ |
| 6 | `/report/:id` 渲染 9 个模块卡片、评分仪表、风险预警 | 浏览器 | ☐ |
| 7 | 问答面板收拢态/展开态切换正常 | 浏览器 | ☐ |
| 8 | 能提问并收到流式回答 | 浏览器 | ☐ |
| 9 | `/settings` 显示自选股、10 维度、iFinD 状态 | 浏览器 | ☐ |
| 10 | 顶部显示 OpenStock，子导航三项可切换 | 浏览器 | ☐ |
| 11 | 后端 `python -m pytest tests/` 全绿 | 命令行 | ☐ |
| 12 | 前端 `npm test` 全绿 | 命令行 | ☐ |
| 13 | `D:\karensAgent` 切回去仍能正常启动 | 命令行 | ☐ |

- [ ] **Step 4: 跑后端完整测试**

```bash
cd /d/openstock/backend
python -m pytest tests/ -v 2>&1 | tail -30
```

Expected: 全部通过。失败项逐个定位修复。

- [ ] **Step 5: 确认 karensagent 未受影响**

```bash
cd /d/karensAgent
git status -sb
git log --oneline -1
```

Expected: 工作区干净，HEAD 仍是 `b8be0ec`（或更新），**没有任何来自本次拆分的改动**。

---

### Task 9: 推送到 openstock 仓库

**Files:**
- Modify: `.git/config`（remote URL）

**Interfaces:**
- Consumes: Task 1–8 的全部产出
- Produces: `https://github.com/WL-karensouza/openstock` 上完整的 OpenStock 代码与历史

- [ ] **Step 1: 切换 remote**

```bash
cd /d/openstock
git remote set-url origin https://github.com/WL-karensouza/openstock.git
git remote -v
```

Expected: `origin` 指向 `openstock.git`。

- [ ] **Step 2: 确认即将推送的提交列表**

```bash
cd /d/openstock
git log --oneline -15
```

Expected: 看到 karensagent 的完整历史 + Task 1–7 的新提交。

- [ ] **Step 3: 强推覆盖 GitHub 的 initial commit**

```bash
cd /d/openstock
export HTTPS_PROXY=http://127.0.0.1:17891 HTTP_PROXY=http://127.0.0.1:17891
git push -f origin main
```

Expected: 推送成功。GitHub 上原有的 `Initial commit`（只有 LICENSE + README）被历史覆盖。

> ⚠️ 这是 force push。已确认该仓库仅有 GitHub 自动生成的 initial commit，可安全覆盖。

- [ ] **Step 4: 验证远程状态**

```bash
cd /d/openstock
export HTTPS_PROXY=http://127.0.0.1:17891 HTTP_PROXY=http://127.0.0.1:17891
git status -sb
gh api repos/WL-karensouza/openstock/commits --jq '.[0:3][] | "\(.sha[0:7])  \(.commit.message | split("\n")[0])"'
```

Expected:
- `git status` 显示 `## main...origin/main`（无 ahead/behind）
- 远程最新提交与本地 HEAD 一致
- 能看到股票模块的完整历史

- [ ] **Step 5: 完成**

向用户汇报：
- 仓库地址
- 本地路径 `D:\openstock`
- 启动方式：后端 `cd D:\openstock\backend && python main.py`（8901），前端 `cd D:\openstock\frontend && npm run dev`（5174）

---

## 附：实施时的已知风险

| 风险 | 触发条件 | 应对 |
|---|---|---|
| `.env` 未创建 | 首次启动后端 | 从 karensagent 复制 `backend/.env`，把 `DATABASE_URL` 的库名改成 `openstock` |
| iFinD 数据拉不到 | 启动后 `/api/health` 返回 `ifind: false` | 确认 `~/.claude/skills/ifind-finance-data/` 存在且 `IFIND_AUTH_TOKEN` 有效 |
| 端口被占 | 5174 / 8901 已有进程 | `netstat -ano \| findstr :8901` 查占用进程 |
| 强推被拒 | 远程有额外提交 | 先 `git fetch` 确认，再决定是否 force |

## 附二：两处有意保持原样（与设计文档 6.2 的偏差）

设计文档 6.2 提出改造 `config.py`（收编 `DEEPSEEK_API_KEY`、删除新闻专用键），以及处理 `stock_agent/analyze.py` 的 import 期副作用。**实施时这两处均保持原样不动**，理由：

1. `analyze.py` 在 **import 期**读取 `.env` 并写入 `os.environ`；若 `config.py` 也读一遍，会形成两份配置来源，语义反而更乱
2. 改造它需要动分析主链路，风险与收益不成比例——删除几个无用键对「跑通」零贡献
3. 保持原样能保证 `stock_agent` 的行为与 karensagent **完全一致**，一旦新站出问题，可立刻判断是拆分引入的还是原有缺陷

若将来要整理配置，单独开任务做，不在本次拆分范围内。
