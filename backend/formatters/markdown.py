"""通用 Markdown 格式化器"""

from datetime import datetime, timedelta


def format_date_range(days: int = 7) -> str:
    """生成日期范围字符串"""
    now = datetime.now()
    start = now - timedelta(days=days)
    end = now
    return f"{start.strftime('%Y.%m.%d')} - {end.strftime('%m.%d')}"


def format_repo_item(repo: dict, idx: int) -> str:
    """格式化单条仓库"""
    stars = repo.get("week_stars") or repo.get("month_stars") or repo.get("stars_today", 0)
    desc = repo.get("description", "")
    desc_line = f"\n   > {desc}" if desc else ""

    line = (
        f"{idx}. ⭐ **[{repo['repo_name']}]({repo['repo_url']})** "
        f"— {stars:,}★"
        f"{desc_line}"
    )
    return line


def format_news_item(news: dict, idx: int) -> str:
    """格式化单条资讯"""
    source_icon = {"hackernews": "💬", "arxiv": "📄"}.get(news.get("source", ""), "📌")
    title = news.get("title", "")
    url = news.get("url", "")
    summary = news.get("summary", "")

    lines = [f"{idx}. {source_icon} [{title}]({url})"]
    if summary:
        lines.append(f"   _{summary[:150]}_")
    return "\n".join(lines)


def build_weekly_report(repos: list[dict], news: list[dict]) -> str:
    """生成周报 Markdown"""
    date_range = format_date_range(days=7)
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"## 🤖 GitHub Agent 周报 | {today}",
        "",
        f"📅 统计周期：{date_range}",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        f"### 🔥 本周 Trending（关键词：skill, agent, MCP...）",
        "",
    ]

    if repos:
        for i, r in enumerate(repos, 1):
            lines.append(format_repo_item(r, i))
            lines.append("")
    else:
        lines.append("> 暂无相关热门仓库")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("### 📚 AI 前沿速递")
    lines.append("")

    if news:
        for i, n in enumerate(news, 1):
            lines.append(format_news_item(n, i))
            lines.append("")
    else:
        lines.append("> 暂无 AI 前沿资讯")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("🤖 _由 GitHub Agent 自动生成_")

    return "\n".join(lines)


def build_monthly_report(repos: list[dict], news: list[dict]) -> str:
    """生成月报 Markdown"""
    date_range = format_date_range(days=30)
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"## 🤖 GitHub Agent 月报 | {today}",
        "",
        f"📅 统计周期：{date_range}",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        f"### 🏆 本月热门 Top 30（关键词：skill, agent, MCP...）",
        "",
    ]

    if repos:
        for i, r in enumerate(repos, 1):
            lines.append(format_repo_item(r, i))
            lines.append("")
    else:
        lines.append("> 暂无相关热门仓库")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("### 📚 AI 前沿速递")
    lines.append("")

    if news:
        for i, n in enumerate(news, 1):
            lines.append(format_news_item(n, i))
            lines.append("")
    else:
        lines.append("> 暂无 AI 前沿资讯")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("🤖 _由 GitHub Agent 自动生成_")

    return "\n".join(lines)
