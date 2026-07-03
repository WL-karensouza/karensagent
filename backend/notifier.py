"""消息推送器 —— 飞书卡片"""

import httpx
from config import FEISHU_WEBHOOK_URL


def send_feishu_card(card: dict) -> bool:
    """发送飞书卡片消息"""
    if not FEISHU_WEBHOOK_URL:
        print("[feishu] Webhook URL 未配置，跳过推送")
        return False

    try:
        resp = httpx.post(FEISHU_WEBHOOK_URL, json=card, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            print("[feishu] [OK] 推送成功")
            return True
        else:
            print(f"[feishu] [FAIL] 推送失败: {result}")
            return False
    except Exception as e:
        print(f"[feishu] [FAIL] 请求异常: {e}")
        return False


def send_error_notification(title: str, detail: str) -> bool:
    """发送飞书错误通知卡片（红色标题，用于系统异常告警）"""
    from datetime import datetime

    card = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "⚠️ Karens Agent 异常"},
                "template": "red",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"**{title}**\n\n{detail}"},
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [{
                        "tag": "plain_text",
                        "content": f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    }],
                },
            ],
        },
    }
    return send_feishu_card(card)


def push_report(weekly_repos: list[dict], monthly_repos: list[dict],
                news: list[dict], today: str) -> dict:
    """推送入口：飞书卡片 + 记录推送历史"""
    from formatters.feishu import build_feishu_card
    from database import save_push_history

    feishu_card = build_feishu_card(today, weekly_repos, monthly_repos, news)
    ok = send_feishu_card(feishu_card)

    repo_count = len(weekly_repos) + len(monthly_repos)

    if ok:
        save_push_history(
            platform="feishu",
            content_type="daily",
            content=str(feishu_card),
            repo_count=repo_count,
            news_count=len(news),
            status="sent",
        )
        # 标记已推送的 AI 资讯（方案 A：页面只显示推送过的）
        from database import mark_news_pushed
        news_urls = [n.get("url", "") for n in news if n.get("url")]
        if news_urls:
            mark_news_pushed(news_urls, today)

    return {"feishu": ok}
