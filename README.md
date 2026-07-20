# 🤖 Karens Agent

AI 驱动的智能信息中枢：GitHub 热榜追踪 + 专业级个股投研分析。

## 功能

- 🔥 **GitHub Trending**：每日抓取 Trending 页面，聚焦 Agent/Skill/MCP 等关键词
- 📚 **AI 前沿资讯**：Hacker News 热帖 + ArXiv CS.AI 最新论文
- 📈 **个股投研分析**：接入同花顺 iFinD 金融数据终端，10 维度深度采集 + DeepSeek AI 综合分析，生成专业级投研报告
- 🔔 **定时推送**：每天早上 9:00 推送到企业微信/飞书
- 🎛️ **可视化后台**：仪表盘、内容预览、推送历史、配置管理、自选股管理

## 版本历程

| 版本 | 内容 | 说明 |
|------|------|------|
| V1 | GitHub 热榜爬虫 Agent | 每日抓取 GitHub Trending 与 AI 前沿资讯，定时推送到飞书 |
| V1.1 | 股票分析 Agent | 通过多个免费 API 拼凑获取行情数据，交由 LLM 分析，生成分析报告 |
| V2 | iFinD 数据源重构 | 全面迁移至同花顺 iFinD 金融终端，单数据源覆盖 10 大维度，SSE 流式生成专业投研报告 |
| V2.1 | 技术指标自算 + 东方财富日K数据源 | 绕开 iFinD MA/MACD/BOLL 不拆分子指标的限制，基于前复权日K OHLCV 自行计算 17 个子指标；引入东方财富免费 HTTP API 作为日K数据源（前复权）|

## V2 重大更新

V2 是股票分析 Agent 的一次底层重构，核心变化：

- **数据源升级**：从多个免费 API 拼凑，迁移至同花顺 iFinD 专业金融数据终端，数据覆盖更全、更准、更稳定
- **10 维度深度覆盖**：实时行情 → 基本信息与估值 → 近期走势 → 财务数据 → 股东结构 → 风险评估 → ESG 评级 → 重大事件 → 近期新闻 → 公司公告
- **SSE 流式架构**：后端边采集边推送，前端实时展示进度，每个维度的状态一目了然
- **DeepSeek AI 综合分析**：10 维数据聚合后交由 DeepSeek 生成结构化投研报告，含综合评分、多空判断、信号归因，内容更专业、更详尽
- **自选股体系**：支持自选股管理、轮播浏览、一键生成投研报告，报告生成后自选股卡片自动显示评分摘要
- **飞书自动推送**：投研报告完成后可选自动推送到飞书，也可在历史报告中手动推送

## V2.1 技术指标增强

V2.1 解决了 iFinD `get_stock_performance` 不拆分技术指标子项的核心痛点：

- **根因**：iFinD 将 MA5/MA10/MA20/MA30/MA60 聚合为单一列 `MA简单移动平均`，MACD 子项（DIF/DEA/柱值）和 BOLL 三轨（上/中/下）需分别 query，10+ 次调用才能拿到全量子指标，免费版 2 QPS 不堪重负
- **方案**：取 OHLCV 原始数据自行计算全部技术指标，仅 1 次 API 调用覆盖 17 个子指标
- **东方财富日K数据源**：引入东方财富免费 HTTP API (`push2his.eastmoney.com`) 获取前复权日K线 OHLCV，与同花顺 APP 日K 数据完全一致，零新依赖（复用已有 `requests`）
- **指标覆盖**：MA(5/10/20/30/60) 含收盘价偏离度、MACD(12/26/9) DIF/DEA/BAR、BOLL(20日 2σ) 上/中/下轨+带宽、RSI(6/12/24) 含超买超卖标注、KDJ(9日) K/D/J 含超买超卖标注
- **数据新鲜度**：从 iFinD 滞后 1 个交易日 → 当日实时（东方财富盘中更新）
- **兜底机制**：东方财富获取失败时自动 fallback 到 iFinD Markdown 表格解析，不中断报告生成

## 快速开始

```bash
cd backend
pip install -r requirements.txt

# 编辑 .env，填入企业微信/飞书 Webhook 及 iFinD 配置
cp .env.example .env
vim .env

# 启动
python main.py
```

浏览器打开 http://localhost:8900

## 测试

```bash
cd backend
python tests/test_core.py
```

## 部署到云服务器

```bash
# 一键部署
bash deploy.sh

# 或手动执行
cd backend
uvicorn main:app --host 0.0.0.0 --port 8900
```

## 项目结构

```
karensAgent/
├── backend/              # FastAPI 后端
│   ├── main.py           # 应用入口
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库操作
│   ├── models.py         # ORM 模型
│   ├── scheduler.py      # 定时任务调度
│   ├── notifier.py       # 企业微信/飞书推送
│   ├── fetchers/         # GitHub / Hacker News / ArXiv 抓取
│   ├── filters/          # 关键词过滤器
│   ├── formatters/       # 消息格式化
│   ├── routers/          # API 路由（dashboard / preview / history / trigger / stock_api）
│   ├── stock_agent/      # 股票分析核心模块
│   │   ├── analyze.py    # DeepSeek 分析引擎 + 飞书推送
│   │   ├── render.py     # Markdown 报告渲染
│   │   ├── datasources/  # 免费 HTTP 数据源（东方财富等）
│   │   │   └── eastmoney.py  # 公司名称兜底 + 前复权日K线 OHLCV
│   │   └── skill/        # iFinD SKILL 驱动架构
│   │       ├── __init__.py   # call_skill 封装 + normalize_stock_code
│   │       ├── indicators.py # 技术指标自算（MA/MACD/BOLL/RSI/KDJ）
│   │       └── report.py     # 10 维度编排、SSE 调度、Markdown 汇总
│   └── tests/            # 测试用例
├── frontend/             # Vue 3 前端
│   └── src/
│       ├── api/          # API 接口层
│       ├── stores/       # Pinia 状态管理
│       ├── components/   # 公共组件（TopNav / SelectPicker / 报告模块）
│       └── views/agent/  # Agent 页面（仪表盘 / 历史报告 / 配置管理 / 报告详情）
└── deploy.sh             # 一键部署脚本
```
