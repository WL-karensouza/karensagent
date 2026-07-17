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
                # 使用直接赋值而非 setdefault，确保 .env 优先于系统环境变量
                os.environ[key.strip()] = value.strip().strip("\"'")


_load_env()

# ── 数据库（本地开发默认 SQLite，生产环境设 MySQL） ──
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # 本地开发：sqlite:///karens_agent.db
    # 生产环境：mysql+pymysql://root:password@localhost:3306/karens_agent
    "sqlite:///karens_agent.db",
)

# ── 飞书 ──
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")

# ── Claude API（后期启用） ──
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── 关键词配置（纯关键词列表，无权重，用于 AI 资讯过滤） ──
DEFAULT_KEYWORDS = [
    "agent", "llm", "mcp", "claude", "langgraph", "autogen",
    "crewai", "tool-use", "function-calling", "multi-agent",
    "rag", "workflow", "openai", "skill", "chain-of-thought",
    "reasoning", "fine-tuning", "alignment", "transformer",
    "deepseek", "gemini", "llama", "embedding", "retrieval",
]

# ── 推送配置 ──
PUSH_TIME = os.getenv("PUSH_TIME", "09:00")  # 每天推送时间
MARKET_REPORT_TIME = os.getenv("MARKET_REPORT_TIME", "15:30")  # 每日大盘分析时间
WEEKLY_TOP_N = int(os.getenv("WEEKLY_TOP_N", "10"))  # 周榜数量
MONTHLY_TOP_N = int(os.getenv("MONTHLY_TOP_N", "30"))  # 月榜数量
NEWS_TOP_N = int(os.getenv("NEWS_TOP_N", "5"))  # 资讯推送数量

# ── HTTP 请求头（模拟浏览器，防 403） ──
GITHUB_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
}
