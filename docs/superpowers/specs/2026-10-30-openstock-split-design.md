# OpenStock 独立站拆分设计

> 状态：设计已定，**尚未实施**（用户明确要求先不迁移）
> 日期：2026-10-30
> 源项目：`D:\karensAgent`（GitHub: `WL-karensouza/karensagent`）
> 目标仓库：`https://github.com/WL-karensouza/openstock.git`（私有，已有 initial commit）

---

## 一、背景与目标

karensAgent 目前是一个「3D 办公室首页 + 两大 Agent（AI 前沿 / 股票分析）」的单体应用。前端是一个 Vue3 SPA，后端是一个 FastAPI 应用，共用一套 MySQL。

现在要把**股票模块**（含投研报告、自选股、karens 问答助理）整体拆出来，成为独立网站 **OpenStock**，用于长期独立发展与迭代。

### 目标（Goals）

1. `openstock` 仓库成为一个可独立运行、独立部署的完整站点（前端 + 后端 + 数据库）
2. 本机能跑通：打开页面、看历史报告、触发分析、发问答，全链路可用
3. 从 karensagent 复制过去的代码**带完整 git 历史**
4. 继承 karensagent 现有的 astryx 风格问答 UI，不重新设计

### 非目标（Non-goals）

1. **不改** karensagent 的任何代码——它是冻结存档
2. 不做新功能，只做「拆分 + 迁移 + 跑通」
3. 不做部署上线（服务器、域名、反向代理留到下一轮）
4. 不重新设计视觉

### 反目标（Anti-goals）

以下情况即使「技术上能跑」也算失败：

1. 两个仓库之间需要长期手工同步同一段代码
2. karensagent 被拆坏（它必须原样可用）
3. 迁移后历史报告丢失
4. 新站启动依赖 karensagent 的服务

---

## 二、已确认的决策

| # | 决策点 | 结论 |
|---|---|---|
| 1 | 拆分动机 | 独立演进，长期把股票模块做深做透 |
| 2 | 仓库形态 | **彻底分家**：新建独立仓库 openstock |
| 3 | 原项目处置 | **复制，不删除**。karensagent 里股票模块原样保留 |
| 4 | 问答助理归属 | **两边都要**：`chat_agent` 一并复制到 openstock |
| 5 | 新站首页 | **`/` 直接是股票仪表盘**，不保留 3D 办公室 |
| 6 | UI | **原样继承**，含 astryx 双态问答面板、配色 token |
| 7 | 数据库 | **独立新库 + 一次性迁移现有股票数据**，迁完两边各写各的 |
| 8 | karensagent 后续 | **冻结**：复制那刻定格，以后只维护 openstock |
| 9 | iFinD 依赖 | **继续复用外部目录** `~/.claude/skills/ifind-finance-data/` |
| 10 | git 历史 | **完整带过去**（clone 全量历史 → 删无关文件 → 改 remote → 推送） |
| 11 | 品牌名 | **OpenStock**（纯英文，与仓库/未来域名一致） |
| 12 | 本轮范围 | **先跑通**，本机可访问即可，不碰部署 |
| 13 | 端口 | 前端 **5174**、后端 **8901**、数据库名 **openstock** |

---

## 三、方案选型记录

### 3.1 仓库形态

| 方案 | 说明 | 取舍 |
|---|---|---|
| **A. 彻底分家（选定）** | 独立仓库、独立后端、独立数据库 | 两个项目完全解耦；代价是两份代码各自演化 |
| B. monorepo 双入口 | 同仓库拆两套 build 入口 | 共享代码成本低，但违背「独立演进」的初衷 |
| C. 只拆前端 | 后端继续连 karensagent | 新站命脉握在另一个部署上，一挂俱挂 |

**选 A 的理由**：用户明确要长期独立发展。代码耦合实测很低（见下），A 的实施成本并不比 B 高多少。

### 3.2 拆分方式的真实成本（实测）

| 维度 | 实测结论 |
|---|---|
| 代码耦合 | **很低**。`ai_news_agent` 对股票零依赖；股票侧对新闻只有 2 处硬编码 import |
| 数据耦合 | **极低**。两域表之间零外键、零 JOIN，只共用同一个 MySQL 连接 |
| 定时任务 | 股票模块**完全没有**定时任务，可完全不带 APScheduler |
| 真正难搬的 | 仓库外的 iFinD skill 目录、两套飞书 Webhook、两套 LLM 凭证 |

---

## 四、目标目录结构

```
openstock/
├── frontend/
│   ├── index.html                    改：title / lang
│   ├── package.json                  改：移除 three、@tresjs/*
│   ├── vite.config.js                改：端口 5174，移除 TresJS 插件
│   ├── public/
│   │   └── favicon.svg
│   └── src/
│       ├── main.js                   改：保留 stock 持久化插件
│       ├── App.vue                   改：简化布局
│       ├── style.css                 原样：含全部 astryx token
│       ├── api/index.js              改：只留股票 + chat
│       ├── router/index.js           改：路由扁平化
│       ├── stores/
│       │   ├── stock.js              原样
│       │   └── agent.js              改：只留 toast
│       ├── components/
│       │   ├── TopNav.vue            改：品牌 + 单模块导航
│       │   ├── DividerLine.vue       原样
│       │   └── report/               整目录（21 个文件）
│       ├── views/agent/
│       │   ├── StockDashboard.vue    原样
│       │   ├── StockHistory.vue      原样
│       │   ├── StockReport.vue       原样
│       │   └── StockSettings.vue     原样
│       ├── utils/
│       │   ├── stock.js              原样
│       │   ├── time.js               原样
│       │   └── carousel.js           原样
│       └── assets/chat/              4 个 SVG 原样
├── backend/
│   ├── main.py                       改
│   ├── config.py                     改
│   ├── database.py                   改
│   ├── models.py                     改：删 PushHistory
│   ├── requirements.txt              修：补缺失包
│   ├── routers/stock_api.py          原样
│   ├── stock_agent/                  整树 + 补 __init__.py
│   ├── chat_agent/                   整树
│   ├── tests/                        股票相关测试 + 改 conftest
│   └── .env                          新建（不进 git）
├── .gitignore
├── LICENSE
└── README.md
```

---

## 五、前端搬迁清单

### 5.1 原样带走

| 文件 | 说明 |
|---|---|
| `src/stores/stock.js` | 唯一 API 消费方，全部页面经它调后端 |
| `src/style.css` | 含 astryx 全部 token（`--ax-*`） |
| `src/components/report/` | 21 个文件：15 个报告模块组件 + 3 个问答组件 + 3 个测试 |
| `src/views/agent/StockDashboard.vue` | 股票仪表盘 |
| `src/views/agent/StockHistory.vue` | 历史报告 |
| `src/views/agent/StockReport.vue` | 报告详情（含问答面板） |
| `src/views/agent/StockSettings.vue` | 自选股 + 10 维度 + 飞书推送 + iFinD 状态 |
| `src/utils/stock.js` | 被 8 个文件引用 |
| `src/utils/time.js` | 被 ChatMessageItem 引用 |
| `src/utils/carousel.js` | 被 StockDashboard 引用 |
| `src/components/DividerLine.vue` | 被 StockDashboard 引用 |
| `src/assets/chat/*.svg` | assistant / user / matrix-idle / matrix-loader |
| `public/favicon.svg` | |

### 5.2 改造后带走

| 文件 | 改什么 |
|---|---|
| `index.html` | `<title>OpenStock</title>`，`lang="zh-CN"` |
| `package.json` | 删除 `three`、`@tresjs/core`、`@tresjs/cientos` |
| `vite.config.js` | 端口改 5174；删除 TresJS 的 `templateCompilerOptions` |
| `main.js` | 保留 pinia 插件（把 `stock.analyzeResult` 持久化到 localStorage）；删除无关注释 |
| `App.vue` | 删除 `is-fullscreen`（无 3D 首页）；保留 `is-wide`（报告详情宽页）与 page transition |
| `api/index.js` | 删除 `getDashboardStats` / `getHistory` / `getHistoryDetail` / `triggerFull`；保留全部 stock + chat |
| `stores/agent.js` | 只保留 `toast` 与 `showToast`；删除 `agents` 注册表、`stats`、`pushHistory`、`fetchStats`、`fetchHistory`、`triggerFull` |
| `TopNav.vue` | 品牌改 `OpenStock`；删除 Agent 标签栏；子导航改为「仪表盘 / 历史报告 / 配置管理」；去掉 `goAgent`/`goHome` 里的 `/agent/*` 前缀 |
| `router/index.js` | 见 5.3 |

### 5.3 路由扁平化

| 旧路径 | 新路径 | 组件 |
|---|---|---|
| `/agent/stock` | **`/`** | StockDashboard |
| `/agent/stock/report/:id` | **`/report/:id`** | StockReport（`meta.wide: true`） |
| `/agent/stock/history` | **`/history`** | StockHistory |
| `/agent/stock/settings` | **`/settings`** | StockSettings |

`TopNav` 的 `activeAgentId` 正则、`subNavItems` 的 `navMap` 一并简化。

### 5.4 明确不带走

| 文件/目录 | 原因 |
|---|---|
| `views/OfficeHome.vue`、`HomeLegacy.vue` | 3D 办公室首页，Q5 已决定不要 |
| `views/Settings.vue` | **空壳**，只有一句说明 + 一个跳转链接 |
| `views/agent/AiNewsDashboard.vue`、`AiNewsHistory.vue` | AI 新闻，留在原项目 |
| `views/agent/StockPlaceholder.vue` | **死代码**，全站无引用 |
| `components/office/` 整目录 | 3D 相关 |
| `components/EmptyState.vue` | 全站无引用 |
| `components/SelectPicker.vue` | 全站无引用 |
| `components/DatePicker.vue` | 全站无引用 |
| `components/AnimatedClock.vue` | 只被 AiNewsDashboard 引用 |
| `composables/useModel.js` | 3D 模型加载 |
| `public/models/`、`public/*.svg`（3D 头像等） | 3D 资源 |
| `public/icons.svg`、`public/sexy 1.svg` | 需实施时再确认是否被引用 |

---

## 六、后端搬迁清单

### 6.1 原样带走

| 路径 | 说明 |
|---|---|
| `routers/stock_api.py` | 14 个股票端点，prefix `/api/stock` |
| `stock_agent/` 整树 | 分析管线、数据源、iFinD skill 封装、prompts、pydantic models |
| `chat_agent/` 整树 | karens 问答：graph / prompts / tools / database / routers/chat.py |
| `tests/test_stock_api.py` | |
| `tests/test_stock_api_integration.py` | |
| `tests/test_analyze.py` | |
| `tests/test_history.py` | |
| `tests/test_models.py` | |
| `tests/test_render.py` | |
| `tests/test_validator.py` | |
| `tests/test_indicators.py` | |
| `tests/test_report_unit.py` | |
| `tests/test_skill_extract.py` | |
| `tests/test_skill_summary.py` | |
| `tests/test_sliding_window.py` | |
| `tests/test_eastmoney.py` / `test_eastmoney_proxy.py` / `test_tencent_name.py` | |
| `tests/test_hk_stock_support.py` | |
| `tests/test_critical_failure_gate.py` | |
| `tests/test_chat_agent_chat.py` / `test_chat_agent_graph.py` / `test_chat_agent_tools.py` | |

### 6.2 切开后带走（不是整文件搬）

**`models.py`** — 只保留 4 个股票模型，删除 `PushHistory`（AI 新闻专用）：
- `StockReport` → `stock_reports`
- `StockWatchlist` → `stock_watchlist`
- `ChatSession` → `chat_sessions`
- `ChatMessage` → `chat_messages`

**`database.py`** — 保留：
- 引擎 / `Base` / `SessionLocal` / `get_db()` / `init_db()` / `_model_to_dict`
- 全部股票 CRUD：`save_stock_report`、`_trim_stock_reports`、`get_stock_report_by_id`、`get_latest_report`、`get_recent_reports`、`get_stock_reports`、`delete_stock_report`、`add_watchlist` / `get_watchlist` / `update_watchlist` / `delete_watchlist`
- 常量 `STOCK_REPORT_MAX = 80`、`STOCK_REPORT_MIN_TRIM = 10`

删除：`init_db()` 里那行 `from ai_news_agent.models import AiNewsReport`

**`config.py`** — 保留 `_load_env`、`DATABASE_URL`、`LLM_MODEL_ID` / `LLM_API_KEY` / `LLM_BASE_URL`
新增为正式配置项：`DEEPSEEK_API_KEY`、`FEISHU_STOCK_WEBHOOK_URL`
删除：`FEISHU_WEBHOOK_URL`、`PUSH_TIME`、`TAVILY_API_KEY`、未使用的 `ANTHROPIC_API_KEY` / `QWEN_*`

**`main.py`** — 保留路由装配（stock + chat）+ CORS + 静态挂载 + `/api/health`
删除：`ai_news_agent.scheduler` 的启停、三个 news router、`config_router`
`/api/health` 里的 iFinD 探测**保留**（本来就是股票能力）

### 6.3 明确不带走

- `ai_news_agent/` 整树
- `routers/config_api.py`（改的是 AI 新闻的飞书 Webhook）
- `tests/test_ai_news_agent.py`
- `karens_agent.db`（旧 V1 SQLite 残留）
- `backend/deploy.sh`（已过时，引用了不存在的 `seed_keywords`）
- `stock_agent/reports/failures/` 里的 39 个失败语料（运行产物，建议清空）

---

## 七、数据库方案

### 7.1 目标状态

| 项 | 值 |
|---|---|
| MySQL 实例 | `localhost:3306` |
| 新库名 | `openstock` |
| 字符集 | `utf8mb4` / `utf8mb4_general_ci` |
| 连接串 | `mysql+pymysql://<user>:<pass>@localhost:3306/openstock` |

### 7.2 需要迁移的表

| 表 | 现有行数 | 迁移 |
|---|---|---|
| `stock_reports` | 75 | ✅ |
| `stock_watchlist` | 5 | ✅ |
| `chat_sessions` | 11 | ✅ |
| `chat_messages` | 64 | ✅ |
| `push_history` | 16 | ❌ AI 新闻专用 |
| `ai_news_reports` | 当前 `karens_agent` 库中不存在 | ❌ |

### 7.3 迁移方式

优先用 Navicat 图形化操作：

1. 在 `localhost` 连接下新建数据库 `openstock`（utf8mb4）
2. 右键 `karens_agent` →「数据传输」→ 目标 `openstock` → 只勾选上述 4 张表
3. openstock 的 `.env` 中 `DATABASE_URL` 指向 `openstock`

迁移完成后，两边彻底断开：
- karensagent 继续写 `karens_agent` 库
- openstock 只写 `openstock` 库
- 两库之间不再有任何同步

### 7.4 ✅ 已确认：数据库层就绪（2026-10-30 复验通过）

用户在 Navicat 中新建了一个名为 `openstock` 的连接，在其下创建了 `openstock` 数据库，并用「数据传输」把四张表复制了过来。

**实测复验结果**（`localhost:3306`）：

| 表 | karens_agent | openstock | 结论 |
|---|---|---|---|
| `stock_reports` | 75 | 75 | 行数一致 |
| `stock_watchlist` | 5 | 5 | 行数一致 |
| `chat_sessions` | 11 | 11 | 行数一致 |
| `chat_messages` | 64 | 64 | 行数一致 |

- 四张表的**列结构完全一致**：列数、字段类型、可空性、主键索引逐项比对相同
- `openstock` 库中**不含** `push_history` / `ai_news_reports`，符合预期

**结论**：数据库层已就绪。实施时 openstock 的 `DATABASE_URL` 直接指向 `openstock` 库即可，无需再做任何数据库操作。

---

## 八、已知坑位与处理方式

拆分时必须逐条处理，否则 openstock 起不来。

| # | 坑位 | 位置 | 处理 |
|---|---|---|---|
| 1 | 启动即崩：无条件 import 新闻调度器 | `main.py:35` | 删除 `from ai_news_agent.scheduler import start_scheduler` |
| 2 | 建表失败：init_db 无条件 import 新闻模型 | `database.py:51` | 删除 `from ai_news_agent.models import AiNewsReport` |
| 3 | `stock_agent/` 没有 `__init__.py`，是隐式命名空间包 | `stock_agent/` | 补一个空的 `__init__.py` |
| 4 | `analyze.py` **import 期**读 `.env`、改 `os.environ`、`sys.path.insert` | `stock_agent/analyze.py:9-30` | 改为惰性初始化或收敛到 `config.py`；`sys.path` 注入保留 |
| 5 | 两套 LLM 凭证语义不同 | `DEEPSEEK_API_KEY`（股票分析） vs `LLM_API_KEY`（问答） | **不合并**，各自保留；在 `config.py` 中分别定义 |
| 6 | `requirements.txt` 缺三个已 import 的包 | `requirements.txt` | 补 `requests`（股票必需）。`anthropic` / `tavily-python` 只有新闻用，**不带** |
| 7 | 测试 conftest 耦合两域 | `tests/conftest.py` | 删除「禁用新闻调度器」的部分，保留「切测试 SQLite + 清股票表」 |
| 8 | 前端 API / 路由 / store 混装 | `api/index.js`、`router/index.js`、`stores/agent.js` | 按第五节的改造清单拆分 |
| 9 | 前端调了不存在的接口 | `api/index.js` 的 `triggerStockCollect` → `/api/stock/collect` | 后端无此路由。实施时**一并删除**该函数及其调用方 |
| 10 | 静态挂载路径 | `main.py` 的 `../frontend/dist` | 新仓库结构一致，路径不用改 |

---

## 九、git 历史迁移方式（决策 10 = 完整历史）

```bash
# 1. 在 D:\ 下克隆当前项目（带完整历史）
git clone https://github.com/WL-karensouza/karensagent.git openstock-work

# 2. 删除所有非股票文件（按第五、六节的「不带走」清单）

# 3. 改 remote 指向新仓库
git remote set-url origin https://github.com/WL-karensouza/openstock.git

# 4. 提交拆分结果
git add -A
git commit -m "refactor: 从 karensagent 拆出股票模块成为独立站 OpenStock"

# 5. 强推覆盖 GitHub 上的 initial commit（LICENSE + README）
git push -f origin main
```

**注意**：第 5 步是 **force push**，会覆盖 openstock 仓库里 GitHub 自动生成的 `Initial commit`。已确认该提交只含 LICENSE 和 README，无实际内容，可安全覆盖。

---

## 十、运行配置

### 10.1 端口

| 服务 | karensagent | openstock |
|---|---|---|
| 前端 dev | 5173 | **5174** |
| 后端 API | 8900 | **8901** |

### 10.2 openstock 的 `.env`（不进 git）

键名清单：
- `DATABASE_URL` → 指向 `openstock` 库
- `DEEPSEEK_API_KEY`
- `FEISHU_STOCK_WEBHOOK_URL`
- `LLM_API_KEY` / `LLM_MODEL_ID` / `LLM_BASE_URL`
- `IFIND_AUTH_TOKEN`（由外部 iFinD skill 消费）

### 10.3 外部依赖

`~/.claude/skills/ifind-finance-data/` —— 由 `stock_agent/skill/client.py` 通过 `sys.path.insert` 导入。
**该目录不在仓库内**，两台机器同时跑 karensagent 和 openstock 时共用这一份即可。
如果将来部署到服务器，那台机器必须同样具备该目录与 `IFIND_AUTH_TOKEN`。

---

## 十一、验收标准

本轮「先跑通」完成的定义：

1. `cd openstock/backend && python main.py` 在 **8901** 端口启动成功，无 ImportError
2. `cd openstock/frontend && npm run dev` 在 **5174** 端口启动成功
3. 浏览器打开 `http://localhost:5174` 直接就是股票仪表盘，**无 3D 场景**
4. 仪表盘能看到自选股（5 只）与最新报告摘要
5. `/history` 能看到历史报告，且**能打开旧的 75 份报告中的任意一份**
6. `/report/:id` 详情页正常渲染（9 个模块卡片、评分仪表、风险预警）
7. 报告页右侧的 karens 问答面板正常显示，**收拢态 / 展开态两态都正确**
8. 能在问答面板提问并收到流式回答
9. `/settings` 能看到自选股列表、10 个维度勾选、iFinD 连接状态
10. 顶部导航显示 **OpenStock**，子导航为「仪表盘 / 历史报告 / 配置管理」
11. 后端测试：`python -m pytest tests/` 跑通（股票相关用例全绿）
12. 前端测试：`npm test` 跑通
13. **karensagent 项目本身不受任何影响**——切换回去仍能正常启动

---

## 十二、明确不做的事

- ❌ 不修改 karensagent 仓库的任何文件
- ❌ 不删除 karensagent 的任何文件（包括股票模块）
- ❌ 不修复 karensagent 的 `requirements.txt`（保持冻结）
- ❌ 不做部署、域名、HTTPS、反向代理
- ❌ 不重新设计 UI
- ❌ 不新增功能
- ❌ 不做两个仓库之间的代码同步机制

---

## 十三、待确认事项

| # | 事项 | 状态 |
|---|---|---|
| 1 | `openstock` 数据库是否已真实创建在 `localhost:3306` | ✅ **已确认**：4 张表行数与列结构均已核验一致（见第 7.4 节） |
| 2 | `public/icons.svg`、`public/sexy 1.svg` 是否被股票页面引用 | 待实施时 grep 确认 |
| 3 | `stock_agent/reports/failures/` 的 39 个失败语料是否要带 | 建议清空，实施时确认 |

---

## 十四、后续轮次（本轮不做）

1. **部署方案**：服务器、域名、Nginx 反代、systemd 服务、iFinD skill 如何在服务器落地
2. **karensagent 侧收尾**：在冻结的股票入口加「本模块已迁移至 OpenStock」提示
3. **openstock 功能演进**：拆分完成后再谈新功能
