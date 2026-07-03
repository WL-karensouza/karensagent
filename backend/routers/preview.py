"""内容预览 API —— 按日期查看 Trend 和资讯"""

from datetime import date, datetime
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import DailyTrend, AiNews

router = APIRouter(prefix="/api/preview", tags=["preview"])


@router.get("/trends")
def preview_trends(
    fetch_date: str = Query(None, description="日期 YYYY-MM-DD，默认今天"),
    source: str = Query("weekly", description="weekly / monthly"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if not fetch_date:
        fetch_date = date.today().isoformat()

    rows = (
        db.query(DailyTrend)
        .filter(DailyTrend.fetch_date == fetch_date, DailyTrend.source == source)
        .order_by(DailyTrend.stars_today.desc())
        .limit(limit)
        .all()
    )
    data = []
    for r in rows:
        d = {}
        for col in r.__table__.columns:
            val = getattr(r, col.key)
            d[col.key] = str(val) if val is not None else ""
        data.append(d)
    return {"code": 0, "data": data}


@router.get("/news")
def preview_news(
    fetch_date: str = Query(None, description="日期 YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if not fetch_date:
        fetch_date = date.today().isoformat()

    rows = (
        db.query(AiNews)
        .filter(AiNews.fetch_date == fetch_date)
        .order_by(AiNews.score.desc())
        .limit(limit)
        .all()
    )
    data = []
    for r in rows:
        d = {}
        for col in r.__table__.columns:
            val = getattr(r, col.key)
            d[col.key] = str(val) if val is not None else ""
        data.append(d)
    return {"code": 0, "data": data}


@router.get("/dates")
def available_dates(db: Session = Depends(get_db)):
    """获取有数据的所有日期列表"""
    trend_dates = {r[0].isoformat() for r in db.query(DailyTrend.fetch_date).distinct().all()}
    news_dates = {r[0].isoformat() for r in db.query(AiNews.fetch_date).distinct().all()}
    all_dates = sorted(trend_dates | news_dates, reverse=True)
    return {"code": 0, "data": all_dates[:90]}
