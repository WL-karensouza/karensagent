"""飞书 Webhook 配置管理 API"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/config", tags=["config"])


# ── 请求体模型 ──

class WebhookBody(BaseModel):
    url: str


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
