"""配置管理 API —— 关键词、飞书 Webhook"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import Keyword

router = APIRouter(prefix="/api/config", tags=["config"])


# ── 请求体模型 ──

class KeywordItem(BaseModel):
    keyword: str
    score: int = 0
    enabled: int = 1


class KeywordUpdate(BaseModel):
    score: int = None
    enabled: int = None


class WebhookBody(BaseModel):
    url: str


# ── 关键词管理 ──

@router.get("/keywords")
def list_keywords(db: Session = Depends(get_db)):
    rows = db.query(Keyword).order_by(Keyword.score.desc()).all()
    data = []
    for r in rows:
        data.append({
            "id": r.id,
            "keyword": r.keyword,
            "score": r.score,
            "enabled": r.enabled,
        })
    return {"code": 0, "data": data}


@router.post("/keywords")
def add_keyword(item: KeywordItem, db: Session = Depends(get_db)):
    exists = db.query(Keyword).filter(Keyword.keyword == item.keyword).first()
    if exists:
        return {"code": 1, "message": f"关键词 [{item.keyword}] 已存在"}

    db.add(Keyword(keyword=item.keyword, score=item.score, enabled=item.enabled))
    db.commit()
    return {"code": 0, "message": f"关键词 [{item.keyword}] 已添加"}


@router.put("/keywords/{keyword}")
def update_keyword(keyword: str, item: KeywordUpdate, db: Session = Depends(get_db)):
    row = db.query(Keyword).filter(Keyword.keyword == keyword).first()
    if not row:
        return {"code": 1, "message": f"关键词 [{keyword}] 不存在"}

    if item.score is not None:
        row.score = item.score
    if item.enabled is not None:
        row.enabled = item.enabled
    db.commit()
    return {"code": 0, "message": f"关键词 [{keyword}] 已更新"}


@router.delete("/keywords/{keyword}")
def delete_keyword(keyword: str, db: Session = Depends(get_db)):
    db.query(Keyword).filter(Keyword.keyword == keyword).delete()
    db.commit()
    return {"code": 0, "message": f"关键词 [{keyword}] 已删除"}


# ── 飞书 Webhook 配置 ──

@router.get("/webhook")
def get_webhook():
    from config import FEISHU_WEBHOOK_URL

    def mask(url):
        if not url:
            return ""
        return url[:40] + "..." if len(url) > 40 else url

    return {
        "code": 0,
        "data": {
            "url": mask(FEISHU_WEBHOOK_URL),
            "configured": bool(FEISHU_WEBHOOK_URL),
        },
    }


@router.put("/webhook")
def update_webhook(body: WebhookBody):
    import os
    import config

    url = body.url
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    found = False
    for i, line in enumerate(lines):
        if line.startswith("FEISHU_WEBHOOK_URL="):
            lines[i] = f"FEISHU_WEBHOOK_URL={url}\n"
            found = True
            break

    if not found:
        lines.append(f"\nFEISHU_WEBHOOK_URL={url}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    config.FEISHU_WEBHOOK_URL = url
    return {"code": 0, "message": "飞书 Webhook 已更新"}
