"""仪表盘 API —— 统计概览数据"""

from fastapi import APIRouter
from ..database import get_dashboard_stats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def dashboard_stats():
    """仪表盘统计卡片数据

    Returns:
        today_daily: 今日日报数
        today_weekly: 今日周报数
        week_reports: 近一周报告总数
        today_pushes: 今日推送次数
        last_push: 上次推送时间
    """
    return {"code": 0, "data": get_dashboard_stats()}
