"""股票分析 API 路由

端点：
  POST   /api/stock/analyze              — 触发个股分析（异步 + 轮询）
  GET    /api/stock/analyze/result/{id}  — 查询分析结果
  GET    /api/stock/reports              — 历史报告列表
  GET    /api/stock/reports/{id}         — 报告详情
  GET    /api/stock/watchlist            — 自选股列表
  POST   /api/stock/watchlist            — 添加自选股
  DELETE /api/stock/watchlist/{code}     — 删除自选股
  PUT    /api/stock/watchlist/{code}     — 更新自选股
  POST   /api/stock/trigger/market-report — 触发自选股分析
"""

import uuid
import time
import threading
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/stock", tags=["stock"])

# ── 内存任务结果存储（与 trigger.py 模式一致） ──
_stock_tasks: dict[str, dict] = {}
_TASK_TTL = 3600  # 1 小时自动清理


def _clean_old_tasks():
    """移除过期任务"""
    now = time.time()
    expired = [
        k for k, v in _stock_tasks.items()
        if now - v.get("_created", 0) > _TASK_TTL
    ]
    for k in expired:
        del _stock_tasks[k]


def _create_task() -> str:
    """创建新任务条目，返回 8 位 task_id"""
    _clean_old_tasks()
    task_id = str(uuid.uuid4())[:8]
    _stock_tasks[task_id] = {
        "status": "running",
        "_created": time.time(),
        "message": "",
    }
    return task_id


# ── Pydantic 请求体 ──

class AnalyzeRequest(BaseModel):
    stock_code: str


class WatchlistAdd(BaseModel):
    stock_code: str
    stock_name: str = ""
    notes: str = ""
    sort_order: int = 0


class WatchlistUpdate(BaseModel):
    stock_name: str | None = None
    notes: str | None = None
    enabled: int | None = None
    sort_order: int | None = None


# ═══════════════════════════════════════════
# 后台分析任务
# ═══════════════════════════════════════════

def _run_analysis(task_id: str, stock_code: str):
    """后台执行个股分析：采集 → LLM 分析 → 渲染 → 存库"""
    try:
        from stock_agent.fetcher import fetch_stock_data
        from stock_agent.analyze import analyze, render_markdown
        from database import save_stock_report

        data = fetch_stock_data(stock_code)
        report, usage = analyze(data)
        md = render_markdown(data, report, usage)
        stock_name = data.get("stock_name", stock_code)

        report_id = save_stock_report(
            stock_code=stock_code,
            stock_name=stock_name,
            report=report,
            markdown=md,
            token_used=usage.get("total", 0),
        )

        _stock_tasks[task_id] = {
            "status": "done",
            "report_id": report_id,
            "report": report,
            "usage": usage,
            "message": f"{stock_name}({stock_code}) 分析完成",
            "_created": _stock_tasks[task_id]["_created"],
        }
    except Exception as e:
        _stock_tasks[task_id] = {
            "status": "error",
            "message": str(e),
            "_created": _stock_tasks[task_id]["_created"],
        }


def _run_watchlist_analyze(task_id: str):
    """后台执行自选股分析：从数据库读取启用状态的自选股，逐只分析（不推送飞书）"""
    try:
        from stock_agent.fetcher import fetch_stock_data
        from stock_agent.analyze import analyze, render_markdown
        from database import save_stock_report, get_watchlist

        watchlist = get_watchlist()
        # 只分析启用状态的自选股（enabled 默认 1）
        codes = [item["stock_code"] for item in watchlist if item.get("enabled", 1)]
        if not codes:
            _stock_tasks[task_id] = {
                "status": "done",
                "results": [],
                "message": "自选股列表为空，无需分析",
                "_created": _stock_tasks[task_id]["_created"],
            }
            return

        results = []
        for code in codes:
            try:
                data = fetch_stock_data(code)
                report, usage = analyze(data)
                md = render_markdown(data, report, usage)
                stock_name = data.get("stock_name", code)
                save_stock_report(
                    stock_code=code, stock_name=stock_name,
                    report=report, markdown=md, token_used=usage.get("total", 0),
                )
                results.append({"code": code, "name": stock_name, "ok": True})
            except Exception as e:
                results.append({"code": code, "name": code, "ok": False, "error": str(e)})

        ok_count = sum(1 for r in results if r["ok"])
        _stock_tasks[task_id] = {
            "status": "done",
            "results": results,
            "message": f"自选股分析完成：{ok_count}/{len(results)} 成功",
            "_created": _stock_tasks[task_id]["_created"],
        }
    except Exception as e:
        _stock_tasks[task_id] = {
            "status": "error",
            "message": str(e),
            "_created": _stock_tasks[task_id]["_created"],
        }


# ═══════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════

@router.post("/analyze")
def trigger_analyze(req: AnalyzeRequest):
    """触发个股分析（后台异步执行，返回 task_id 供轮询）"""
    task_id = _create_task()
    threading.Thread(target=_run_analysis, args=(task_id, req.stock_code), daemon=True).start()
    return {"code": 0, "task_id": task_id, "message": f"已触发 {req.stock_code} 分析"}


@router.get("/analyze/result/{task_id}")
def get_analyze_result(task_id: str):
    """查询分析任务结果"""
    result = _stock_tasks.get(task_id)
    if not result:
        return {"code": 1, "message": "任务不存在或已过期"}
    return {
        "code": 0,
        "data": {
            "status": result.get("status"),
            "report_id": result.get("report_id"),
            "report": result.get("report"),
            "usage": result.get("usage"),
            "message": result.get("message"),
        },
    }


@router.get("/reports")
def list_reports(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页条数"),
):
    """分页获取历史报告列表"""
    from database import get_stock_reports

    rows, total = get_stock_reports(page=page, page_size=page_size)
    return {"code": 0, "data": {"items": rows, "total": total, "page": page, "page_size": page_size}}


@router.get("/reports/{report_id}")
def get_report(report_id: int):
    """获取报告详情"""
    from database import get_stock_report_by_id

    row = get_stock_report_by_id(report_id)
    if not row:
        return {"code": 1, "message": "报告不存在"}
    return {"code": 0, "data": row}


@router.get("/watchlist")
def list_watchlist():
    """获取自选股列表"""
    from database import get_watchlist

    items = get_watchlist()
    return {"code": 0, "data": items}


@router.post("/watchlist")
def add_watchlist(item: WatchlistAdd):
    """添加自选股"""
    from database import add_watchlist as db_add_watchlist

    ok = db_add_watchlist(item.stock_code, item.stock_name, item.notes)
    if not ok:
        return {"code": 1, "message": f"股票 [{item.stock_code}] 已在自选股中"}
    # 如果指定了 sort_order，更新它
    if item.sort_order > 0:
        from database import update_watchlist
        update_watchlist(item.stock_code, {"sort_order": item.sort_order})
    return {"code": 0, "message": f"已添加 [{item.stock_code}]"}


@router.delete("/watchlist/{stock_code}")
def remove_watchlist(stock_code: str):
    """删除自选股"""
    from database import delete_watchlist

    delete_watchlist(stock_code)
    return {"code": 0, "message": f"已删除 [{stock_code}]"}


@router.put("/watchlist/{stock_code}")
def update_watchlist_item(stock_code: str, item: WatchlistUpdate):
    """更新自选股"""
    from database import update_watchlist

    updates = {k: v for k, v in item.model_dump().items() if v is not None}
    if not updates:
        return {"code": 1, "message": "无更新字段"}
    ok = update_watchlist(stock_code, updates)
    if not ok:
        return {"code": 1, "message": f"股票 [{stock_code}] 不在自选股中"}
    return {"code": 0, "message": f"已更新 [{stock_code}]"}


@router.post("/reports/{report_id}/push")
def push_report(report_id: int):
    """推送指定报告到飞书"""
    from database import get_stock_report_by_id
    from stock_agent.analyze import push_to_feishu

    row = get_stock_report_by_id(report_id)
    if not row:
        return {"code": 1, "message": "报告不存在"}

    ok = push_to_feishu(row["markdown"], row["stock_name"], row["stock_code"])
    if ok:
        return {"code": 0, "message": f"已推送 {row['stock_name']}({row['stock_code']}) 到飞书"}
    else:
        return {"code": 1, "message": "推送失败，请检查飞书 Webhook 配置"}


@router.post("/trigger/market-report")
def trigger_market_report():
    """手动触发自选股分析（后台异步执行，从数据库自选股表读取，不推送飞书）"""
    task_id = _create_task()
    threading.Thread(target=_run_watchlist_analyze, args=(task_id,), daemon=True).start()
    return {"code": 0, "task_id": task_id, "message": "已触发自选股分析"}
