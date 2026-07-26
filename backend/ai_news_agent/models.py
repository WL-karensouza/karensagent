"""AI 前沿咨询 Agent —— ORM 模型定义"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from database import Base


class AiNewsReport(Base):
    """AI 新闻报告（每次搜索+摘要的记录）"""
    __tablename__ = "ai_news_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(20), nullable=False, comment="报告类型 daily/weekly")
    search_query = Column(String(500), default="", comment="搜索查询词")
    search_results = Column(Text, default="", comment="Tavily 原始搜索结果")
    summary = Column(Text, default="", comment="LLM 整理的中文摘要")
    source_urls = Column(Text, default="", comment="来源 URL（JSON 数组）")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    __table_args__ = (
        {"comment": "AI 新闻日报/周报"},
    )
