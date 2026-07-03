"""手动触发 API —— 立即抓取/推送（后台异步执行 + 结果轮询）"""

import uuid
import time
import threading
from fastapi import APIRouter

router = APIRouter(prefix="/api/trigger", tags=["trigger"])

# ── 内存任务结果存储 ──
_task_results: dict[str, dict] = {}
_TASK_TTL = 3600  # 1 小时后自动清理


def _clean_old_tasks():
    """移除过期任务"""
    now = time.time()
    expired = [
        k for k, v in _task_results.items()
        if now - v.get("_created", 0) > _TASK_TTL
    ]
    for k in expired:
        del _task_results[k]


def _create_task() -> str:
    """创建新任务条目，返回 task_id"""
    _clean_old_tasks()
    task_id = str(uuid.uuid4())[:8]
    _task_results[task_id] = {
        "status": "running",
        "_created": time.time(),
        "fetch": None,
        "push": None,
        "message": "",
    }
    return task_id


# ═══════════════════════════════════════════
# 后台任务
# ═══════════════════════════════════════════

def _run_fetch(task_id: str):
    """后台抓取 —— 逐源调用，逐个收集错误信息"""
    from datetime import datetime
    from fetchers.github import fetch_all_trends
    from fetchers.ai_news import fetch_hackernews, fetch_arxiv, fetch_paperswithcode
    from database import save_daily_trends, save_ai_news

    today = datetime.now().strftime("%Y-%m-%d")
    fetch_result = {"ok": True, "all_failed": False, "sources": {}}
    all_failed_count = 0
    total_sources = 4

    # ── GitHub Trending（daily + weekly + monthly 统一抓取） ──
    try:
        trends = fetch_all_trends(date=today)
        if trends:
            save_daily_trends(trends, source="daily", fetch_date=today)
        fetch_result["sources"]["github"] = {"ok": True, "count": len(trends)}
    except Exception as e:
        fetch_result["sources"]["github"] = {"ok": False, "error": str(e)}
        fetch_result["ok"] = False
        all_failed_count += 1
        print(f"[trigger] GitHub 抓取失败: {e}")

    # ── HackerNews ──
    try:
        hn = fetch_hackernews(limit=10)
        for n in hn:
            n["fetch_date"] = today
        fetch_result["sources"]["hackernews"] = {"ok": True, "count": len(hn)}
    except Exception as e:
        hn = []
        fetch_result["sources"]["hackernews"] = {"ok": False, "error": str(e)}
        fetch_result["ok"] = False
        all_failed_count += 1
        print(f"[trigger] HN 抓取失败: {e}")

    # ── ArXiv ──
    try:
        arxiv = fetch_arxiv(limit=10)
        for n in arxiv:
            n["fetch_date"] = today
        fetch_result["sources"]["arxiv"] = {"ok": True, "count": len(arxiv)}
    except Exception as e:
        arxiv = []
        fetch_result["sources"]["arxiv"] = {"ok": False, "error": str(e)}
        fetch_result["ok"] = False
        all_failed_count += 1
        print(f"[trigger] ArXiv 抓取失败: {e}")

    # ── PapersWithCode / HuggingFace ──
    try:
        pwc = fetch_paperswithcode(limit=10)
        for n in pwc:
            n["fetch_date"] = today
        fetch_result["sources"]["paperswithcode"] = {"ok": True, "count": len(pwc)}
    except Exception as e:
        pwc = []
        fetch_result["sources"]["paperswithcode"] = {"ok": False, "error": str(e)}
        fetch_result["ok"] = False
        all_failed_count += 1
        print(f"[trigger] PwC 抓取失败: {e}")

    # ── 保存 AI 资讯（部分数据也可以入库） ──
    all_news = hn + arxiv + pwc
    if all_news:
        try:
            save_ai_news(all_news, date=today)
        except Exception as e:
            print(f"[trigger] save_ai_news 入库异常（不阻断流程）: {e}")

    # ── 汇总状态 ──
    fetch_result["all_failed"] = (all_failed_count >= total_sources)

    failed_names = [
        name for name, info in fetch_result["sources"].items()
        if not info["ok"]
    ]
    if not failed_names:
        fetch_result["message"] = "所有数据源抓取成功"
    elif fetch_result["all_failed"]:
        fetch_result["message"] = f"所有数据源抓取失败：{'、'.join(failed_names)}"
    else:
        fetch_result["message"] = f"{'、'.join(failed_names)} 抓取失败，已用已有数据推送"

    _task_results[task_id]["fetch"] = fetch_result
    print(f"[trigger] 后台抓取完成 — {fetch_result['message']}")


def _run_push(task_id: str):
    """后台推送 —— 带异常包装，错误信息写入 task_result"""
    from datetime import datetime
    from filters.keyword import filter_repos, filter_news
    from database import get_trends_by_source, get_ai_news
    from notifier import push_report, send_error_notification
    from config import WEEKLY_TOP_N, MONTHLY_TOP_N, NEWS_TOP_N

    today = datetime.now().strftime("%Y-%m-%d")
    push_result = {"ok": False, "error": None, "repo_count": 0, "news_count": 0}

    try:
        weekly_raw = get_trends_by_source(source="weekly", fetch_date=today, top_n=50)
        monthly_raw = get_trends_by_source(source="monthly", fetch_date=today, top_n=50)
        ai_news_raw = get_ai_news(today, top_n=30)

        # 完全没有数据可推时跳过
        if not weekly_raw and not monthly_raw and not ai_news_raw:
            push_result["ok"] = True
            push_result["message"] = "无数据可推送，跳过"
            _task_results[task_id]["push"] = push_result
            return

        weekly_filtered = filter_repos(weekly_raw, top_n=WEEKLY_TOP_N)
        monthly_filtered = filter_repos(monthly_raw, top_n=MONTHLY_TOP_N)
        news_filtered = filter_news(ai_news_raw, top_n=NEWS_TOP_N)

        report_result = push_report(
            weekly_filtered, monthly_filtered, news_filtered, today
        )

        push_result["ok"] = report_result["feishu"]
        push_result["repo_count"] = len(weekly_filtered) + len(monthly_filtered)
        push_result["news_count"] = len(news_filtered)

        if push_result["ok"]:
            push_result["message"] = "推送成功"
        else:
            push_result["error"] = "飞书 Webhook 返回失败状态"
            push_result["message"] = "飞书推送失败，请检查 Webhook 配置"

    except Exception as e:
        push_result["ok"] = False
        push_result["error"] = str(e)
        push_result["message"] = f"推送阶段异常: {e}"
        print(f"[trigger] 推送异常: {e}")
        # 尽力尝试通知飞书
        try:
            send_error_notification("推送失败", str(e))
        except Exception:
            pass

    _task_results[task_id]["push"] = push_result
    print(f"[trigger] 后台推送完成 — ok={push_result['ok']}")


def _run_full(task_id: str):
    """全流程：先抓取，按结果决定是否推送"""
    from notifier import send_error_notification

    _run_fetch(task_id)
    fetch_result = _task_results[task_id].get("fetch", {})

    if fetch_result.get("all_failed", False):
        # 所有数据源失败 → 阻止推送，通知飞书
        _task_results[task_id]["status"] = "done"
        _task_results[task_id]["message"] = fetch_result.get("message", "所有数据源抓取失败")

        # 飞书错误通知（best-effort）
        try:
            error_detail = "\n".join(
                f"- {name}: {info.get('error', 'unknown')}"
                for name, info in fetch_result.get("sources", {}).items()
                if not info.get("ok")
            )
            send_error_notification("今日数据抓取全部失败", error_detail)
        except Exception as e:
            print(f"[trigger] 飞书错误通知发送失败: {e}")
        return

    # 至少一个数据源成功 → 继续推送
    _run_push(task_id)

    push_result = _task_results[task_id].get("push", {})
    if push_result.get("ok"):
        final_msg = fetch_result.get("message", "操作成功")
    else:
        final_msg = push_result.get("message", "推送失败")

    _task_results[task_id]["status"] = "done"
    _task_results[task_id]["message"] = final_msg


# ═══════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════

@router.post("/fetch")
def trigger_fetch():
    """手动触发抓取（后台执行，返回 task_id 供轮询）"""
    task_id = _create_task()
    threading.Thread(target=_run_fetch, args=(task_id,), daemon=True).start()
    return {"code": 0, "task_id": task_id, "message": "已触发后台抓取"}


@router.post("/push")
def trigger_push():
    """手动触发推送（后台执行，返回 task_id 供轮询）"""
    task_id = _create_task()
    threading.Thread(target=_run_push, args=(task_id,), daemon=True).start()
    return {"code": 0, "task_id": task_id, "message": "已触发后台推送"}


@router.post("/full")
def trigger_full():
    """一键全流程：抓取 + 推送（后台执行，返回 task_id 供轮询）"""
    task_id = _create_task()
    threading.Thread(target=_run_full, args=(task_id,), daemon=True).start()
    return {"code": 0, "task_id": task_id, "message": "已触发后台全流程"}


@router.get("/result/{task_id}")
def get_task_result(task_id: str):
    """查询后台任务执行结果"""
    result = _task_results.get(task_id)
    if not result:
        return {"code": 1, "message": "任务不存在或已过期"}
    return {
        "code": 0,
        "data": {
            "status": result.get("status"),
            "fetch": result.get("fetch"),
            "push": result.get("push"),
            "message": result.get("message"),
        },
    }
