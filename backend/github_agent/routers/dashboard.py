"""仪表盘 API —— 统计概览数据"""

from fastapi import APIRouter
from database import get_dashboard_stats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def dashboard_stats():
    """
    仪表盘统计卡片数据

    Returns:
        today_repos: 今日抓取仓库数
        week_unique_repos: 本周不重复仓库数
        week_news: 本周 AI 资讯数
        last_push: 上次推送时间
    """
    return {"code": 0, "data": get_dashboard_stats()}
