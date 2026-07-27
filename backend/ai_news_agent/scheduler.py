"""AI 前沿咨询 Agent —— 定时任务调度器"""

import json
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import PUSH_TIME
from .graph import run_news_search
from .feishu import build_ai_news_card, send_feishu_card, send_error_notification
from .database import save_ai_news_report, save_push_history

# 全局单例调度器
_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    """获取调度器单例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    return _scheduler


def daily_ai_news_push():
    """每日 AI 新闻抓取 + 推送（定时任务入口）"""
    print("[ai_news] 定时任务触发 — " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    today_str = datetime.now().strftime("%Y-%m-%d")

    errors = []
    results = {}

    # 依次搜索日报 / 周报（结构相同，循环处理）
    report_tasks = [
        ("daily", "昨日 AI 新闻"),
        ("weekly", "近一周 AI 新闻"),
    ]
    for report_type, label in report_tasks:
        print(f"[ai_news] {label} 开始搜索...")
        try:
            result = run_news_search(report_type)
            save_ai_news_report(
                report_type=report_type,
                search_query=result["search_query"],
                search_results=result["search_results"],
                summary=result["summary"],
                source_urls=_extract_urls(result["search_results"]),
            )
            results[report_type] = result
        except Exception as e:
            errors.append(f"{label}: {e}")
            print(f"[ai_news] {label}搜索失败: {e}")

    # 构建飞书卡片并推送
    if not results:
        send_error_notification(
            "AI 新闻抓取失败",
            "日期: " + today_str + "\n\n" + "\n".join(errors),
        )
        return

    daily_summary = results.get("daily", {}).get("summary", "今日搜索失败，请稍后重试")
    weekly_summary = results.get("weekly", {}).get("summary", "搜索失败，请稍后重试")

    card = build_ai_news_card(daily_summary, weekly_summary)
    card_json = json.dumps(card, ensure_ascii=False)
    success = send_feishu_card(card)

    # 记录推送历史
    save_push_history(
        platform="feishu",
        content_type="daily",
        content=card_json,
        news_count=len(results),
        status="sent" if success else "failed",
    )

    if success:
        print(f"[ai_news] 推送完成 {today_str}")
    else:
        print(f"[ai_news] 推送失败 {today_str}")


def _extract_urls(search_results: str) -> list[str]:
    """从搜索结果文本中提取 URL 列表"""
    urls = []
    for line in search_results.split("\n"):
        line = line.strip()
        if line.startswith("🔗"):
            url = line.replace("🔗", "").strip()
            if url:
                urls.append(url)
    return urls


def start_scheduler():
    """启动定时任务调度器"""
    scheduler = get_scheduler()
    hour, minute = _parse_push_time()

    scheduler.add_job(
        daily_ai_news_push,
        CronTrigger(hour=hour, minute=minute, timezone="Asia/Shanghai"),
        misfire_grace_time=300,
        id="daily_ai_news_push",
        name="每日 AI 新闻推送",
        replace_existing=True,
    )

    scheduler.start()
    print(f"[ai_news] ⏰ 定时任务已启动 — 每天 {hour:02d}:{minute:02d} 推送")


def stop_scheduler():
    """停止定时任务调度器"""
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[ai_news] ⏰ 定时任务已停止")


def _parse_push_time() -> tuple[int, int]:
    """解析 PUSH_TIME 配置（格式 HH:MM）"""
    try:
        parts = PUSH_TIME.split(":")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return 9, 0
