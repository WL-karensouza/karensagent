"""AI 前沿咨询 Agent —— 数据库操作"""

import json
from datetime import date, datetime, timedelta

from sqlalchemy import func
from database import SessionLocal, _model_to_dict
from .models import AiNewsReport


# ═══════════════════════════════════════════
# AI 新闻报告
# ═══════════════════════════════════════════

def save_ai_news_report(
    report_type: str,
    search_query: str,
    search_results: str,
    summary: str,
    source_urls: list[str] | None = None,
) -> int:
    """保存一份 AI 新闻报告，返回报告 ID"""
    db = SessionLocal()
    try:
        obj = AiNewsReport(
            report_type=report_type,
            search_query=search_query,
            search_results=search_results,
            summary=summary,
            source_urls=json.dumps(source_urls or [], ensure_ascii=False),
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        report_id = obj.id
        print(f"[db] save_ai_news_report: id={report_id} type={report_type}")
        return report_id
    finally:
        db.close()


def get_ai_news_reports(report_type: str = "", limit: int = 30) -> list[dict]:
    """获取 AI 新闻报告列表（按创建时间倒序）"""
    db = SessionLocal()
    try:
        query = db.query(AiNewsReport)
        if report_type:
            query = query.filter(AiNewsReport.report_type == report_type)
        rows = (
            query.order_by(AiNewsReport.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_model_to_dict(r) for r in rows]
    finally:
        db.close()


def get_ai_news_report_by_id(report_id: int) -> dict | None:
    """按 ID 获取单份报告"""
    db = SessionLocal()
    try:
        row = db.query(AiNewsReport).filter(AiNewsReport.id == report_id).first()
        if row is None:
            return None
        return _model_to_dict(row)
    finally:
        db.close()


# ═══════════════════════════════════════════
# 推送历史（从 backend/models.py 复用 PushHistory 模型）
# ═══════════════════════════════════════════

def save_push_history(
    platform: str = "feishu",
    content_type: str = "daily",
    content: str = "",
    news_count: int = 0,
    status: str = "sent",
):
    """记录推送历史"""
    from models import PushHistory

    db = SessionLocal()
    try:
        db.add(PushHistory(
            platform=platform,
            content_type=content_type,
            content=content,
            news_count=news_count,
            status=status,
        ))
        db.commit()
        print(f"[db] save_push_history: platform={platform} news={news_count}")
    finally:
        db.close()


def get_push_history(limit: int = 30) -> list[dict]:
    """获取推送历史列表"""
    from models import PushHistory

    db = SessionLocal()
    try:
        rows = (
            db.query(PushHistory)
            .order_by(PushHistory.push_time.desc())
            .limit(limit)
            .all()
        )
        return [_model_to_dict(r) for r in rows]
    finally:
        db.close()


def get_push_history_by_id(push_id: int) -> dict | None:
    """按 ID 获取单条推送记录"""
    from models import PushHistory

    db = SessionLocal()
    try:
        row = db.query(PushHistory).filter(PushHistory.id == push_id).first()
        if row is None:
            return None
        return _model_to_dict(row)
    finally:
        db.close()


# ═══════════════════════════════════════════
# 仪表盘统计
# ═══════════════════════════════════════════

def get_dashboard_stats() -> dict:
    """仪表盘统计"""
    from models import PushHistory

    db = SessionLocal()
    try:
        today = date.today()
        week_ago = today - timedelta(days=7)

        # 今日报告数
        today_daily = db.query(func.count(AiNewsReport.id)).filter(
            AiNewsReport.report_type == "daily",
            func.date(AiNewsReport.created_at) == today,
        ).scalar() or 0

        today_weekly = db.query(func.count(AiNewsReport.id)).filter(
            AiNewsReport.report_type == "weekly",
            func.date(AiNewsReport.created_at) == today,
        ).scalar() or 0

        # 近一周报告总数
        week_reports = db.query(func.count(AiNewsReport.id)).filter(
            AiNewsReport.created_at >= week_ago,
        ).scalar() or 0

        # 今日推送次数
        today_pushes = db.query(func.count(PushHistory.id)).filter(
            func.date(PushHistory.push_time) == today,
        ).scalar() or 0

        # 上次推送时间
        last_push = db.query(PushHistory.push_time).order_by(
            PushHistory.push_time.desc()
        ).first()
        last_push_str = last_push[0].strftime("%Y-%m-%d %H:%M") if last_push else None

        return {
            "today_daily": today_daily,
            "today_weekly": today_weekly,
            "week_reports": week_reports,
            "today_pushes": today_pushes,
            "last_push": last_push_str,
        }
    finally:
        db.close()


