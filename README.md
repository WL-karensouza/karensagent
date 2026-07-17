# 🤖 Karens Agent

每日自动推送 GitHub 热榜和 AI 前沿资讯到企业微信/飞书。

## 功能

- 🔥 **GitHub Trending**：每日抓取 Trending 页面，聚焦 Agent/Skill/MCP 等关键词
- 📚 **AI 前沿**：Hacker News 热帖 + ArXiv CS.AI 最新论文
- 🔔 **定时推送**：每天早上 9:00 推送到企业微信/飞书
- 🎛️ **可视化后台**：仪表盘、内容预览、推送历史、配置管理

## 版本进度

| 版本 | 内容 | 说明 |
|------|------|------|
| V1 | GitHub 热榜爬虫 Agent | 每日抓取 GitHub Trending 与 AI 前沿资讯，定时推送到飞书 |
| V1.1 | 股票分析 Agent | 通过多个免费 API 拼凑获取真实行情数据，交由 LLM 分析，最终生成分析报告 |

## 快速开始

```bash
cd backend
pip install -r requirements.txt

# 编辑 .env，填入你的企业微信 Webhook URL
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
├── backend/           # FastAPI 后端
│   ├── main.py        # 入口
│   ├── config.py      # 配置
│   ├── database.py    # 数据库操作
│   ├── scheduler.py   # 定时任务
│   ├── notifier.py    # 消息推送
│   ├── fetchers/      # 数据抓取器
│   ├── filters/       # 关键词过滤器
│   ├── formatters/    # 格式化器
│   ├── routers/       # API 路由
│   └── tests/         # 测试
├── frontend/          # Vue3 前端（开发中）
└── deploy.sh          # 部署脚本
```
