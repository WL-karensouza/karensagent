"""手动触发 API —— 支持手动执行 AI 新闻抓取+推送"""

import threading
import uuid
from datetime import datetime

from fastapi import APIRouter
from ..scheduler import daily_ai_news_push

router = APIRouter(prefix="/api/trigger", tags=["trigger"])

# 内存中的任务结果存储（TTL 1 小时自动清理）
_task_results: dict[str, dict] = {}


@router.post("/full")
def trigger_full():
    """手动触发一次完整的 AI 新闻抓取+推送流程（后台执行）"""
    task_id = str(uuid.uuid4())[:8]
    _task_results[task_id] = {
        "status": "running",
        "message": "任务已启动",
        "started_at": datetime.now().isoformat(),
    }

    thread = threading.Thread(
        target=_run_full,
        args=(task_id,),
        daemon=True,
    )
    thread.start()

    return {"code": 0, "task_id": task_id, "message": "后台任务已启动"}


@router.get("/result/{task_id}")
def get_task_result(task_id: str):
    """查询手动触发任务的结果"""
    result = _task_results.get(task_id)
    if result is None:
        return {"code": 404, "message": "任务不存在或已过期"}
    return {"code": 0, "data": result}


def _run_full(task_id: str):
    """后台执行抓取+推送"""
    try:
        daily_ai_news_push()
        _task_results[task_id] = {
            "status": "done",
            "message": "AI 新闻抓取+推送完成",
            "finished_at": datetime.now().isoformat(),
        }
    except Exception as e:
        _task_results[task_id] = {
            "status": "failed",
            "message": f"执行失败: {str(e)}",
            "finished_at": datetime.now().isoformat(),
        }


# ── 定期清理过期任务结果 ──
def _cleanup_expired_tasks():
    """清理 1 小时前的任务结果"""
    now = datetime.now()
    expired = [
        tid for tid, r in _task_results.items()
        if r.get("status") in ("done", "failed")
        and (now - datetime.fromisoformat(r.get("finished_at", r.get("started_at")))).seconds > 3600
    ]
    for tid in expired:
        del _task_results[tid]
