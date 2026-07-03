"""关键词过滤器 —— 仓库纯 Stars 排名，资讯按关键词布尔匹配"""

from database import SessionLocal
from models import Keyword


def get_active_keywords() -> list[str]:
    """从数据库获取所有启用的关键词（纯列表，无权重）"""
    db = SessionLocal()
    try:
        rows = db.query(Keyword).filter(Keyword.enabled == 1).all()
        return [r.keyword for r in rows]
    finally:
        db.close()


def filter_repos(repos: list[dict], top_n: int = 10) -> list[dict]:
    """
    仓库按 stars 纯排名（不应用关键词评分）
    排序：最近 stars 多 → 少
    """
    sorted_repos = sorted(
        repos,
        key=lambda r: r.get("stars_today", 0),
        reverse=True,
    )
    return sorted_repos[:top_n]


def filter_news(news_items: list[dict], top_n: int = 5) -> list[dict]:
    """
    资讯按关键词布尔匹配过滤
    标题或摘要命中任意关键词 → 保留，按来源热度排序
    """
    keywords = get_active_keywords()

    matched = []
    for n in news_items:
        text = (n.get("title", "") + " " + n.get("summary", "")).lower()
        if any(kw in text for kw in keywords):
            matched.append(n)

    # 按原热度排序（HN 有 score，ArXiv/PwC 按时间自然序）
    matched.sort(key=lambda n: n.get("score", 0), reverse=True)
    return matched[:top_n]
