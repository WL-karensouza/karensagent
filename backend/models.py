"""SQLAlchemy ORM 模型定义"""

from datetime import date
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, func, UniqueConstraint
)
from database import Base


class DailyTrend(Base):
    """GitHub Trending 日榜原始数据"""
    __tablename__ = "daily_trends"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_name = Column(String(255), nullable=False, comment="仓库全名 e.g. anthropics/skills-collection")
    repo_url = Column(String(512), nullable=False, comment="仓库链接")
    description = Column(Text, default="", comment="仓库描述")
    language = Column(String(50), default="", comment="编程语言")
    stars_today = Column(Integer, default=0, comment="今日新增 stars")
    total_stars = Column(Integer, default=0, comment="总 stars")
    rank = Column(Integer, default=0, comment="当日排名")
    source = Column(String(20), default="daily", comment="数据来源 daily/weekly")
    fetch_date = Column(Date, nullable=False, comment="抓取日期")

    __table_args__ = (
        UniqueConstraint("repo_name", "fetch_date", "source", name="uq_daily_repo_date_source"),
        {"comment": "GitHub Trending 每日抓取数据"},
    )


class AiNews(Base):
    """AI 前沿资讯"""
    __tablename__ = "ai_news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False, comment="标题")
    url = Column(String(500), nullable=False, comment="链接")
    source = Column(String(50), nullable=False, comment="来源 hackernews/arxiv")
    score = Column(Integer, default=0, comment="热度分数")
    summary = Column(Text, default="", comment="摘要")
    fetch_date = Column(Date, nullable=False, comment="抓取日期")
    is_pushed = Column(Integer, default=0, comment="是否已推送 1/0")

    __table_args__ = (
        UniqueConstraint("url", "fetch_date", name="uq_news_url_date"),
        {"comment": "AI 前沿资讯"},
    )


class PushHistory(Base):
    """推送历史记录"""
    __tablename__ = "push_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    push_time = Column(DateTime, server_default=func.now(), comment="推送时间")
    platform = Column(String(20), nullable=False, comment="推送平台 wecom/feishu")
    content_type = Column(String(20), nullable=False, comment="内容类型 daily/weekly/monthly")
    content = Column(Text, nullable=False, comment="完整推送内容")
    repo_count = Column(Integer, default=0, comment="包含仓库数")
    news_count = Column(Integer, default=0, comment="包含资讯数")
    status = Column(String(20), default="sent", comment="状态 sent/failed")

    __table_args__ = (
        {"comment": "推送历史"},
    )


class Keyword(Base):
    """关键词配置（可热更新）"""
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(100), nullable=False, unique=True, comment="关键词")
    score = Column(Integer, default=5, comment="权重分数")
    enabled = Column(Integer, default=1, comment="是否启用 1/0")

    __table_args__ = (
        {"comment": "关键词过滤配置"},
    )
