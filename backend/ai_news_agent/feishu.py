"""AI 前沿咨询 Agent —— 飞书卡片构建与发送"""

from datetime import datetime
import httpx
from config import FEISHU_WEBHOOK_URL

# 飞书卡片内容上限 100KB，单个 lark_md 块安全上限约 40KB，留足余量
_MAX_CARD_LEN = 15000


def build_ai_news_card(daily_summary: str, weekly_summary: str) -> dict:
    """构建 AI 新闻飞书交互式卡片

    Args:
        daily_summary: 昨日 AI 新闻摘要
        weekly_summary: 近一周 AI 新闻摘要

    Returns:
        飞书卡片 JSON dict
    """
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 飞书卡片内容上限 100KB，单个 lark_md 块实测安全上限约 40KB
    MAX_LEN = 15000

    def _safe(s: str, label: str) -> str:
        if len(s) <= MAX_LEN:
            return s
        print(f"[feishu] ⚠️ {label} 内容过长 ({len(s)} 字符)，截断至 {MAX_LEN}")
        return s[:MAX_LEN] + "\n\n...（内容过长已截断，完整报告请查看后台历史）"

    daily_safe = _safe(daily_summary, "日报")
    weekly_safe = _safe(weekly_summary, "周报")

    card = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🤖 AI 前沿速递 | {today_str}",
                },
                "template": "blue",
            },
            "elements": [
                # ── 昨日 AI 新闻 ──
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "### 📅 昨日 AI 新闻\n\n" + daily_safe,
                    },
                },
                {"tag": "hr"},
                # ── 近一周 AI 新闻 ──
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "### 📊 近一周 AI 新闻\n\n" + weekly_safe,
                    },
                },
                {"tag": "hr"},
                # ── 底部注脚 ──
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "Karens Agent · AI 前沿 Agent 自动生成 · 每天 09:00 推送",
                        }
                    ],
                },
            ],
        },
    }

    return card


def _post_card(card: dict) -> bool:
    """发送飞书卡片（内部通用发送逻辑）

    Returns:
        True 表示发送成功
    """
    if not FEISHU_WEBHOOK_URL:
        print("[feishu] ⚠️ FEISHU_WEBHOOK_URL 未配置，跳过推送")
        return False

    try:
        resp = httpx.post(
            FEISHU_WEBHOOK_URL,
            json=card,
            timeout=30,
            headers={"Content-Type": "application/json"},
        )
        data = resp.json()
        ok = data.get("code") == 0 or data.get("StatusCode") == 0
        if ok:
            print("[feishu] ✅ 卡片推送成功")
        else:
            print(f"[feishu] ❌ 推送失败: {data}")
        return ok
    except Exception as e:
        print(f"[feishu] ❌ 推送异常: {e}")
        return False


def send_feishu_card(card: dict) -> bool:
    """发送飞书交互式卡片消息"""
    return _post_card(card)


def send_error_notification(title: str, detail: str) -> bool:
    """发送飞书错误告警卡片（红色标题）"""
    card = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"⚠️ {title}"},
                "template": "red",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": detail},
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"Karens Agent · {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        }
                    ],
                },
            ],
        },
    }
    return _post_card(card)
