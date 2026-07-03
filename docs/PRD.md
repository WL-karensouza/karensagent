# 产品需求文档：Karens Agent 多智能体平台

**作者**：王磊
**日期**：2026-06-30（最后修订：2026-07-02）
**状态**：V1.0 运行中（持续迭代）
**版本**：1.1.0

---

## 1. 执行摘要

Karens Agent 是一个**个人多智能体（Multi-Agent）运营平台**，以插件化方式集成多个 AI Agent，各自承担独立的信息采集、分析、推送任务。首个 Agent（GitHub 热榜追踪）已上线运行，每日 09:00 自动抓取 GitHub Trending 和 AI 前沿资讯，经关键词过滤后推送到飞书群。平台采用无登录直接访问设计，前端以 Claude.com 温暖极简风格呈现，后端通过 FastAPI + APScheduler 驱动定时任务。

## 2. 背景与上下文

### 2.1 问题空间

- 开发者需要持续关注 GitHub 热门开源项目，但手动浏览 trending 页面耗时且容易遗漏
- AI 领域论文和资讯分散在多个平台（Hacker News、ArXiv、HuggingFace），碎片化严重
- 不同信息来源需要不同 Agent 独立处理，传统单体应用难以灵活扩展
- 需要一个轻量、无感知的后台系统，定时采集、过滤、推送，不打扰日常工作流

### 2.2 已有成果

**GitHub 热榜追踪 Agent（已完成）：**
- 可进行AI关键词驱动资讯布尔过滤
- 3 大数据源：Hacker News + ArXiv CS.AI + HuggingFace Daily Papers
- GitHub 官方 daily/weekly/monthly trending 页面直接解析，排名与官网一致
- 飞书交互式卡片推送，结构化呈现榜单和资讯
- 前端管理面板：仪表盘、内容预览、推送历史、关键词配置、Webhook 配置

## 3. 目标与成功指标

### 3.1 目标

 | # | 目标 | 类型 |
|---|------|------|
| G1 | 构建可扩展的多 Agent 平台架构，新增 Agent 成本低于 200 行代码 | 架构 |
| G2 | GitHub Agent 每日稳定推送，故障率 < 5% | 可靠性 |
| G3 | 平台操作直观无学习成本，Agent 管理入口统一 | 体验 |
| G4 | 支持至少 3 个不同领域的 Agent 并行运行 | 规模 |

### 3.2 非目标

| # | 内容 | 原因 |
|---|------|------|
| N1 | 用户登录/注册/权限系统 | 当前为个人使用，暂不需要多用户体系 |
| N2 | 移动端原生 App | Web 端响应式已满足需求 |
| N3 | Agent 间协同/链式调用 | 每个 Agent 独立运行，解耦优先 |
| N4 | 商业级 SaaS 多租户 | 个人平台，非 SaaS 定位 |

### 3.3 成功指标

| 指标 | 当前值 | 目标值 | 测量方式 |
|------|--------|--------|----------|
| 每日推送成功率 | 手动测试通过 | ≥ 95% | 推送历史 status 字段统计 |
| 新增 Agent 开发耗时 | — | ≤ 4 小时/个 | 实际开发时间记录 |
| 前端页面加载时间 | ~190ms build | 首屏 ≤ 2s | Lighthouse / Chrome DevTools |
| 数据源可用性 | 4/4 源正常 | ≥ 2/4 源可用 | 抓取日志监控 |

## 4. 目标用户

| 角色 | 描述 | 场景 |
|------|------|------|
| **个人开发者**（主要用户） | 需要自动化信息聚合的技术人员 | 每天早上在飞书群收到 GitHub + AI 日报，无需手动浏览多个网站 |
| **Agent 扩展者** | 希望添加新 Agent 的开发者 | 参照 GitHub Agent 模板，快速接入新数据源和推送逻辑 |

## 5. 用户故事与需求

### P0 — 必须拥有（已完成）

| # | 用户故事 | 验收标准 | 状态 |
|---|----------|----------|------|
| US1 | 作为用户，我每天 09:00 自动收到飞书推送，包含 GitHub 周榜/月榜和 AI 资讯，无需任何手动操作 | 定时任务触发→抓取→过滤→推送全流程自动化；卡片格式正确，超链接可点击 | ✅ |
| US2 | 作为用户，我可以在仪表盘上查看今日抓取了多少仓库和资讯 | 统计卡片实时展示 today_repos / week_news / last_push（`week_unique_repos` 为预留字段，当前显示 "—"） | ✅ |
| US3 | 作为用户，我可以随时手动点击"立即抓取"来获取最新数据，点击"一键全流程"完成抓取+推送。**操作完成后前端轮询返回具体结果（成功/部分失败/全部失败），而非泛泛的"操作成功"** | POST /api/trigger/full 返回 task_id；前端 3s 间隔轮询 GET /api/trigger/result/{task_id} 获取执行结果；toast 显示具体错误信息（如 "HN、ArXiv 抓取失败，已用已有数据推送"）| ✅ |
| US4 | 作为用户，推送的周榜和月榜排名必须与 GitHub Trending 页面完全一致 | 直接从 `?since=weekly` 和 `?since=monthly` 页面解析，不做二次聚合 | ✅ |
| US5 | 作为用户，我可以添加/删除/启停关键词，控制哪些 AI 资讯被推送 | 关键词 CRUD 接口正常；AI 资讯布尔匹配正确 | ✅ |

### P1 — 应该拥有（当前在规划中）

| # | 用户故事 | 验收标准 | 状态 |
|---|----------|----------|------|
| US6 | 作为用户，我可以将飞书 Webhook URL 从前端界面配置进去，无需改 .env 文件 | 前端输入框 → PUT /api/config/webhook → .env 文件更新 → 即时生效 | ✅ |
| US7 | 作为用户，我可以按日期回溯查看历史抓取的内容 | 日期选择器 → GET /api/preview/trends?fetch_date=YYYY-MM-DD | ✅ |
| US8 | 作为用户，我可以在首页看到所有 Agent 的运行状态（运行中/已停止） | Home 页 Agent 卡片网格，每个 Agent 显示状态点和关键统计 | ✅ |
| US9 | 作为用户，我可以在顶部导航栏一键切换不同 Agent | 点击 Agent 标签切换路由，页面平滑过渡动画 180ms | ✅ |
| US10 | 作为用户，我可以新增一个股票分析 Agent，它有自己的数据源和推送逻辑 | Stock Agent 独立路由、抓取器、配置项 | 🚧 |

### P2 — 锦上添花（未来迭代）

| # | 用户故事 | 验收标准 | 状态 |
|---|----------|----------|------|
| US11 | 作为用户，我可以在前端直接配置推送时间（如改为 08:30） | Settings 页时间选择器 → 写入 .env/db → 调度器动态更新 | 📋 |
| US12 | 作为用户，当数据源异常时我能收到告警通知 | **抓取全部失败时自动向飞书推送红色告警卡片（`send_error_notification`）**；定时任务推送失败时同样飞书告警 | ✅ |
| US13 | 作为用户，我可以查看每个 Agent 近 30 天的推送趋势图 | Dashboard 嵌入简单的推送数量趋势折线图 | 📋 |
| US14 | 作为用户，我可以一键导出周报为 Markdown 文件 | 点击导出按钮 → 下载 .md 文件 | 📋 |
| US15 | 作为用户，我可以通过 Claude API 自动生成每日资讯的 AI 摘要 | 接入 Anthropic API，对推送的每条资讯生成一句话中文摘要 | 📋 |

## 6. 解决方案概述

### 6.1 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Karens Agent 平台                      │
├─────────────────────────────────────────────────────────┤
│  前端 (Vue3 + Vite + Pinia)                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │  Home    │ │  GitHub  │ │  Stock   │ │ Settings │   │
│  │ 控制台   │ │  Agent   │ │  Agent   │ │ 平台设置  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                      │ Axios / REST API                   │
├──────────────────────┼──────────────────────────────────┤
│  后端 (FastAPI :8900) │                                   │
│  ┌───────────────────┴──────────────────────────────┐   │
│  │  Routers: dashboard / preview / history           │   │
│  │           trigger / config                        │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌────────────┐ ┌──────────┐ ┌──────────────────────┐   │
│  │ Scheduler  │ │ Fetchers │ │ Filters + Formatters │   │
│  │ APScheduler│ │ github   │ │ keyword / feishu     │   │
│  │ 每天 09:00 │ │ ai_news  │ │ markdown             │   │
│  └────────────┘ └──────────┘ └──────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Database: SQLite (dev) / MySQL (prod)            │   │
│  │  Tables: daily_trends, ai_news, push_history,     │   │
│  │          keywords                                 │   │
│  └──────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  外部服务                                                │
│  GitHub Trending · Hacker News API · ArXiv RSS          │
│  HuggingFace Daily Papers · 飞书 Webhook                │
└─────────────────────────────────────────────────────────┘
```

### 6.2 关键技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 前端路由模式 | Hash Router (`createWebHashHistory`) | 无后端配置即可部署，刷新不 404 |
| 状态管理 | Pinia (单 Store) | 当前规模小，单 Store 足够；后续可按 Agent 拆 Store |
| 数据库双模式 | SQLite dev / MySQL prod | 本地零配置启动，生产无缝切换 |
| GitHub 数据获取 | 直接解析 Trending HTML 页面 | 无官方 API，BeautifulSoup 解析是最可靠方式 |
| 资讯过滤 | 纯关键词布尔匹配 | 简单、可解释、可热更新，无需 NLP 模型 |
| 定时任务 | APScheduler (BackgroundScheduler) | FastAPI 原生集成，无需额外 Celery/Redis |
| 前端构建 | Vite 8 + Rolldown | 当前最新，构建速度 190ms |

### 6.3 Agent 扩展规范

新增一个 Agent 需要以下 4 个文件：

```
backend/
  fetchers/<agent>_data.py    # 数据抓取（可选）
  routers/<agent>_api.py      # Agent 专属 API（可选）
frontend/
  src/views/agent/<Agent>Dashboard.vue  # Agent 主页
  src/views/agent/<Agent>Settings.vue   # Agent 配置页
```

并在以下位置注册：
- `frontend/src/router/index.js` — 添加路由
- `frontend/src/stores/agent.js` — 注册 agents 数组
- `backend/main.py` — 可选：注册新 router

### 6.4 数据流

```
定时/手动触发
    │
    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ fetch_all_    │     │ fetch_all_   │     │ (future)     │
│ trends()      │     │ news()       │     │ stock_data() │
│ daily/weekly  │     │ HN/ArXiv/PwC │     │              │
│ /monthly      │     │              │     │              │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌──────────────────────────────────────────────────────┐
│              save_daily_trends / save_ai_news          │
│              SQLite / MySQL (批量去重 + IntegrityError 兜底) │
└──────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│ get_trends_  │     │ get_ai_news()│
│ by_source()  │     │              │
│ weekly/month │     │              │
└──────┬───────┘     └──────┬───────┘
       │                    │
       ▼                    ▼
┌──────────────┐     ┌──────────────┐
│ filter_repos │     │ filter_news  │
│ (纯 stars    │     │ (关键词布尔  │
│  排名 Top N) │     │  匹配 Top N) │
└──────┬───────┘     └──────┬───────┘
       │                    │
       └────────┬───────────┘
                ▼
     ┌──────────────────┐
     │ build_feishu_card│
     │ push_report()    │
     └────────┬─────────┘
              ▼
     ┌──────────────────┐
     │ 飞书 Webhook POST │
     │ save_push_history │
     └──────────────────┘
```

#### 手动触发异步流程（v1.1.0 新增）

```
POST /api/trigger/full
    │
    ├─→ 立即返回 {task_id}（~50ms）
    │
    └─→ 后台线程 _run_full(task_id)
          │
          ├─ _run_fetch(task_id)
          │    ├─ try GitHub    → 成功: sources.github = {ok, count}
          │    ├─ try HN        → 失败: sources.hackernews = {ok:false, error}
          │    ├─ try ArXiv     → 失败: sources.arxiv = {ok:false, error}
          │    └─ try PwC       → 成功: sources.paperswithcode = {ok, count}
          │    └─ 汇总: all_failed=(4/4失败)?  message=具体描述
          │
          ├─ if all_failed:
          │    status="done" → send_error_notification(飞书红色卡片) → return
          │
          └─ else:
               └─ _run_push(task_id)
                    ├─ 读 DB → 过滤 → push_report → 飞书卡片
                    ├─ 成功: push.ok=true, message="推送成功"
                    └─ 失败: push.ok=false, message="飞书推送失败..."
               └─ status="done", message = push.ok ? fetch.message : push.message

前端轮询:
  GET /api/trigger/result/{task_id}  (每 3s, 最多 20 次)
    → status="done" → toast(message) → fetchStats
    → 60s 超时 → toast("操作超时...")
```

## 7. 技术栈明细

### 7.1 后端

| 组件 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI | ≥ 0.115.0 |
| ASGI 服务器 | Uvicorn | ≥ 0.34.0 |
| ORM | SQLAlchemy | ≥ 2.0.0 |
| MySQL 驱动 | PyMySQL | ≥ 1.1.0 |
| HTTP 客户端 | httpx | ≥ 0.28.0 |
| 定时任务 | APScheduler | ≥ 3.10.0 |
| RSS 解析 | feedparser | ≥ 6.0.0 |
| HTML 解析 | BeautifulSoup4 + lxml | ≥ 4.12.0 / ≥ 5.0.0 |
| 测试 | pytest | ≥ 8.0.0 |

### 7.2 前端

| 组件 | 技术 | 版本 |
|------|------|------|
| UI 框架 | Vue 3 | ^3.5.38 |
| 构建工具 | Vite (Rolldown) | ^8.1.0 |
| 状态管理 | Pinia | ^3.0.4 |
| 路由 | Vue Router (Hash) | ^4.6.4 |
| HTTP 客户端 | Axios | ^1.18.1 |
| 字体 | Inter (Google Fonts) | — |

### 7.3 设计系统

| 属性 | 值 |
|------|-----|
| 背景色 | `#F1EFEA` (page) / `#FFFFFF` (card) |
| 强调色 | `#D97706` (amber-600) |
| 文字色 | `#2D2A26` (primary) / `#78716C` (secondary) |
| 圆角 | 8px / 12px / 20px / 24px |
| 字体 | Inter, -apple-system, sans-serif |
| 卡片阴影 | `0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03)` |
| 动效时长 | 150–300ms (ease) |

## 8. API 接口清单

### 8.1 仪表盘
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dashboard/stats` | 获取仪表盘统计 |
| GET | `/api/health` | 健康检查 |

### 8.2 内容预览
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/preview/trends?fetch_date=&source=&limit=` | 按日期查看 Trend |
| GET | `/api/preview/news?fetch_date=&limit=` | 按日期查看资讯 |
| GET | `/api/preview/dates` | 获取有数据的日期列表 |

### 8.3 推送历史
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/history/list?limit=` | 推送历史列表 |
| GET | `/api/history/detail/{push_id}` | 推送历史详情 |

### 8.4 手动触发

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/trigger/fetch` | 立即抓取（返回 task_id，后台执行） |
| POST | `/api/trigger/push` | 立即推送（返回 task_id，后台执行） |
| POST | `/api/trigger/full` | 一键全流程（返回 task_id，后台执行） |
| GET | `/api/trigger/result/{task_id}` | **v1.1 新增** 查询后台任务执行结果，返回 fetch/push 各源状态和最终 message |

**触发端点返回值变化（v1.1）：**

```json
// 旧版（v1.0）
{"code": 0, "message": "已触发后台全流程"}

// 新版（v1.1）
{"code": 0, "task_id": "887bf80b", "message": "已触发后台全流程"}
```

**轮询结果端点返回值：**

```json
// 任务进行中
{"code": 0, "data": {"status": "running", "fetch": null, "push": null, "message": ""}}

// 部分失败（继续推送）
{"code": 0, "data": {
  "status": "done",
  "fetch": {
    "ok": false, "all_failed": false,
    "sources": {
      "github": {"ok": true, "count": 61},
      "hackernews": {"ok": false, "error": "Connection refused"},
      "arxiv": {"ok": true, "count": 10},
      "paperswithcode": {"ok": true, "count": 10}
    },
    "message": "HN 抓取失败，已用已有数据推送"
  },
  "push": {"ok": true, "repo_count": 40, "news_count": 5, "message": "推送成功"},
  "message": "HN 抓取失败，已用已有数据推送"
}}

// 全部失败（阻止推送 + 飞书告警，push 阶段未执行故为 null）
{"code": 0, "data": {
  "status": "done",
  "fetch": {"ok": false, "all_failed": true, "message": "所有数据源抓取失败：GitHub、HN、ArXiv、PwC"},
  "push": null,
  "message": "所有数据源抓取失败：GitHub、HN、ArXiv、PwC"
}}
```

### 8.5 配置管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config/keywords` | 关键词列表 |
| POST | `/api/config/keywords` | 添加关键词 |
| PUT | `/api/config/keywords/{keyword}` | 启用/禁用关键词 |
| DELETE | `/api/config/keywords/{keyword}` | 删除关键词 |
| GET | `/api/config/webhook` | 获取飞书 Webhook |
| PUT | `/api/config/webhook` | 更新飞书 Webhook |

## 9. 数据库模型

### 9.1 daily_trends（GitHub Trending 抓取数据）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| repo_name | VARCHAR(255) | 仓库全名 |
| repo_url | VARCHAR(512) | 仓库链接 |
| description | TEXT | 描述 |
| language | VARCHAR(50) | 编程语言 |
| stars_today | INTEGER | 期间获星数（daily/weekly/monthly） |
| total_stars | INTEGER | 总星数 |
| rank | INTEGER | GitHub 页面原始排名 |
| source | VARCHAR(20) | daily / weekly / monthly |
| fetch_date | DATE | 抓取日期 |

唯一约束：`(repo_name, fetch_date, source)`

### 9.2 ai_news（AI 资讯）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| title | VARCHAR(500) | 标题 |
| url | VARCHAR(500) | 链接 |
| source | VARCHAR(50) | hackernews / arxiv / paperswithcode |
| score | INTEGER | 热度分数 |
| summary | TEXT | 摘要 |
| fetch_date | DATE | 抓取日期 |
| is_pushed | INTEGER | 是否已推送 1/0（默认 0） |

唯一约束：`(url, fetch_date)`

### 9.3 push_history（推送历史）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| push_time | DATETIME | 推送时间（server_default=now） |
| platform | VARCHAR(20) | feishu / wecom |
| content_type | VARCHAR(20) | daily / weekly / monthly |
| content | TEXT | 完整推送内容 JSON |
| repo_count | INTEGER | 仓库数 |
| news_count | INTEGER | 资讯数 |
| status | VARCHAR(20) | sent / failed |

### 9.4 keywords（关键词配置）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| keyword | VARCHAR(100) UNIQUE | 关键词 |
| score | INTEGER | 权重（模型 default=5，种子数据固定为 0，当前未启用） |
| enabled | INTEGER | 是否启用 1/0 |

## 10. 部署信息

| 项目 | 值 |
|------|-----|
| 项目根目录 | `D:\karensAgent\` |
| 后端启动 | `uvicorn main:app --host 0.0.0.0 --port 8900 --reload` |
| 前端开发 | `npm run dev` (Vite HMR) |
| 前端构建 | `npm run build` → `dist/` |
| 前后端一体部署 | FastAPI 直接 serve `frontend/dist/` 静态文件 |
| 环境变量 | `.env` 文件（DATABASE_URL, FEISHU_WEBHOOK_URL, PUSH_TIME 等） |

## 11. 路线图

### Phase 1：基础可用（✅ 已完成）
- GitHub Trending 每日抓取 + 飞书推送
- AI 资讯聚合（HN + ArXiv + PwC）
- 前端管理面板（仪表盘、预览、历史、配置）
- 多 Agent 架构骨架（Home 页 Agent 网格 + 顶部标签导航）

### Phase 2：Agent 扩展（🚧 当前）
- [ ] 股票分析 Agent 实现（数据源 + 推送逻辑）
- [ ] Agent 配置独立化（每个 Agent 独立 settings 页面）
- [ ] 前端暗色模式支持
- [x] **异常告警基础能力（v1.1）：抓取全失败 / 推送失败 → 飞书红色告警卡片**

### Phase 3：智能化（📋 规划中）
- [ ] Claude API 集成（AI 摘要生成）
- [ ] 推送趋势可视化图表
- [ ] 第三方 Agent 模板（Webhook / RSS 通用模板）

### Phase 4：体验优化（📋 远期）
- [ ] PWA 支持（离线缓存 + 桌面快捷方式）
- [ ] i18n 国际化
- [ ] Agent 市场（社区贡献 Agent 模板）

## 12. 开放问题

| # | 问题 | 负责人 | 截止 |
|---|------|--------|------|
| Q1 | 股票分析 Agent 的具体数据源选什么？（东方财富 API / tushare / akshare？） | 王磊 | 待定 |
| Q2 | 是否需要 Agent 运行日志持久化到数据库？ | 王磊 | 待定 |
| Q3 | ~~告警推送用飞书还是其他渠道？~~ → **已确定：通过 `send_error_notification()` 向飞书推送红色卡片告警** | 王磊 | ✅ 已解决 |
| Q4 | Claude API 摘要功能是否需要等 API 额度充足后再开启？ | 王磊 | 待定 |

## 13. 附录

### A. 项目文件结构

```
karensAgent/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 全局配置
│   ├── database.py          # SQLAlchemy 引擎 + CRUD
│   ├── models.py            # ORM 模型定义
│   ├── scheduler.py         # APScheduler 定时任务
│   ├── notifier.py          # 飞书推送
│   ├── requirements.txt     # Python 依赖
│   ├── .env                 # 环境变量（不入 git）
│   ├── fetchers/
│   │   ├── github.py        # GitHub Trending 抓取
│   │   └── ai_news.py       # AI 资讯聚合（HN/ArXiv/PwC）
│   ├── filters/
│   │   └── keyword.py       # 关键词布尔过滤器
│   ├── formatters/
│   │   ├── feishu.py        # 飞书卡片 JSON 构建
│   │   └── markdown.py      # Markdown 报告生成
│   ├── routers/
│   │   ├── dashboard.py     # 仪表盘 API
│   │   ├── preview.py       # 内容预览 API
│   │   ├── history.py       # 推送历史 API
│   │   ├── trigger.py       # 手动触发 API
│   │   └── config_api.py    # 配置管理 API
│   └── tests/
│       └── test_core.py     # 核心功能测试
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── style.css         # 全局样式（设计系统）
│       ├── api/
│       │   └── index.js      # Axios 封装 + API 函数
│       ├── router/
│       │   └── index.js      # Hash Router 路由定义
│       ├── stores/
│       │   └── agent.js      # Pinia 全局 Store
│       ├── components/
│       │   ├── TopNav.vue              # 顶部导航栏（含二级子导航）
│       │   ├── AnimatedClock.vue       # 仪表盘时钟 SVG 动画组件
│       │   ├── DatePicker.vue          # 日期选择器（B1 极简风）
│       │   └── SelectPicker.vue        # 通用下拉选择器
│       └── views/
│           ├── Home.vue              # 首页 Agent 控制台
│           ├── Settings.vue          # 平台全局设置
│           └── agent/
│               ├── GithubDashboard.vue  # GitHub 仪表盘
│               ├── GithubPreview.vue    # GitHub 内容预览
│               ├── GithubHistory.vue    # GitHub 推送历史
│               ├── GithubSettings.vue   # GitHub 配置管理
│               └── StockPlaceholder.vue # 股票 Agent 占位
└── docs/
    └── PRD.md              # 本文档
```

### B. 飞书推送卡片示例结构

```
┌────────────────────────────────────┐
│  Karens Agent 日报 | 2026-06-30    │  ← 蓝色标题栏
├────────────────────────────────────┤
│  🔥 本周 GitHub 热榜 Top 10        │
│  1. owner/repo — ⭐ 17,483         │
│     > 项目描述（100字以内）          │
│  ...                               │
├────────────────────────────────────┤
│  🏆 本月 GitHub 热榜精选            │
│  1. owner/repo — ⭐ 26,117         │
│  ...                               │
├────────────────────────────────────┤
│  📚 AI 前沿速递                     │
│  1. [HN] Article Title             │
│  2. [ArXiv] Paper Title            │
│  3. [PwC] Paper Title              │
├────────────────────────────────────┤
│  Karens Agent 自动生成 · 每天 9:00  │  ← 底部注释
└────────────────────────────────────┘
```

### C. 默认关键词列表

```
agent, llm, mcp, claude, langgraph, autogen, crewai,
tool-use, function-calling, multi-agent, rag, workflow,
openai, skill, chain-of-thought, reasoning, fine-tuning,
alignment, transformer, deepseek, gemini, llama,
embedding, retrieval
```

---

## 14. 变更记录

### v1.1.0（2026-07-02）—— Trigger 全链路错误报告 + 界面优化

#### 背景
用户点击"立即抓取新数据并推送"后，后台 daemon 线程中的任何错误都被静默吞掉，前端永远显示"操作成功"。实际后端可能因网络不通、数据重复等原因失败，用户完全无感知。

#### 需求分析
经过全链路逐环节排查，梳理出 4 个数据源（GitHub / HN / ArXiv / PwC）、入库、飞书推送各阶段的 13 种潜在失败原因。核心决策：
- **部分失败**（如 HN 超时但 GitHub 成功）：继续推送，toast 标注失败源
- **全部失败**（4 源全挂）：阻止推送 + toast 报错 + 飞书红色告警卡片
- **推送失败**：toast 报错（飞书挂了无法再通知飞书）

#### 后端改动

| 文件 | 改动 | 原因 |
|------|------|------|
| `fetchers/github.py` | `fetch_trending()` 网络错误从 `return []` 改为 `raise` | 让调用层感知错误，而非静默返回空 |
| `fetchers/ai_news.py` | `fetch_hackernews/arxiv/paperswithcode` 3 处同上 | 同上 |
| `database.py` | `save_ai_news` / `save_daily_trends`：批量查询替代 N 次逐条查询 + 内存去重 + `IntegrityError` 兜底逐条插入 | 解决 `autoflush=False` 导致同批次重复检测失效 |
| `routers/trigger.py` | **完整重写**：`_task_results` 内存任务存储 + `_create_task` + `_clean_old_tasks`；`_run_fetch` 4 源独立调用 + 逐源错误收集；`_run_push` try/except 异常包装；`_run_full` 根据 `all_failed` 分支决策；新增 `GET /api/trigger/result/{task_id}` 轮询端点 | 核心需求 |
| `notifier.py` | 新增 `send_error_notification(title, detail)`，构建红色飞书告警卡片 | 异常推送至飞书 |
| `scheduler.py` | `daily_fetch_and_push()` 对齐逐源错误收集 + 飞书告警 + 全失败阻止推送 | 定时任务与手动触发行为一致 |
| `tests/test_core.py` | 新增 6 个测试：错误传播 ×4、task_id 返回、404 查询 | TDD |

#### 前端改动

| 文件 | 改动 | 原因 |
|------|------|------|
| `api/index.js` | 新增 `getTaskResult(taskId)` | 轮询查询 |
| `stores/agent.js` | `triggerAction()` 改为轮询模式（3s × 20 次 = 60s 上限），toast 显示具体错误信息 | 替代原来的"操作成功" |

#### 界面优化（上次会话遗留）
- `AnimatedClock.vue`：仪表盘时钟 SVG 动画组件（从 Clock.html 提取）
- `DatePicker.vue` + `SelectPicker.vue`：B1 极简风日期/下拉选择器
- `TopNav.vue`：AgentSubNav 二级导航合并入一级导航栏
- `GithubDashboard.vue`：删除 `<h1>`，描述文字居中

#### 架构影响
- 触发端点从同步假异步改为真正的"提交-轮询"模式
- Fetcher 层网络错误不再吞掉，调用层统一处理
- 数据库写入层幂等安全（自动去重 + 异常兜底）

#### 已验证场景
| 场景 | toast | 飞书 |
|------|-------|------|
| 全部成功 | "所有数据源抓取成功" | 正常推送卡片 |
| GitHub 失败其余成功 | "GitHub 抓取失败，已用已有数据推送" | 正常推送卡片 |
| HN+ArXiv 失败 | "HN、ArXiv 抓取失败，已用已有数据推送" | 正常推送卡片 |
| 4 源全挂 | "所有数据源抓取失败：…" | 红色告警卡片 |
| 飞书推送失败 | "飞书推送失败，请检查 Webhook 配置" | — |
| 60s 无结果 | "操作超时，请稍后刷新查看结果" | — |

---

*文档版本：1.1.0 | 最后更新：2026-07-02 | 下次评审：Phase 2 启动前*
