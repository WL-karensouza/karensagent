"""SQLAlchemy ORM 模型定义"""

from datetime import date
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, func, UniqueConstraint
)
from database import Base


class PushHistory(Base):
    """推送历史记录"""
    __tablename__ = "push_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    push_time = Column(DateTime, server_default=func.now(), comment="推送时间")
    platform = Column(String(20), nullable=False, comment="推送平台 wecom/feishu")
    content_type = Column(String(20), nullable=False, comment="内容类型 daily")
    content = Column(Text, nullable=False, comment="完整推送内容")
    news_count = Column(Integer, default=0, comment="包含资讯数")
    status = Column(String(20), default="sent", comment="状态 sent/failed")

    __table_args__ = (
        {"comment": "推送历史"},
    )


class StockReport(Base):
    """个股分析报告"""
    __tablename__ = "stock_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, comment="股票代码")
    stock_name = Column(String(50), default="", comment="股票名称")
    score = Column(Integer, default=0, comment="综合评分 0-100")
    decision = Column(String(10), default="", comment="综合判断 看多/震荡/看空")
    summary = Column(Text, default="", comment="综合评估摘要")
    report_json = Column(Text, nullable=False, comment="完整报告 JSON")
    markdown = Column(Text, default="", comment="Markdown 格式报告")
    token_used = Column(Integer, default=0, comment="消耗 Token 数")
    debate_stats = Column(Text, nullable=True, comment="双模型辩论过程 JSON（标准分析/降级时为 null）")
    created_at = Column(DateTime, server_default=func.now(), comment="生成时间")

    __table_args__ = (
        {"comment": "个股分析报告"},
    )


class StockWatchlist(Base):
    """自选股列表"""
    __tablename__ = "stock_watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, unique=True, comment="股票代码")
    stock_name = Column(String(50), default="", comment="股票名称")
    notes = Column(String(500), default="", comment="备注")
    enabled = Column(Integer, default=1, comment="是否启用 1/0")
    sort_order = Column(Integer, default=0, comment="排序权重")
    added_at = Column(DateTime, server_default=func.now(), comment="添加时间")

    __table_args__ = (
        {"comment": "自选股列表"},
    )


class ChatSession(Base):
    """AI 问答会话（绑定股票共享，每只股票一个活跃会话）"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, unique=True, comment="股票代码")
    stock_name = Column(String(64), default="", comment="股票名称")
    report_id = Column(Integer, nullable=True, comment="最近锚定的报告 ID")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        {"comment": "AI 问答会话"},
    )


class ChatMessage(Base):
    """AI 问答消息"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, nullable=False, comment="所属会话 ID")
    role = Column(String(16), nullable=False, comment="user / assistant")
    content = Column(Text, nullable=False, comment="问题或回答")
    tool_calls = Column(Text, nullable=True, comment="该轮工具调用记录 JSON 数组")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    __table_args__ = (
        {"comment": "AI 问答消息"},
    )
