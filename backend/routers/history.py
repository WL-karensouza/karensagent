"""推送历史 API"""

from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from database import get_db, get_push_history
from models import PushHistory

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/list")
def list_history(
    limit: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows = get_push_history(limit=limit)
    return {"code": 0, "data": rows}


@router.get("/detail/{push_id}")
def history_detail(push_id: int, db: Session = Depends(get_db)):
    row = db.query(PushHistory).filter(PushHistory.id == push_id).first()
    if not row:
        return {"code": 1, "message": "记录不存在"}

    d = {}
    for col in row.__table__.columns:
        val = getattr(row, col.key)
        d[col.key] = str(val) if val is not None else ""
    return {"code": 0, "data": d}
