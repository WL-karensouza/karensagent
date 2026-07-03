"""飞书机器人富文本卡片格式化器

飞书消息卡片使用 JSON 格式，支持：
- 多列布局
- 颜色标签
- Markdown 内容块
- 按钮跳转
"""

from datetime import datetime
import json


def build_feishu_card(today: str, weekly_repos: list[dict],
                      monthly_repos: list[dict],
                      news: list[dict]) -> dict:
    """
    构建飞书卡片消息 JSON

    返回完整的飞书卡片消息体，可直接 POST 到飞书 Webhook
    """

    # ── 标题 ──
    header = {
        "title": {
            "tag": "plain_text",
            "content": f"Karens Agent 日报 | {today}"
        },
        "template": "blue"
    }

    elements = []

    # ── 本周热榜（Top 10，纯 Stars 排名） ──
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "### 🔥 本周 GitHub 热榜 Top 10"
        }
    })

    for i, r in enumerate(weekly_repos[:10], 1):
        stars = r.get("stars_today", 0)
        desc = r.get("description", "")
        if len(desc) > 100:
            desc = desc[:100] + "..."

        content = f"**{i}. [{r['repo_name']}]({r['repo_url']})** — ⭐ {stars:,}"
        if desc:
            content += f"\n> {desc}"

        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": content}
        })

    # ── 分隔线 ──
    elements.append({"tag": "hr"})

    # ── 本月精选 ──
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "### 🏆 本月 GitHub 热榜精选"
        }
    })

    for i, r in enumerate(monthly_repos[:10], 1):
        stars = r.get("stars_today", 0)
        desc = r.get("description", "")
        if len(desc) > 100:
            desc = desc[:100] + "..."

        content = f"**{i}. [{r['repo_name']}]({r['repo_url']})** — ⭐ {stars:,}"
        if desc:
            content += f"\n> {desc}"

        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": content}
        })

    # ── 分隔线 ──
    elements.append({"tag": "hr"})

    # ── AI 资讯（Top 5） ──
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "### 📚 AI 前沿速递"
        }
    })

    for i, n in enumerate(news[:5], 1):
        source_label = {
            "hackernews": "HN",
            "arxiv": "ArXiv",
            "paperswithcode": "PwC",
        }.get(n.get("source", ""), n.get("source", ""))
        content = f"{i}. [{source_label}] [{n.get('title', '')}]({n.get('url', '')})"
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": content}
        })

    # ── 底部 ──
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "note",
        "elements": [{
            "tag": "plain_text",
            "content": "Karens Agent 自动生成 · 每天 9:00 推送"
        }]
    })

    card = {
        "config": {"wide_screen_mode": True},
        "header": header,
        "elements": elements
    }

    return {"msg_type": "interactive", "card": card}
