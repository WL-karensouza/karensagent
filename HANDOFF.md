# iFind 重构 + 前端重设计 — 交接文档

> 日期：2026-07-10
> 状态：**产品发现阶段完成，准备进入编码阶段**
> 下一阶段：TDD 编码实现（后端 refactor + 前端 redesign）

---

## 1. 项目概述

用同花顺官方 iFind MCP API 全量替换现有爬虫数据采集层，同时重设计前端页面。这是一次重构级别的改动。

- **项目位置**：`d:\karensAgent\.claude\worktrees\ifind-refactor\`（git worktree 隔离环境）
- **主分支**：master
- **当前分支**：master（worktree 隔离，改动不污染主工作区）

---

## 2. 已完成的验证工作（11 个实验全部通过）

### 2.1 实验清单

| # | 假设 | 实验 | 结果 | 关键发现 |
|:--:|------|------|:--:|------|
| 1 | H1.1 | Stock 数据完整性 | ✅ | 5/5 工具返回有效数据，每工具 5-246 字段 |
| 2 | H1.2 | News 数据完整性 | ✅ | search_news + search_notice 正常，search_trending_news 无权限 |
| 3 | H3.1 | Reasoner 信息增量 | ✅ | Reasoner 比 Chat 多 3+ 独立洞察，引用 iFind 独有数据 |
| 4 | H3.2 | Reasoner 逻辑自洽 | ✅ | Reasoner 0 事实错误；Chat 有 1 处事实错误（判错均线位置） |
| 5 | H7.1 | MCP 并发稳定性 | ✅ | 10/10 成功，session 复用后 ~0.3s/次 |
| 6 | H8.1 | Pydantic 字段覆盖 | ✅ | 枚举 7 工具共 176 个去重字段 |
| 7 | H8.2 | 双格式兼容 | ✅ | 统一解析器兼容 data.answer(markdown) + data.data(json_array) |
| 8 | H3.3 | 成本分析 | ✅ | Reasoner $0.0057/次，200次/月仅 $1.13 |
| 9 | H1.3 | EDB 宏观数据 | ✅ | 8/8 查询成功，含全球半导体销售额等细分指标 |
| 10 | H7.2 | Session 超时 | ✅ | 空闲 5 分钟后 session 仍存活，热复用加速 7x |
| 11 | H7.3 | SSL 安全 | ✅ | verify=True 直接可用，证书 DigiCert 签发，有效期 160 天 |

### 2.2 关键架构发现（来自实验，未写入旧文档）

1. **iFind Stock 和 News 返回格式不同**：
   - Stock server → `data.answer`（markdown 表格，含内嵌 JSON code block）
   - News server → `data.data`（JSON 数组字符串）
   - Pydantic 模型需要统一解析器自动识别格式

2. **iFind 字段三件套模式**：每个指标有 `指标名` + `指标名.params`（查询参数上下文） + `指标名.unit`（单位），Pydantic 不宜写死字段名，需用动态 key-value 模式

3. **search_trending_news 不可用**（当前 token 无权限，错误码 -32002），News 采集只需 search_news + search_notice

4. **ESG 未来季度数据为 null**，前端需处理 null 单元格渲染

5. **verify=True 立即可用**，certifi CA bundle 也通过，直接改 `ifind_call.py` 移除 `verify=False` 即可消除安全风险

6. **EDB 数据质量远超预期**：可查到全球半导体月度销售额、日本半导体设备出货额等高价值细分指标

7. **MCP session 不会短时空闲断开**（5 分钟验证通过），但冷启动需要 ~4s，建议实现 session 预热机制

### 2.3 实验脚本位置

所有实验脚本保存在 `backend/tests/`，可直接复用：

```
backend/tests/
├── probe_ifind_stock.py        # 实验 1
├── probe_ifind_news.py         # 实验 2
├── probe_ifind_reasoner.py     # 实验 3+4
├── probe_ifind_concurrent.py   # 实验 5
├── probe_ifind_pydantic.py     # 实验 6
├── probe_ifind_format.py       # 实验 7
├── probe_ifind_cost.py         # 实验 8
├── probe_ifind_edb.py          # 实验 9
├── probe_ifind_session.py      # 实验 10
├── probe_ifind_ssl.py          # 实验 11
└── probe_results/              # 所有实验输出 JSON
```

---

## 3. 参考文档索引

| 文档 | 路径 | 内容 |
|------|------|------|
| 重构方案 | `IFIND_REFACTOR_PLAN.md` | 后端目录结构、数据模型、删除清单、测试策略 |
| 前端重设计 | `docs/superpowers/specs/2026-07-10-stock-frontend-redesign.md` | 页面布局、组件树、路由、状态机 |
| 发现计划 | `C:\Users\王磊\.claude\plans\shiny-kindling-gem.md` | 假设优先级、实验设计、决策框架 |
| iFind SDK | `backend/ifind_call.py` | MCP 连接层（已修复 list_tools bug） |
| PRD | `docs/PRD-stock-agent.md` | 完整产品需求文档 |
| 发现文档 | `docs/discovery-stock-agent.md` | 原始发现上下文 |
| 同花顺交接 | `docs/同花顺iFinD接入交接文档.md` | iFind MCP 接入说明 |

---

## 4. 编码阶段准备

### 4.1 后端编码清单（来自 IFIND_REFACTOR_PLAN.md）

**新建文件**：
```
stock_agent/
├── ifind_client.py          # iFind MCP 连接层
├── fetchers/
│   ├── market_data/         # 行情+K线+技术指标 (MarketData)
│   ├── financials/          # 财务 (FinancialsData)
│   ├── news_events/         # 新闻+公告 (NewsEventsData)
│   ├── risk/                # 风险+ESG (RiskData)
│   └── market_env/          # 市场环境+EDB (MarketEnvData)
├── analyze.py               # 主入口（重写）
└── render.py                # Markdown 报告渲染
```

**删除文件**：
- `stock_agent/fetcher.py`
- `stock_agent/skills/` 整个目录（7 个文件）
- `stock_agent/experiment_a.py`
- `backend/tests/test_stock_agent.py`
- `analyze.py` 中旧 prompt 常量（ROLE_DEFINITION/CORE_RULES/OUTPUT_SCHEMA/build_prompt/build_system_prompt）
- `analyze.py` 中 render_markdown（抽出到 render.py）

**TDD 顺序**：先写测试 → 再写实现 → 跑通验证 → 合并回 master

### 4.2 前端编码清单（来自 2026-07-10-stock-frontend-redesign.md）

| 页面/组件 | 路由 | 说明 |
|------|------|------|
| StockDashboard | `/agent/stock` | 搜索 + 5 Tab + 自选股 + 最近报告 |
| StockReport | `/agent/stock/report/:id` | LLM 综合报告展示 |
| StockHistory | `/agent/stock/history` | 历史报告列表 |
| StockSettings | `/agent/stock/settings` | 自选股管理 + 系统配置 |

搜索栏状态机：unanalyzed → running → done/partial/error → report

### 4.3 已知的前置修正（编码前应先处理）

1. **`ifind_call.py`**：`verify=False` → `verify=True`（实验 11 已验证可行）
2. **`ifind_call.py`**：`list_tools()` 的 `_post(server_type)` → `_post(server_type, payload)`（已修复）
3. **SSL 警告抑制**：移除 `verify=False` 后 InsecureRequestWarning 自然消失

---

## 5. iFind MCP API 使用说明

### 5.1 Server 列表

| Server | URL 后缀 | 使用 | 工具数 |
|------|------|:--:|:--:|
| stock | `hexin-ifind-ds-stock-mcp` | ✅ | 6 个工具 |
| news | `hexin-ifind-ds-news-mcp` | ✅ | 2 个可用（search_trending_news 无权限） |
| edb | `hexin-ifind-ds-edb-mcp` | ✅ | 1 个工具 |
| fund | `hexin-ifind-ds-fund-mcp` | ❌ 不使用 | 7 个工具 |

### 5.2 认���配置

- Auth Token：在 `backend/.env` 的 `IFIND_AUTH_TOKEN` 中
- 协议：JSON-RPC 2.0 over HTTPS
- Base URL：`https://api-mcp.51ifind.com:8643/ds-mcp-servers`
- Session 管理：initialize → notifications/initialized → tools/call，session 跨请求复用

### 5.3 返回格式差异（重要！）

```
Stock: result.data.content[].text → JSON.parse → data.answer (markdown 表格)
News:  result.data.content[].text → JSON.parse → data.data (JSON 数组字符串)
EDB:   result.data.content[].text → JSON.parse → data.answer (markdown 表格)
```

---

## 6. 约束与决策

| 决策 | 结论 | 来源 |
|------|------|------|
| 全量替换不保留 fallback | ✅ 已定 | IFIND_REFACTOR_PLAN.md §1 |
| 删除 skills 中间层 | ✅ 已定 | IFIND_REFACTOR_PLAN.md §4 |
| Prompt 放各自职责目录 | ✅ 已定 | IFIND_REFACTOR_PLAN.md §5 |
| 用 deepseek-reasoner 替代 chat | ✅ 已定（实验 3+4 验证） | IFIND_REFACTOR_PLAN.md §8 |
| verify=False → verify=True | ✅ 已定（实验 11 验证） | 新增决策 |
| EDB 纳入 market_env fetcher | ✅ 建议（实验 9 验证） | 新增决策 |
| JSON Schema 重设计 | ⏳ 待定 | IFIND_REFACTOR_PLAN.md §16 |
| 开发阶段顺序 | ⏳ 待定 | IFIND_REFACTOR_PLAN.md §16 |
| 旧文件删除时机 | ⏳ 待定（跑通后再删） | IFIND_REFACTOR_PLAN.md §16 |

---

## 7. 建议的编码顺序

1. **先修 `ifind_call.py`**：verify=True + 已验证的 list_tools 修复
2. **写统一解析器**：`ifind_client.py` 封装 iFind 调用 + 自动格式识别
3. **写 Pydantic 模型**：基于实验 6 的 176 字段覆盖（动态 key-value 模式）
4. **写 5 个 fetcher + prompt.py**：market_data → financials → news_events → risk → market_env
5. **重写 analyze.py + render.py**
6. **写测试**：每步写完后立即跑 probe 脚本验证
7. **前端重构**：Dashboard → Report → History → Settings

---

## 8. 建议调用的 Skills

编码阶段建议按以下顺序使用 skills：

| 步骤 | Skill | 用途 |
|------|------|------|
| 1 | `writing-plans` | 将重构方案 + 实验结果转化为详细的 TDD 实现计划 |
| 2 | `frontend-design` | 基于前端 Spec 设计具体 Vue 组件结构和样式 |
| 3 | `/batch` | 按后端→前端的依赖关系拆分为低耦合子任务，确保每个子任务边界清晰 |
| 4 | `test-driven-development` | 严格 TDD 流程：先写测试 → 再写实现 → 重构 |
| 5 | `code-reviewer` | 每个子任务完成后交叉审查 |
| 6 | `/simplify` | 编码完成后精简冗余代码 |

---

## 9. 注意事项

- **Git 规范**：禁止在 git 记录中暴露 AI 写作痕迹
- **命名规范**：文件名大驼峰，常量/变量小写蛇形，函数方法小驼峰
- **编码风格**：先方案后代码，不问不猜，需求模糊时先提问
- **改动范围**：严格限定在 IFIND_REFACTOR_PLAN.md 和前端 Spec 中明确要求的范围，不涉及的非必要不重构
- **auth_token 安全**：始终从 `.env` 读取，不硬编码，不提交到 git
- **API 月调用量限制**：同花顺 API 有月调用量限制，测试时避免无意义的压力测试
