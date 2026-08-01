"""配置管理 —— 所有可配置项集中此文件"""

import os


def _load_env(path=None):
    """加载 .env 文件（不依赖 python-dotenv）"""
    if path is None:
        path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            if key and value:
                os.environ[key.strip()] = value.strip().strip("\"'")


_load_env()

# ── 数据库（本地开发默认 SQLite，生产环境设 MySQL） ──
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///karens_agent.db",
)

# ── 飞书 ──
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")

# ── Claude API（后期启用） ──
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── 推送配置 ──
PUSH_TIME = os.getenv("PUSH_TIME", "09:00")  # 每天推送时间

# ── LLM 配置（AI 新闻摘要） ──
# deepseek-reasoner/deepseek-chat 均已下架，统一使用 deepseek-v4-flash。
# v4-flash 默认开启思考模式；思考开关由各调用方显式声明：
#   analyze.py 开思考（extra_body={"thinking":{"type":"enabled"}}）
#   graph.py 关思考（model_kwargs={"thinking":{"type":"disabled"}}）让 temperature 生效
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "deepseek-v4-flash")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")

# ── Tavily 搜索 API ──
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
