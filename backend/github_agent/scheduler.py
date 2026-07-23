"""定时任务调度器 —— APScheduler 管理"""

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from config import PUSH_TIME, WEEKLY_TOP_N, MONTHLY_TOP_N, NEWS_TOP_N
from database import save_daily_trends, save_ai_news, get_trends_by_source, get_ai_news
from github_agent.fetchers.github import fetch_all_trends
from github_agent.fetchers.ai_news import fetch_hackernews, fetch_arxiv, fetch_paperswithcode
from github_agent.filters.keyword import filter_repos, filter_news
from github_agent.notifier import send_error_notification, push_report


_scheduler = None


def get_scheduler() -> BackgroundScheduler:
    """获取全局调度器实例（单例）"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    return _scheduler


# ═══════════════════════════════════════════
# 抓取辅助（逐源 + 错误收集）
# ═══════════════════════════════════════════

def _fetch_all_with_errors(today: str) -> dict:
    """逐源抓取，返回 {all_failed, sources, message}"""

    result = {"all_failed": False, "sources": {}}
    all_failed_count = 0
    total_sources = 4

    # ── GitHub ──
    try:
        trends = fetch_all_trends(date=today)
        if trends:
            save_daily_trends(trends, source="daily", fetch_date=today)
        result["sources"]["github"] = {"ok": True, "count": len(trends)}
    except Exception as e:
        result["sources"]["github"] = {"ok": False, "error": str(e)}
        all_failed_count += 1
        print(f"[scheduler] GitHub 抓取失败: {e}")

    # ── HN ──
    try:
        hn = fetch_hackernews(limit=10)
        for n in hn:
            n["fetch_date"] = today
        result["sources"]["hackernews"] = {"ok": True, "count": len(hn)}
    except Exception as e:
        hn = []
        result["sources"]["hackernews"] = {"ok": False, "error": str(e)}
        all_failed_count += 1
        print(f"[scheduler] HN 抓取失败: {e}")

    # ── ArXiv ──
    try:
        arxiv = fetch_arxiv(limit=10)
        for n in arxiv:
            n["fetch_date"] = today
        result["sources"]["arxiv"] = {"ok": True, "count": len(arxiv)}
    except Exception as e:
        arxiv = []
        result["sources"]["arxiv"] = {"ok": False, "error": str(e)}
        all_failed_count += 1
        print(f"[scheduler] ArXiv 抓取失败: {e}")

    # ── PwC ──
    try:
        pwc = fetch_paperswithcode(limit=10)
        for n in pwc:
            n["fetch_date"] = today
        result["sources"]["paperswithcode"] = {"ok": True, "count": len(pwc)}
    except Exception as e:
        pwc = []
        result["sources"]["paperswithcode"] = {"ok": False, "error": str(e)}
        all_failed_count += 1
        print(f"[scheduler] PwC 抓取失败: {e}")

    # ── 保存 AI 资讯（部分数据也入库） ──
    all_news = hn + arxiv + pwc
    if all_news:
        try:
            save_ai_news(all_news, date=today)
        except Exception as e:
            print(f"[scheduler] save_ai_news 入库异常（不阻断流程）: {e}")

    result["all_failed"] = (all_failed_count >= total_sources)

    failed_names = [
        name for name, info in result["sources"].items()
        if not info["ok"]
    ]
    if not failed_names:
        result["message"] = "所有数据源抓取成功"
    elif result["all_failed"]:
        result["message"] = f"所有数据源抓取失败：{'、'.join(failed_names)}"
    else:
        result["message"] = f"{'、'.join(failed_names)} 抓取失败，已用已有数据推送"

    return result


def daily_fetch_and_push():
    """
    每日定时任务：
    1. 逐源抓取 + 错误收集
    2. 全部失败 → 飞书通知 + 阻止推送
    3. 部分失败 → 继续推送
    4. 推送失败 → 飞书通知
    """
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[scheduler] ⏰ 定时任务触发 — {today}")
    print(f"{'='*50}")

    # ── 步骤 1: 抓取 ──
    print("[scheduler] ① 抓取数据...")
    fetch_result = _fetch_all_with_errors(today)

    if fetch_result["all_failed"]:
        print(f"[scheduler] ❌ {fetch_result['message']}")
        try:
            error_detail = "\n".join(
                f"- {name}: {info.get('error', 'unknown')}"
                for name, info in fetch_result["sources"].items()
                if not info.get("ok")
            )
            send_error_notification("今日数据抓取全部失败", error_detail)
        except Exception as e:
            print(f"[scheduler] 飞书错误通知发送失败: {e}")
        print(f"[scheduler] ⛔ 跳过推送\n")
        return

    if not fetch_result["sources"] or all(
        info.get("ok") for info in fetch_result["sources"].values()
    ):
        print(f"[scheduler] ✅ {fetch_result['message']}")
    else:
        print(f"[scheduler] ⚠️ {fetch_result['message']}")

    # ── 步骤 2: 过滤 ──

    print("[scheduler] ② 数据聚合...")

    weekly_raw = get_trends_by_source(source="weekly", fetch_date=today, top_n=50)
    monthly_raw = get_trends_by_source(source="monthly", fetch_date=today, top_n=50)
    ai_news_raw = get_ai_news(today, top_n=30)

    weekly_filtered = filter_repos(weekly_raw, top_n=WEEKLY_TOP_N)
    monthly_filtered = filter_repos(monthly_raw, top_n=MONTHLY_TOP_N)
    news_filtered = filter_news(ai_news_raw, top_n=NEWS_TOP_N)

    print(f"[scheduler] 周榜过滤后: {len(weekly_filtered)} 条")
    print(f"[scheduler] 月榜过滤后: {len(monthly_filtered)} 条")
    print(f"[scheduler] 资讯过滤后: {len(news_filtered)} 条")

    # ── 步骤 3: 推送 ──
    print("[scheduler] ③ 推送消息...")
    result = push_report(weekly_filtered, monthly_filtered, news_filtered, today)

    print(f"[scheduler] 推送结果: 飞书={result['feishu']}")

    if not result["feishu"]:
        try:
            send_error_notification("定时推送失败", "飞书 Webhook 返回失败状态")
        except Exception as e:
            print(f"[scheduler] 飞书错误通知发送失败: {e}")

    print(f"[scheduler] ✅ 任务完成\n")


def start_scheduler():
    """启动定时任务"""
    scheduler = get_scheduler()

    hour, minute = PUSH_TIME.split(":")
    scheduler.add_job(
        daily_fetch_and_push,
        "cron",
        hour=int(hour),
        minute=int(minute),
        misfire_grace_time=60,
        id="daily_push",
        name="每日 GitHub 热榜推送",
        replace_existing=True,
    )

    # 大盘分析定时任务已移除
    # 用户可通过前端按钮手动触发自选股分析

    scheduler.start()
    print(f"[scheduler] ✅ 定时任务已启动 — 每天 {PUSH_TIME} 执行")


def stop_scheduler():
    """停止定时任务"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        print("[scheduler] 🛑 定时任务已停止")
