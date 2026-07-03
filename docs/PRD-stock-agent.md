# 产品需求文档：股票分析 Agent

**作者**：王磊
**日期**：2026-07-03
**状态**：Phase 2 规划中
**版本**：1.0（初稿）

---

## 1. 执行摘要

股票分析 Agent 是 karensAgent 多智能体平台的**第二个 Agent 插件**。它每日自动抓取 A 股大盘数据，通过 DeepSeek 大模型生成"市场动荡报告"推送到飞书；同时支持在 Web 端输入任意 A 股代码，从技术面、资金面、消息面、基本面四个维度进行深度分析（"个股体检"）。

### 核心差异化

| 对比维度 | 传统行情软件（同花顺/东财） | 股票分析 Agent |
|----------|--------------------------|---------------|
| 信息获取 | 被动翻看 N 个页面 | **一张飞书卡片看完今日重点** |
| 分析方式 | 看指标 → 人脑判断 | **LLM 综合多维度信息 → 自然语言结论 + 评分** |
| 时间成本 | 每天 15-30 分钟 | **推送即读，2 分钟搞定** |
| 个股分析 | 分散在 F10/盘口/K 线 | **一次输入，四维报告，含风险提示** |

---

## 2. 背景与目标

### 2.1 参考项目启示

从 [daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis)（53k+ stars）提取的关键设计借鉴：

| 模块 | 借鉴点 | 本项目简化方案 |
|------|--------|--------------|
| **Agent 编排** | 多 Agent 流水线（Technical → Intel → Risk → Decision） | 单 Agent + 内部 Skills 拆分，不引入多 Agent 通信复杂度 |
| **数据源抽象** | `data_provider/` 统一接口，12 种数据源 fallback | 先用 akshare 单一数据源，接口预留扩展 |
| **技能系统** | `Skill` dataclass + YAML 定义 + `SkillManager` 动态加载 | 硬编码 3-4 个分析维度，接口参考 Skill 设计 |
| **LLM 引擎** | LiteLLM 适配 10+ 模型后端 | 直连 DeepSeek API，后续加模型切换开关 |
| **GA 定时** | `00-daily-analysis.yml` 工作日 18:00 触发 | 参考其结构，简化为 karensAgent 版本 |
| **分析报告 Schema** | `AnalysisReportSchema` 结构化 JSON（评分/趋势/风险/催化/操作清单） | 简化版 schema，聚焦核心字段 |

### 2.2 目标

| # | 目标 | 类型 |
|---|------|------|
| G1 | 每日 18:00 自动推送大盘动荡报告，总结当日市场情绪和关键变化 | 功能 |
| G2 | Web 端输入 A 股代码，30 秒内返回结构化的个股分析报告 | 功能 |
| G3 | 分析报告不是数据罗列，而是有独立逻辑洞察的"阅读材料" | 体验 |
| G4 | 新增一个分析维度（如"行业对比"）≤ 50 行代码，不修改调度逻辑 | 架构 |

### 2.3 非目标（本次不做）

| # | 内容 | 原因 |
|---|------|------|
| N1 | 港股/美股分析 | 先聚焦 A 股，数据源和规则复杂度可控 |
| N2 | 回测系统 | 参考项目有完整回测，本项目聚焦"分析"而非"策略验证" |
| N3 | 实时盘中监控/自动交易 | 法律风险和复杂度双高，只做盘后分析 |
| N4 | 多 Agent 协作编排（orchestrator 模式） | 单 Agent 足够，过度设计 |
| N5 | 聊天机器人多轮对话（钉钉/飞书 Bot） | 先做 Web + 推送，Bot 后续迭代 |

---

## 3. 用户故事

### P0 — 必须拥有（当前实现）

| # | 用户故事 | 验收标准 |
|---|----------|----------|
| US1 | 作为用户，我每个交易日 18:00 自动收到飞书推送的市场动荡报告，一眼看清今天大盘是涨是跌、哪些板块在动、有没有异常信号 | 飞书卡片包含：主要指数涨跌 / 涨跌家数 / 领涨领跌板块 / LLM 生成的市场点评 / 异动个股提示 |
| US2 | 作为用户，我在 Web 端搜索框输入股票代码（如 "600519" 或 "茅台"），点击分析，30 秒内得到一份包含评分、技术面、资金面、消息面、风险提示的结构化报告 | API 返回结构化 JSON；前端渲染为报告卡片，含评分仪表盘、颜色标签 |
| US3 | 作为用户，我可以在 Stock Agent 页面看到自选股列表，点击任意一只直接触发分析 | 自选股 CRUD；列表项显示名称、代码、最近分析时间和评分 |
| US4 | 作为用户，当个股分析生成后，我可以一键推送到飞书 | "推送到飞书"按钮 → 调用现有 notifier 模块 → 飞书卡片送达 |

### P1 — 应该拥有（后续迭代）

| # | 用户故事 | 验收标准 |
|---|----------|----------|
| US5 | 作为用户，我可以在前端查看历史分析报告列表，按日期和股票筛选 | 历史列表页 + 报告详情弹窗 |
| US6 | 作为用户，当大盘出现异常波动（单日涨跌 > 2%），飞书推送会标红提示 | 报告中"动荡指数"高于阈值时，卡片标题变红 |
| US7 | 作为用户，我可以配置自选股列表并在飞书推送中获得这些股票的摘要分析 | 每日推送附带自选股概览（一行一只，含评分） |

### P2 — 锦上添花（远期）

| # | 用户故事 |
|---|----------|
| US8 | 作为用户，我可以用自然语言描述想分析的角度（"帮我看看茅台最近的北向资金变化趋势"） |
| US9 | 作为用户，我可以对比两只股票的分析报告，LLM 给出横向比较结论 |
| US10 | 作为用户，个股报告可以一键导出为 Markdown 文件 |

---

## 4. 解决方案概述

### 4.1 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Karens Agent 平台                         │
├─────────────────────────────────────────────────────────────┤
│  前端 (Vue3 + Vite + Pinia)                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  Home    │ │  GitHub  │ │  Stock   │ │ Settings │        │
│  │ 控制台   │ │  Agent   │ │  Agent   │ │ 平台设置  │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│                      │ Axios / REST API                       │
├──────────────────────┼──────────────────────────────────────┤
│  后端 (FastAPI :8900) │                                        │
│  ┌───────────────────┴─────────────────────────────────┐     │
│  │  Routers: dashboard / trigger / config              │     │
│  │           stock_analysis / stock_watchlist           │     │
│  └─────────────────────────────────────────────────────┘     │
│  ┌──────────────┐ ┌────────────────────────────────────┐    │
│  │  Scheduler   │ │         Stock Analysis Engine       │    │
│  │  APScheduler │ │  ┌──────────┐ ┌──────────────────┐ │    │
│  │  每个交易日  │ │  │ 数据采集层│ │   LLM 分析引擎   │ │    │
│  │  18:00 执行  │ │  │ akshare   │ │   DeepSeek API   │ │    │
│  └──────────────┘ │  │ 大盘+个股 │ │   Prompt + JSON  │ │    │
│                   │  └──────────┘ └──────────────────┘ │    │
│                   │  ┌─────────────────────────────────┐│    │
│                   │  │       Skills（分析维度）         ││    │
│                   │  │ 技术面│资金面│消息面│基本面     ││    │
│                   │  │ (默认启用) (默认启用) (按需)     ││    │
│                   │  └─────────────────────────────────┘│    │
│                   └────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Database: SQLite (dev) / MySQL (prod)               │   │
│  │  Tables: stock_reports, stock_watchlist, push_history │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  外部服务                                                     │
│  akshare（行情数据）· DeepSeek API（LLM 分析）· 飞书 Webhook  │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 数据流

```
                        ┌─ 定时触发（APScheduler 18:00）
                        │
                        ▼
┌──────────────────────────────────────────────┐
│           fetch_market_snapshot()             │
│  akshare: 大盘指数 / 涨跌分布 / 板块排名       │
│           / 成交量 / 北向资金                  │
└────────────────────┬─────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────┐
│        build_market_report_prompt()           │
│  将原始数据 + 分析指令 → DeepSeek Prompt       │
└────────────────────┬─────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────┐
│           DeepSeek API 调用                    │
│  Chat Completion → 结构化 JSON 报告            │
└────────────────────┬─────────────────────────┘
                     │
                     ▼
┌──────────────┐  ┌──────────────┐  ┌──────────┐
│ 存入 DB       │  │ 飞书卡片推送  │  │ 前端展示 │
│ stock_reports │  │ notifier.py  │  │ Dashboard│
└──────────────┘  └──────────────┘  └──────────┘


个股分析流程（Web 手动触发）：

POST /api/stock/analyze {stock_code: "600519"}
    │
    ├─ 1. fetch_stock_data(stock_code)
    │     ├─ akshare 日 K 线（近 60 日）
    │     ├─ akshare 实时行情（价/量/换手/量比）
    │     ├─ akshare 资金流向（主力/超大单/散户）
    │     └─ akshare 个股新闻（近 3 日）
    │
    ├─ 2. 对各 skill 准备 context
    │     ├─ technical_skill: K线 + MA/MACD/RSI/BOLL 指标
    │     ├─ capital_skill: 主力资金 + 北向资金 + 融资融券
    │     ├─ news_skill: 新闻标题 + 公告摘要
    │     └─ fundamental_skill: PE/PB/ROE/营收增速（预留）
    │
    ├─ 3. build_analysis_prompt(stock_context) → DeepSeek
    │
    └─ 4. 返回结构化 JSON → 前端渲染报告卡片
```

### 4.3 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 数据源 | akshare | 免费、数据全（A股行情/资金流/新闻）、纯 Python、无需注册 |
| LLM | DeepSeek API | 便宜（¥1/百万 token）、中文好、无需科学上网、API 稳定 |
| 分析模式 | 大盘自动 + 个股按需 | 大盘每日推送用户零成本；个股按需调用省 API 费用 |
| Skills 接口 | 函数式 skill 注册 | 每个 skill 是一个函数，输入 stock_context，输出分析文本片段 |
| Prompt 策略 | 系统指令 + 数据 context + JSON Schema 约束 | 严格的 JSON Schema 让 LLM 输出结构化、可解析的结果 |
| 大盘定时 | APScheduler（本地）/ GitHub Actions（云端）| 双模式：本地开发用 APScheduler，GA 零成本定时 |
| 个股分析 API | 同步接口（等待 LLM 返回）| 个股分析耗时 15-30 秒，同步等待可接受，避免轮询复杂度 |

---

## 5. 核心模块设计

### 5.1 Skills 技能系统（分析维度）

参考开源项目的 `Skill` 设计，但简化为**函数式注册**：

```python
# backend/stock_agent/skills/__init__.py

from typing import Protocol, Dict, Any

class AnalysisSkill(Protocol):
    """分析技能协议 —— 一个 skill 对应一个分析维度"""
    name: str
    label: str          # 中文显示名
    description: str    # 功能描述
    required_data: list[str]  # 需要的原始数据字段

    def analyze(self, stock_context: Dict[str, Any]) -> str:
        """分析 stock_context，返回自然语言分析文本片段"""
        ...
```

内置 4 个技能：

| 技能 | 文件 | 分析内容 | 默认状态 |
|------|------|----------|:---:|
| `technical_skill` | 技术面分析 | K 线形态、均线排列、MACD/RSI/BOLL 指标解读、支撑压力位 | ✅ 启用 |
| `capital_skill` | 资金面分析 | 主力净流入/流出、北向资金、大单中单小单分布、融资余额变化 | ✅ 启用 |
| `news_skill` | 消息面分析 | 近期新闻关键词提取、利好/利空分类、公告解读 | ✅ 启用 |
| `fundamental_skill` | 基本面分析 | PE/PB 分位、ROE、营收/利润增速、行业对比 | 📋 预留 |

**扩展方式：** 新增一个技能只需：
1. 在 `backend/stock_agent/skills/` 下创建新文件，实现 `AnalysisSkill` 协议
2. 在 `__init__.py` 注册到 `SKILL_REGISTRY` 字典
3. 前端 Settings 页面自动出现新开关

### 5.2 LLM 分析引擎

```python
# backend/stock_agent/analyzer.py

async def analyze_stock(
    stock_code: str,
    stock_context: Dict[str, Any],  # akshare 采集的原始数据
    enabled_skills: List[str] = None,
) -> StockReport:
    """
    个股分析引擎：
    1. 对每个启用的 skill 准备 context
    2. 组装完整 Prompt（系统指令 + 各 skill context + 输出规范）
    3. 调用 DeepSeek API
    4. 解析返回的结构化 JSON → StockReport
    """
```

**Prompt 设计原则（关键）：**
- 系统指令明确角色："你是一个专业的 A 股分析师..."
- 数据与指令分离：先给数据，再给分析指令
- JSON Schema 约束输出格式，防止幻觉
- 要求 LLM 区分"数据事实"和"分析推断"
- 禁止给出"买入/卖出"操作建议，改为"关注点"和"风险提示"

### 5.3 数据采集层

```python
# backend/stock_agent/fetcher.py

async def fetch_market_snapshot() -> MarketSnapshot:
    """采集大盘快照：指数/涨跌/板块/资金"""

async def fetch_stock_data(stock_code: str) -> StockContext:
    """采集单只个股全量数据"""
```

使用 akshare 的接口：

| 数据 | akshare 函数 | 说明 |
|------|-------------|------|
| 大盘指数 | `stock_zh_index_daily(symbol="sh000001")` | 上证/深证/创业板 |
| 涨跌统计 | `stock_zh_ah_spot()` 等 | 上涨/下跌/平盘家数 |
| 板块涨跌 | `stock_board_concept_name_em()` | 概念板块排名 |
| 个股 K 线 | `stock_zh_a_hist(symbol="600519", period="daily")` | 日 K 线（近 60 日） |
| 个股实时 | `stock_individual_info_em(symbol="600519")` | 实时行情指标 |
| 资金流向 | `stock_individual_fund_flow(stock="600519")` | 主力/散户资金 |
| 个股新闻 | `stock_news_em(symbol="600519")` | 东方财富新闻 |
| 北向资金 | `stock_hsgt_hist_em()` | 沪深港通资金流 |

---

## 6. 数据模型

### 6.1 stock_reports（分析报告）

```sql
CREATE TABLE stock_reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code  VARCHAR(10)  NOT NULL,          -- 股票代码，如 "600519"
    stock_name  VARCHAR(50)  NOT NULL,          -- 股票名称，如 "贵州茅台"
    report_type VARCHAR(20)  NOT NULL DEFAULT 'stock',  -- 'market' | 'stock'
    score       INTEGER,                        -- 综合评分 0-100
    decision    VARCHAR(10),                    -- 看多/看空/震荡
    report_json TEXT         NOT NULL,          -- 完整报告 JSON
    report_md   TEXT,                           -- Markdown 格式报告
    llm_model   VARCHAR(50),                    -- 使用的 LLM 模型
    llm_tokens  INTEGER,                        -- 消耗的 token 数
    created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stock_reports_code ON stock_reports(stock_code);
CREATE INDEX idx_stock_reports_date ON stock_reports(created_at);
```

### 6.2 stock_watchlist（自选股）

```sql
CREATE TABLE stock_watchlist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code  VARCHAR(10) NOT NULL UNIQUE,    -- 股票代码
    stock_name  VARCHAR(50) NOT NULL,           -- 股票名称
    notes       TEXT,                           -- 备注
    enabled     INTEGER    NOT NULL DEFAULT 1,  -- 是否启用
    added_at    DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 6.3 push_history（复用现有表，新增字段）

在现有 `push_history` 表中 agent_type 字段已可区分来源（github / stock）。

---

## 7. API 设计

### 7.1 股票分析

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/stock/analyze` | 个股分析（同步等待 LLM 返回） |
| GET | `/api/stock/reports?stock_code=&limit=&offset=` | 历史报告列表 |
| GET | `/api/stock/reports/{id}` | 报告详情 |
| GET | `/api/stock/latest?report_type=market` | 最新大盘报告 |

**POST /api/stock/analyze 请求体：**
```json
{
    "stock_code": "600519",
    "skills": ["technical", "capital", "news"]
}
```

**返回体：**
```json
{
    "code": 0,
    "data": {
        "id": 42,
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "score": 72,
        "decision": "看多",
        "report": {
            "summary": "茅台近期走势稳健，...",
            "technical": { "trend": "上升通道", "ma_arrangement": "多头排列", "rsi": 58, "supports": ["1680", "1620"], "resistances": ["1750"] },
            "capital": { "main_force": "净流入1.2亿", "north_bound": "连续3日增持", "sentiment": "偏积极" },
            "news": { "recent_events": ["Q1业绩超预期", "北向资金连续增持"], "positive_count": 2, "negative_count": 0 },
            "risks": ["白酒板块整体估值偏高", "消费税政策不确定性"],
            "catalysts": ["茅台1935放量在即", "端午节前备货行情"]
        },
        "report_md": "...",
        "llm_model": "deepseek-chat",
        "created_at": "2026-07-03T18:05:00"
    }
}
```

### 7.2 自选股管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stock/watchlist` | 自选股列表 |
| POST | `/api/stock/watchlist` | 添加自选股 |
| DELETE | `/api/stock/watchlist/{stock_code}` | 删除自选股 |
| PUT | `/api/stock/watchlist/{stock_code}` | 更新备注/启用状态 |

### 7.3 手动触发

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/stock/trigger/market-report` | 手动触发大盘报告生成+推送 |

---

## 8. 前端设计

### 8.1 页面结构

替换现有 `StockPlaceholder.vue` 为完整的 Stock Agent 页面组：

```
src/views/agent/
  ├── StockDashboard.vue     # 主面板：大盘概览 + 搜索分析 + 自选股列表
  ├── StockReport.vue        # 个股报告详情页
  ├── StockHistory.vue       # 历史报告列表
  └── StockSettings.vue      # 自选股管理 + Skills 开关
```

### 8.2 StockDashboard 布局

```
┌─────────────────────────────────────────────┐
│  📊 股票分析                                   │
├─────────────────────────────────────────────┤
│                                              │
│  ┌─────────────────────────────────────┐     │
│  │  输入股票代码或名称进行分析...  [分析] │     │
│  └─────────────────────────────────────┘     │
│                                              │
│  ┌─────────────────┐ ┌──────────────────┐   │
│  │  📈 今日大盘     │ │  ⭐ 我的自选股     │   │
│  │  上证 3250 +0.8% │ │  600519 茅台 72分 │   │
│  │  深证 10521 +1.0%│ │  000858 五粮液   │   │
│  │  创业 2156 +1.4% │ │  300750 宁德时代 │   │
│  │  [查看完整报告]   │ │  [+ 添加自选]    │   │
│  └─────────────────┘ └──────────────────┘   │
│                                              │
│  ┌─────────────────────────────────────┐     │
│  │  📋 最近分析历史                      │     │
│  │  07-03 茅台 72分 看多 →              │     │
│  │  07-03 宁德 58分 震荡 →              │     │
│  │  07-02 五粮液 65分 看多 →            │     │
│  └─────────────────────────────────────┘     │
│                                              │
└─────────────────────────────────────────────┘
```

### 8.3 StockReport 报告卡片设计

参考开源项目的决策仪表盘设计，但更简约（符合 karensAgent 设计系统）：

```
┌─────────────────────────────────────────────┐
│  贵州茅台 (600519)                    ⭐ 72分 │
│  ┌──────────────────────────────────────┐   │
│  │  ████████████░░░░░░░░  看多           │   │
│  │  综合评分 72 分                        │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  📊 技术面                                   │
│  趋势：上升通道，均线多头排列...              │
│  支撑位：1680 / 1620  压力位：1750           │
│                                              │
│  💰 资金面                                   │
│  主力资金净流入1.2亿，北向连续3日增持...      │
│                                              │
│  📰 消息面                                   │
│  ✅ Q1业绩超预期 | ✅ 北向资金增持            │
│                                              │
│  ⚠️ 风险提示                                 │
│  · 白酒板块整体估值偏高                       │
│  · 消费税政策不确定性                         │
│                                              │
│  [📤 推送到飞书] [📋 复制 Markdown]           │
└─────────────────────────────────────────────┘
```

---

## 9. 文件结构规划

```
karensAgent/
├── backend/
│   ├── stock_agent/                 # 🆕 股票 Agent 包
│   │   ├── __init__.py
│   │   ├── analyzer.py              # LLM 分析引擎
│   │   ├── fetcher.py               # akshare 数据采集
│   │   ├── prompts.py               # Prompt 模板管理
│   │   ├── skills/                  # 分析技能
│   │   │   ├── __init__.py           # Skill 协议 + 注册表
│   │   │   ├── technical.py          # 技术面技能
│   │   │   ├── capital.py            # 资金面技能
│   │   │   ├── news.py               # 消息面技能
│   │   │   └── fundamental.py        # 基本面技能（预留）
│   │   └── schemas.py               # 数据模型（StockReport 等）
│   ├── routers/
│   │   └── stock_api.py             # 🆕 股票 API 路由
│   ├── models.py                    # 🔧 新增 stock_reports / stock_watchlist 表
│   ├── main.py                      # 🔧 注册 stock_api router
│   └── scheduler.py                # 🔧 新增大盘定时任务
│
├── frontend/src/
│   ├── views/agent/
│   │   ├── StockDashboard.vue       # 🆕 主面板
│   │   ├── StockReport.vue          # 🆕 报告详情
│   │   ├── StockHistory.vue         # 🆕 历史报告
│   │   └── StockSettings.vue        # 🆕 自选股 + Skills 配置
│   ├── api/index.js                 # 🔧 新增 stock API 函数
│   ├── stores/agent.js              # 🔧 新增 stock state
│   └── router/index.js              # 🔧 新增 stock 路由
│
├── .github/workflows/
│   └── stock-analysis.yml           # 🆕 GitHub Actions 定时分析
│
└── docs/
    ├── PRD-stock-agent.md            # 🆕 本文档
    └── discovery-stock-agent.md      # 发现计划
```

**改动量估算：**

| 层 | 新增文件 | 修改文件 | 预估代码量 |
|------|:---:|:---:|------|
| 后端 - stock_agent 核心 | 7 个 | — | ~500 行 |
| 后端 - API + 模型 | 1 个 | 3 个 | ~200 行 |
| 前端 - 页面 | 4 个 | 3 个 | ~600 行 |
| GA workflow | 1 个 | — | ~80 行 |
| **合计** | **13 个** | **6 个** | **~1400 行** |

符合 PRD 中"新增 Agent ≤ 200 行代码"的目标吗？不完全是——股票 Agent 比 GitHub Agent 复杂，但核心引擎（analyzer.py）控制在 ~150 行，Skills 每个 ~60 行，符合"新增一个 skill ≤ 50 行"的目标。

---

## 10. 飞书推送卡片设计

### 10.1 大盘动荡报告卡片

```
┌────────────────────────────────────────────┐
│  📊 A股市场动荡报告 | 2026-07-03 周三       │  ← 🟢/🟡/🔴 动荡等级
├────────────────────────────────────────────┤
│                                             │
│  📈 主要指数                                 │
│  上证 3250.12  🟢+0.85%                     │
│  深证 10521.36 🟢+1.02%                     │
│  创业板 2156.78  🟢+1.35%                   │
│                                             │
│  📊 市场情绪                                 │
│  上涨 3920 家 | 下跌 1349 家                 │
│  涨停 155 家  | 跌停 3 家                    │
│  成交量 1.28 万亿，较昨日 +8.3%              │
│                                             │
│  🔥 板块表现                                 │
│  🟢 领涨：互联网服务、文化传媒、小金属       │
│  🔴 领跌：保险、航空机场                     │
│                                             │
│  💡 AI 市场点评                              │
│  今日市场情绪偏积极，成交量放大配合指数上涨，│
│  短期趋势健康。科技成长风格占优，互联网和    │
│  AI 相关板块资金持续流入。但需注意保险板块    │
│  的持续走弱可能反映大资金对后市的谨慎态度。  │
│                                             │
│  ⚡ 异动个股                                 │
│  涨停：中钨高新(000657)、新莱应材(300260)    │
│                                             │
├────────────────────────────────────────────┤
│  Karens Agent · 股票分析 · 自动生成          │
└────────────────────────────────────────────┘
```

### 10.2 个股分析推送卡片（略简版）

个股推送到飞书时使用紧凑格式，完整报告在 Web 端查看。

---

## 11. GitHub Actions 定时方案

```yaml
# .github/workflows/stock-analysis.yml
name: 股票每日分析

on:
  schedule:
    - cron: '0 10 * * 1-5'   # 工作日 UTC 10:00 = 北京时间 18:00
  workflow_dispatch:           # 支持手动触发

jobs:
  analyze:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: '3.11'
          cache: 'pip'
      - run: pip install -r requirements.txt
      - name: 执行大盘分析并推送
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          FEISHU_WEBHOOK_URL: ${{ secrets.FEISHU_WEBHOOK_URL }}
          STOCK_WATCHLIST: ${{ secrets.STOCK_WATCHLIST }}
        run: python -m backend.stock_agent.daily_task
```

---

## 12. 实现计划

### Phase 2a：核心引擎（预计 4-6 小时）

| # | 任务 | 文件 | 预估 |
|---|------|------|:---:|
| 1 | Stock Agent 目录结构 + Skill 协议定义 | `backend/stock_agent/__init__.py`, `skills/__init__.py` | 0.5h |
| 2 | akshare 数据采集层 | `backend/stock_agent/fetcher.py` | 1h |
| 3 | Prompt 模板 + JSON Schema | `backend/stock_agent/prompts.py`, `schemas.py` | 0.5h |
| 4 | LLM 分析引擎 | `backend/stock_agent/analyzer.py` | 1h |
| 5 | 技术面 + 资金面 + 消息面 3 个 Skills | `backend/stock_agent/skills/*.py` | 1h |
| 6 | 数据库模型 + 迁移 | `backend/models.py` | 0.5h |

### Phase 2b：API + 前端（预计 4-6 小时）

| # | 任务 | 文件 | 预估 |
|---|------|------|:---:|
| 7 | Stock API 路由 | `backend/routers/stock_api.py` | 1h |
| 8 | 飞书大盘卡片模板 | `backend/formatters/stock_card.py` | 0.5h |
| 9 | 定时任务集成 | `backend/scheduler.py` | 0.5h |
| 10 | StockDashboard + StockReport 页面 | 前端 2 个 .vue | 2h |
| 11 | StockHistory + StockSettings 页面 | 前端 2 个 .vue | 1h |
| 12 | 前端 API + Store + Router | 前端 3 个文件修改 | 1h |

### Phase 2c：CI + 测试 + 文档（预计 2-3 小时）

| # | 任务 | 预估 |
|---|------|:---:|
| 13 | GitHub Actions workflow | 0.5h |
| 14 | 核心逻辑测试 | 1h |
| 15 | 文档更新（PRD + README） | 0.5h |

---

## 13. 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|:---:|:---:|------|
| akshare 接口不稳定，数据偶发失败 | 中 | 中 | 关键数据加 try/except + fallback 默认值；大盘数据缺失时推送标注"部分数据不可用" |
| DeepSeek API 返回格式不合法（不遵循 JSON Schema）| 中 | 高 | retry 机制（最多 2 次）+ 解析失败时降级为纯文本报告 |
| LLM 幻觉（编造不存在的新闻/数据）| 中 | 高 | Prompt 中严格要求引用数据源；对"超出数据范围"的推断标注"仅供参考" |
| 个股分析耗时过长（>30s 用户不耐烦）| 低 | 中 | 只取近 60 日 K 线 + 5 条新闻，控制 context 大小；后续加 loading 动画 |
| akshare 在 GitHub Actions 环境中安装失败 | 中 | 中 | GA workflow 加 akshare 预装测试；如不行回退到纯 HTTP 调用东方财富 API |

---

## 14. 开放问题

| # | 问题 | 优先级 |
|---|------|:---:|
| Q1 | DeepSeek API Key 是否已有？用什么模型版本（`deepseek-chat` / `deepseek-reasoner`）？ | 🔴 高 |
| Q2 | 数据查询时是否已有 akshare 的使用经验？需要我先验证 akshare 关键接口的可用性吗？ | 🟡 中 |
| Q3 | 飞书推送频率：大盘报告每天 1 次没问题，个股分析推送是否需要限制频率？ | 🟢 低 |
| Q4 | 是否需要支持自选股批量分析（一次分析 5 只，合并报告）？ | 🟢 低 |

---

## 15. 附录：参考项目关键代码片段学习

### A. Agent 编排器模式（orchestrator.py）

```python
# 参考项目核心流水线：顺序执行多个 Agent，共享 Context
# 模式 → 本项目借鉴为 skills 的顺序执行
class AgentOrchestrator:
    def run(self, task, context):
        # Technical → Intel → Risk → Decision
        for agent in self.pipeline:
            result = agent.analyze(context)
            context.update(result)
        return context.build_dashboard()
```

### B. Skill 定义（skills/base.py）

```python
# 参考项目用 dataclass 定义 Skill 元数据
# 本项目简化为函数式协议
@dataclass
class Skill:
    name: str
    display_name: str
    instructions: str       # 自然语言，注入 LLM prompt
    required_tools: List[str]
    enabled: bool = False
```

### C. Prompt 注入模式（analyzer.py）

```python
# 参考项目：market_context → phase_context → skill_policy → core_rules → report_schema
# 层层注入，最终组装成完整 system prompt
# 本项目简化为：system_role + skills_context + json_schema
```

---

*文档版本：1.0 | 创建日期：2026-07-03 | 状态：待评审*
