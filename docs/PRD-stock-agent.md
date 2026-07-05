# 产品需求文档：股票分析 Agent

**作者**：王磊
**日期**：2026-07-03
**最后更新**：2026-07-05
**状态**：Phase 2 核心引擎已完成，API + 前端待开发
**版本**：1.1

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
| **数据源抽象** | `data_provider/` 统一接口，12 种数据源 fallback | 多数据源采集（腾讯+同花顺+新浪+交易所），curl_cffi 绕过系统代理 |
| **技能系统** | `Skill` dataclass + YAML 定义 + `SkillManager` 动态加载 | 函数式注册，6 个分析维度（技术面/资金面/消息面/基本面/风险面/市场环境） |
| **LLM 引擎** | LiteLLM 适配 10+ 模型后端 | 直连 DeepSeek API，后续加模型切换开关 |
| **GA 定时** | `00-daily-analysis.yml` 工作日 18:00 触发 | 参考其结构，简化为 karensAgent 版本 |
| **分析报告 Schema** | `AnalysisReportSchema` 结构化 JSON（评分/趋势/风险/催化/操作清单） | 简化版 schema，聚焦核心字段 |

### 2.2 目标

| # | 目标 | 类型 |
|---|------|------|
| G1 | 每日 18:00 自动推送大盘动荡报告，总结当日市场情绪和关键变化 | 功能 |
| G2 | Web 端输入 A 股代码，30 秒内返回结构化的个股分析报告 | 功能 |
| G3 | 分析报告不是数据罗列，而是有独立逻辑洞察的"阅读材料" | 体验 |
| G4 | 新增一个分析维度只需写技能文件 + 一行注册，不修改调度逻辑 | 架构 |

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
│  │  18:00 执行  │ │  │ 腾讯+同花顺│ │   DeepSeek API   │ │    │
│  └──────────────┘ │  │ +新浪+交易所│ │   Prompt + JSON  │ │    │
│                   │  └──────────┘ └──────────────────┘ │    │
│                   │  ┌─────────────────────────────────────┐│    │
│                   │  │         Skills（6维分析）            ││    │
│                   │  │ 技术面│资金面│消息面│基本面│风险面  ││    │
│                   │  │  │市场环境（全部默认启用）           ││    │
│                   │  └─────────────────────────────────────┘│    │
│                   └────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Database: MySQL（本地开发/生产统一）                   │   │
│  │  Tables: stock_reports, stock_watchlist, push_history │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  外部服务                                                     │
│  腾讯+同花顺+新浪+交易所（行情数据）· DeepSeek API（LLM 分析）· 飞书 Webhook  │
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
│           / 成交量 / 北向资金（LLM知识覆盖）       │
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
    │     ├─ 腾讯 K 线 API（主力，curl_cffi 直调）
    │     ├─ 腾讯实时行情（价/量/换手/量比/PE）
    │     ├─ 同花顺 资金流向（主力净流入排名）
    │     ├─ 沪深交易所 融资融券（个股融资余额/融券余额）
    │     └─ 新浪 基本面数据（PE/PB/ROE/营收增速）
    │
    ├─ 2. 对各 skill 准备 context
    │     ├─ technical_skill: K线 + MA/MACD/RSI/量比指标
    │     ├─ capital_skill: 主力资金（同花顺）+ 融资融券（交易所）；北向资金由LLM知识覆盖
    │     ├─ news_skill: 新闻标题 + 公告摘要
    │     └─ fundamental_skill: PE/PB/ROE/营收增速（新浪源）
    │
    ├─ 3. build_analysis_prompt(stock_context) → DeepSeek
    │
    └─ 4. 返回结构化 JSON → 前端渲染报告卡片
```

### 4.3 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 数据源 | 多源采集（腾讯+同花顺+新浪+交易所，curl_cffi 直调） | 免费、无需注册、绕过 Windows 系统代理；东方财富 API 被封堵，改用替代源 |
| LLM | DeepSeek Reasoner API | 深度推理、中文好、便宜（¥4/百万 token）；通过数据守卫 + Prompt 约束防止幻觉 |
| 分析模式 | 大盘自动 + 个股按需 | 大盘每日推送用户零成本；个股按需调用省 API 费用 |
| Skills 接口 | 函数式 skill 注册 | 每个 skill 是一个函数，输入 stock_context，输出分析文本片段 |
| Prompt 策略 | 系统指令 + 数据 context + JSON Schema 约束 | 严格的 JSON Schema 让 LLM 输出结构化、可解析的结果 |
| 大盘定时 | APScheduler（本地）/ GitHub Actions（云端）| 双模式：本地开发用 APScheduler，GA 零成本定时 |
| 个股分析 API | 同步接口（等待 LLM 返回）| 个股分析耗时 15-30 秒，同步等待可接受，避免轮询复杂度 |
| 飞书推送通道 | GitHub 热榜和股票分析使用独立 Webhook | 两个消息通道互不干扰，方便分别管理机器人、调整推送频率 |
| 报告尾部信息 | 仅显示生成时间，不暴露 LLM 模型和 Token 数 | 终端用户不需要关心底层技术细节，保持报告简洁 |

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

内置 6 个技能（6 维分析）：

| 技能 | 文件 | 分析内容 | 默认状态 |
|------|------|----------|:---:|
| `technical_skill` | 技术面分析 | K 线形态、均线排列、MACD/RSI/BOLL 指标解读、支撑压力位 | ✅ 启用 |
| `capital_skill` | 资金面分析 | 主力净流入（同花顺）、融资融券（沪深交易所官方）、量价配合、换手率 | ✅ 启用 |
| `news_skill` | 消息面分析 | 近期新闻关键词提取、利好/利空分类、公告解读 | ✅ 启用 |
| `fundamental_skill` | 基本面分析 | PE/PB 估值水位、ROE 盈利能力、营收/利润增速、资产负债率（新浪+东方财富源） | ✅ 启用 |
| `risk_skill` | 风险面分析 | 综合技术/资金/基本面/消息四维度风险信号 → 风险等级评定 + Top 3 警惕点 | ✅ 启用 |
| `market_env_skill` | 市场环境分析 | 市值风格、估值风格、相对大盘强弱、板块关联（LLM 知识辅助） | ✅ 启用 |

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
- JSON Schema 约束输出格式
- 要求 LLM 区分"数据事实"和"分析推断"
- 禁止给出"买入/卖出"操作建议，改为"关注点"和"风险提示"

**防幻觉策略（配合 `deepseek-reasoner`）：**

reasoner 模型推理能力强，但数据不足时可能自行脑补。采用三层防线：

1. **数据守卫（调用前）**：`validate_data()` 检查 `latest_close`、`recent_bars` 等关键字段是否存在，缺失则拒绝调用 LLM，直接返回"数据不可用"
2. **Prompt 约束（调用中）**：系统指令明确要求"数据不足时说'数据不足，无法判断'""结论必须有数据支撑""缺失的维度不要编造"；`temperature=0` 最大化输出确定性，确保同样数据 → 同样结论，结果可复现
3. **输出校验（调用后）**：解析 JSON 后检查关键数值是否在合理范围（如评分 0-100、价格与输入数据一致），偏差过大时触发重试或标记"仅供参考"

> 实际案例：之前 `deepseek-chat` 在没有 K 线数据时，把海澜之家 5.46 元编造成"7.5-8 元区间波动"。加入数据守卫后该问题已杜绝。

### 5.3 数据采集层

```python
# backend/stock_agent/fetcher.py

async def fetch_market_snapshot() -> MarketSnapshot:
    """采集大盘快照：指数/涨跌/板块/资金"""

async def fetch_stock_data(stock_code: str) -> StockContext:
    """采集单只个股全量数据"""
```

使用多数据源采集，curl_cffi 直调 HTTP 接口（不依赖 Windows 系统代理）：

| 数据 | 数据源 | 说明 |
|------|--------|------|
| 大盘指数 | akshare `stock_zh_index_daily()` | 上证/深证/创业板 |
| 涨跌统计 | 腾讯 `qt.gtimg.cn` | 上涨/下跌/平盘家数 |
| 板块涨跌 | akshare 同花顺源 | 概念板块排名 |
| 个股 K 线 | 腾讯 `web.ifzq.gtimg.cn`（主力）→ akshare 新浪源（fallback） | 日 K 线（近 90 日）|
| 个股实时 | 腾讯 `qt.gtimg.cn` | 价/量/换手/量比/PE |
| 主力资金 | 同花顺 `data.10jqka.com.cn` | 全市场主力净流入排名 |
| 融资融券 | 上交所/深交所官方 API | 个股融资余额/融券余额 |
| 个股新闻 | akshare 新浪源 | 近 3 日新闻标题 |
| 基本面 | akshare 新浪源 `stock_financial_analysis_indicator()` | PE/PB/ROE/营收增速 |

> ⚠️ 北向资金（沪深港通）目前仅东方财富有免费公开接口（已被封堵），同花顺/新浪/腾讯均不提供。
> 参考 `ZhuLinsen/daily_stock_analysis` 的做法：在 Prompt 中让 LLM 结合训练知识自行考量北向资金因素，不提供实时数据。

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

### 6.3 push_history（复用现有表，需新增字段）

现有 `push_history` 表字段：`push_time`、`platform`（wecom/feishu）、`content_type`（daily/weekly/monthly）、`content`、`repo_count`、`news_count`、`status`。

股票分析推送需新增 `agent_type` 字段（VARCHAR(20)，取值 github/stock），用于区分推送来源。

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

## 9. 文件结构

### 9.1 当前实际结构（Phase 2 核心引擎已完成）

```
karensAgent/
├── backend/
│   ├── stock_agent/                 # 股票 Agent 包
│   │   ├── __init__.py
│   │   ├── analyze.py               # 🔥 主入口：CLI + 数据采集 → LLM 分析 → Markdown 渲染 → 飞书推送（合并了 analyzer/prompts/schemas）
│   │   ├── fetcher.py               # 多数据源采集层（腾讯+akshare+新浪+东方财富，curl_cffi 绕过系统代理）
│   │   ├── experiment_a.py          # 实验 A：LLM 分析质量 PoC（海澜之家 600398）
│   │   ├── skills/                  # 分析技能（6维）
│   │   │   ├── __init__.py           # SkillMeta 协议 + 注册表 SKILLS
│   │   │   ├── technical.py          # 技术面
│   │   │   ├── capital.py            # 资金面
│   │   │   ├── news.py               # 消息面
│   │   │   ├── fundamental.py        # 基本面
│   │   │   ├── risk.py               # 风险面
│   │   │   └── market_env.py         # 市场环境
│   │   ├── reports/                  # 分析报告 Markdown 输出目录
│   │   │   ├── 600398_*.md
│   │   │   ├── 600519_*.md
│   │   │   └── ...
│   ├── tests/
│   │   └── test_stock_agent.py       # 股票 Agent 测试
│   ├── routers/
│   │   └── stock_api.py             # ⬜ 待开发：股票 API 路由
│   ├── models.py                    # ⬜ 待新增 stock_reports / stock_watchlist 表
│   ├── main.py                      # ⬜ 待注册 stock_api router
│   └── scheduler.py                # ⬜ 待新增大盘定时任务
│
├── frontend/src/                    # ⬜ 全部待开发
│   ├── views/agent/
│   │   ├── StockDashboard.vue
│   │   ├── StockReport.vue
│   │   ├── StockHistory.vue
│   │   └── StockSettings.vue
│   ├── api/index.js
│   ├── stores/agent.js
│   └── router/index.js
│
├── .github/workflows/
│   └── stock-analysis.yml           # ⬜ 待开发
│
└── docs/
    ├── PRD-stock-agent.md            # 本文档
    └── discovery-stock-agent.md      # 发现计划
```

### 9.2 CLI 使用方式（当前可用）

```bash
# 分析单只股票（终端查看报告）
python backend/stock_agent/analyze.py 600398

# 分析 + 推送到飞书
python backend/stock_agent/analyze.py 600398 --push

# 批量分析（逗号分隔）
python backend/stock_agent/analyze.py 600398,000858,300750 --push

# 分析默认自选股列表
python backend/stock_agent/analyze.py --watchlist --push

# JSON 格式输出
python backend/stock_agent/analyze.py 600398 --json
```

### 9.3 环境变量

```bash
# .env 配置
DEEPSEEK_API_KEY=sk-...              # DeepSeek API 密钥
FEISHU_WEBHOOK_URL=https://...       # GitHub 热榜推送 Webhook
FEISHU_STOCK_WEBHOOK_URL=https://... # 股票分析推送 Webhook（独立通道）
```

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

### 10.2 个股分析推送卡片

个股推送到飞书时使用飞书卡片消息格式，包含：
- **蓝色标题栏**：显示"股票名称（代码）分析报告"
- **正文**：完整 Markdown 报告（去掉 H1 标题避免与卡片 header 重复）
- **底部注释**：Karens Agent · 股票分析 · 生成时间

> ⚠️ 报告尾部仅显示生成时间，不展示 LLM 模型名称和 Token 消耗量（终端用户不需要关心底层技术细节）。

### 10.3 Webhook 通道分离

| 通道 | 环境变量 | 用途 |
|------|----------|------|
| GitHub 热榜 | `FEISHU_WEBHOOK_URL` | 每日 GitHub Trending + AI 资讯推送 |
| 股票分析 | `FEISHU_STOCK_WEBHOOK_URL` | 个股分析报告推送 |

两个通道使用独立的飞书机器人，互不干扰，便于分别管理推送频率和目标群组。

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

### Phase 2a：核心引擎 ✅ 已完成

| # | 任务 | 文件 | 状态 |
|---|------|------|:---:|
| 1 | Stock Agent 目录结构 + Skill 协议定义 | `backend/stock_agent/__init__.py`, `skills/__init__.py` | ✅ |
| 2 | 多数据源采集层（腾讯+akshare+新浪+东方财富） | `backend/stock_agent/fetcher.py` | ✅ |
| 3 | Prompt 模板 + JSON Schema（合并在 analyze.py） | `backend/stock_agent/analyze.py` | ✅ |
| 4 | LLM 分析引擎（DeepSeek API） | `backend/stock_agent/analyze.py` | ✅ |
| 5 | 6 个 Skills（技术/资金/消息/基本面/风险/市场环境） | `backend/stock_agent/skills/*.py` | ✅ |
| 6 | Markdown 报告渲染 + 飞书推送 | `backend/stock_agent/analyze.py` | ✅ |
| 7 | Webhook 通道分离（GitHub/股票独立） | `backend/.env`, `analyze.py` | ✅ |
| 8 | 报告尾部精简（去掉 DeepSeek/Token 信息） | `backend/stock_agent/analyze.py` | ✅ |
| 9 | Windows UTF-8 控制台编码修复 | `backend/stock_agent/analyze.py` | ✅ |
| 10 | 实验 A：LLM 分析质量 PoC | `backend/stock_agent/experiment_a.py` | ✅ |
| 11 | 核心逻辑测试 | `backend/tests/test_stock_agent.py` | ✅ |

### Phase 2b：API + 前端 ⬜ 待开发

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
| 数据源接口不稳定，数据偶发失败 | 中 | 中 | 多数据源 fallback（腾讯→新浪→akshare）；关键数据缺失时拒绝调用 LLM（data guard） |
| DeepSeek API 返回格式不合法（不遵循 JSON Schema）| 中 | 高 | retry 机制（最多 2 次）+ 解析失败时降级为纯文本报告 |
| LLM 幻觉（编造不存在的价格/新闻/数据）| 中 | 高 | 三层防幻觉策略：数据守卫拦截空数据 + Prompt 约束 + 输出校验；reasoner 模型配合约束可有效降低幻觉率 |
| 个股分析耗时过长（>30s 用户不耐烦）| 低 | 中 | 只取近 60 日 K 线 + 5 条新闻，控制 context 大小；后续加 loading 动画 |
| akshare 在 GitHub Actions 环境中安装失败 | 中 | 中 | GA workflow 加 akshare 预装测试；如不行回退到纯 HTTP 调用东方财富 API |

---

## 14. 开放问题

| # | 问题 | 结论 | 状态 |
|---|------|------|:---:|
| Q1 | DeepSeek API Key 是否已有？用什么模型版本？ | API Key 已有（`.env`）；使用 `deepseek-reasoner`，深度推理能力可提升分析质量；通过数据守卫 + Prompt 约束防止幻觉 | ✅ 已关闭 |
| Q2 | 数据源可用性是否已验证？ | 已验证，腾讯/同花顺/新浪/交易所多源采集层已建立，curl_cffi 绕过系统代理 | ✅ 已关闭 |
| Q3 | 个股分析推送是否需要限制频率？ | 不限制，个股分析是用户手动触发，非自动推送，按需调用不会骚扰 | ✅ 已关闭 |
| Q4 | 是否需要支持自选股批量分析？ | 不需要，保持简单：一次分析一只，多看几只就多次触发 | ✅ 已关闭 |
| Q5 | 是否需要支持北交所（代码 8/9 开头）？ | 2026-07-03 实测 920510（丰光精密）发现腾讯 K 线 API 和 akshare 均不支持北交所，需适配独立数据源。暂不实现，后期评审。 | 🔲 待评审 |
| Q6 | GitHub 热榜和股票分析是否共用同一个飞书 Webhook？ | **不共用**。拆分为两个独立 Webhook（`FEISHU_WEBHOOK_URL` + `FEISHU_STOCK_WEBHOOK_URL`），使用不同机器人，方便分别管理推送频率和目标群组。 | ✅ 已关闭 |
| Q7 | 报告尾部是否需要展示 LLM 模型名和 Token 消耗？ | **不展示**。终端用户不需要关心底层技术细节，仅保留生成时间即可。 | ✅ 已关闭 |
| Q8 | Windows 控制台中文/Emoji 输出乱码如何解决？ | 在 `analyze.py` 入口处添加 `sys.stdout.reconfigure(encoding="utf-8")` 强制 UTF-8 输出。 | ✅ 已关闭 |

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
