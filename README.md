# 🤖 Karens Agent

AI 驱动的智能信息中枢：AI 前沿咨询速递 + 专业级个股投研分析。

## 功能

- 🤖 **AI 前沿速递**：LangGraph 编排（understand → search → summarize），Tavily 搜索 + DeepSeek 中文摘要，每日自动推送"昨日 AI 新闻 + 近一周 AI 新闻"到飞书
- 📈 **个股投研分析**：接入同花顺 iFinD 金融数据终端，10 维度深度采集 + DeepSeek AI 综合分析，生成专业级投研报告
- 🔔 **定时推送**：每天早上 9:00 推送到飞书
- 🎛️ **可视化后台**：仪表盘、推送历史、配置管理、自选股管理

## 版本历程

| 版本 | 更新时间 | 内容 | 说明 |
|------|----------|------|------|
| V1 | 2026-06-03 | GitHub 热榜爬虫 Agent | 每日抓取 GitHub Trending 与 AI 前沿资讯，定时推送到飞书 |
| V1.1 | 2026-06-08 | 股票分析 Agent | 通过多个免费 API 拼凑获取行情数据，交由 LLM 分析，生成分析报告 |
| V1.2 | 2026-06-12 | iFinD 数据源重构 | 全面迁移至同花顺 iFinD 金融终端，单数据源覆盖 10 大维度，SSE 流式生成专业投研报告 |
| V1.3 | 2026-06-13 | 技术指标自算 + 东方财富日K数据源 | 绕开 iFinD MA/MACD/BOLL 不拆分子指标的限制，基于前复权日K OHLCV 自行计算 17 个子指标；引入东方财富免费 HTTP API 作为日K数据源（前复权）|
| V2.0 | 2026-06-26 | LangGraph + Tavily 全量重构 | 取消 GitHub 热榜，聚焦 AI 前沿新闻，LangGraph 3 节点工作流，前端热榜 UI 全清，新增 AI 新闻仪表盘 |
| V2.1 | 2026-07-05 | Home 页 3D 办公室场景 | 取消原 Home 页 UI，替换为 3D 办公室场景 |

## 快速开始

```bash
cd backend
pip install -r requirements.txt

# 编辑 .env，填入企业微信/飞书 Webhook 及 iFinD 配置
vim .env

# 启动
python main.py
```

浏览器打开 http://localhost:8900

## 测试

```bash
cd backend
python -m pytest tests/ -v
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
│   ├── ai_news_agent/    # AI 前沿咨询 Agent（V3.0）
│   │   ├── graph.py      # LangGraph 3 节点工作流（understand → search → summarize）
│   │   ├── prompts.py    # Prompt 模板（搜索意图 + understand + 摘要）
│   │   ├── scheduler.py  # APScheduler 定时任务（每天 09:00）
│   │   ├── feishu.py     # 飞书卡片构建 + 推送
│   │   ├── database.py   # ai_news_reports + push_history CRUD
│   │   ├── models.py     # ORM: AiNewsReport
│   │   └── routers/      # API 路由（dashboard / history / trigger）
│   ├── stock_agent/      # 股票分析核心模块
│   │   ├── analyze.py    # DeepSeek 分析引擎 + 飞书推送
│   │   ├── render.py     # Markdown 报告渲染
│   │   ├── datasources/  # 免费 HTTP 数据源（东方财富等）
│   │   │   └── eastmoney.py  # 公司名称兜底 + 前复权日K线 OHLCV
│   │   └── skill/        # iFinD SKILL 驱动架构
│   │       ├── __init__.py   # call_skill 封装 + normalize_stock_code
│   │       ├── indicators.py # 技术指标自算（MA/MACD/BOLL/RSI/KDJ）
│   │       └── report.py     # 10 维度编排、SSE 调度、Markdown 汇总
│   ├── routers/          # API 路由（config_api / stock_api）
│   └── tests/            # 测试用例
├── frontend/             # Vue 3 前端
│   └── src/
│       ├── api/          # API 接口层
│       ├── stores/       # Pinia 状态管理
│       ├── components/   # 公共组件（TopNav / SelectPicker / 报告模块）
│       └── views/agent/  # Agent 页面（AI 新闻仪表盘/推送历史 + 股票仪表盘/历史/配置/详情）
└── deploy.sh             # 一键部署脚本
```
