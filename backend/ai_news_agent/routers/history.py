"""推送历史 API"""

from fastapi import APIRouter
from ..database import get_push_history, get_push_history_by_id

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/list")
def history_list(limit: int = 30):
    """获取推送历史列表（按时间倒序）"""
    data = get_push_history(limit)
    return {"code": 0, "data": data}


@router.get("/detail/{push_id}")
def history_detail(push_id: int):
    """获取单条推送详情（含完整飞书卡片 JSON）"""
    data = get_push_history_by_id(push_id)
    if data is None:
        return {"code": 404, "message": "记录不存在"}
    return {"code": 0, "data": data}
