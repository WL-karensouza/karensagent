"""
消息面分析技能
=============
从新闻数据中提取关键主题和情绪信号
"""
from typing import Any


def news_skill(data: dict) -> dict[str, Any]:
    """消息面分析——新闻数据可用时才启用"""

    news = data.get("news")
    if not news:
        return {"enabled": False, "reason": "无近期新闻数据"}

    headlines = []
    for n in news[:8]:
        headlines.append({
            "time": str(n.get("time", "")),
            "title": str(n.get("title", "")),
        })

    return {
        "enabled": True,
        "section": {
            "title": "消息面",
            "fields": {"近期新闻": headlines},
            "hint": "请基于以上新闻标题给出：消息面情绪（偏多/中性/偏空）、关键主题词、独立洞察",
        },
    }
