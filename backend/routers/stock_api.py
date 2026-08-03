"""股票分析 API 路由

端点：
  POST   /api/stock/skill-report         — 综合数据报告（SSE 流式，由 SKILL 驱动）
  POST   /api/stock/skill-report/invest  — 投研报告（SKILL 数据 → DeepSeek 分析，SSE 流式）
  POST   /api/stock/analyze              — 触发个股分析（异步 + 轮询，内部走 SKILL）
  GET    /api/stock/analyze/result/{id}  — 查询分析结果
  GET    /api/stock/reports              — 历史报告列表
  GET    /api/stock/reports/{id}         — 报告详情
  GET    /api/stock/watchlist            — 自选股列表
  POST   /api/stock/watchlist            — 添加自选股
  DELETE /api/stock/watchlist/{code}     — 删除自选股
  PUT    /api/stock/watchlist/{code}     — 更新自选股
  POST   /api/stock/trigger/market-report — 触发自选股分析
"""

import asyncio
import uuid
import time
import threading
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/stock", tags=["stock"])

# ── 内存任务结果存储（与 trigger.py 模式一致） ──
_stock_tasks: dict[str, dict] = {}
_TASK_TTL = 3600  # 1 小时自动清理

# 关键维度（实时行情/基本信息）采集失败的统一提示文案（三个分析入口共用，
# 括号内维度清单与 report.py 中 critical=True 的维度对应）
_CRITICAL_FAIL_MSG = "关键数据采集失败（实时行情/基本信息）"


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
    dimensions: list[str] | None = None


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
    """后台执行个股分析：SKILL 取数 → DeepSeek 分析 → 渲染 → 存库"""
    try:
        from stock_agent.skill.report import generate_report_sync
        from stock_agent.analyze import analyze_with_validation
        from stock_agent.render import render_markdown
        from database import save_stock_report

        # Step 1: SKILL 采集 10 维度数据 → Markdown 报告
        data_result = generate_report_sync(stock_code)
        # 关门：关键维度（实时行情/基本信息）失败即硬终止，
        # 避免拿失败数据调 DeepSeek 并将垃圾报告存库
        if data_result.get("has_critical_failure"):
            raise RuntimeError(f"{_CRITICAL_FAIL_MSG}，已终止分析，请稍后重试")
        data_md = data_result["markdown"]
        # 使用归一化后的代码入库（如 HK2513 → 2513.HK）
        stock_code = data_result.get("stock_code", stock_code)
        stock_name = data_result.get("stock_name", stock_code)

        # Step 2: DeepSeek 分析（单 LLM + 语义校验 + 历史记忆）
        report, usage = analyze_with_validation(data_md, stock_code)

        # Step 3: 渲染
        md = render_markdown(stock_code, report, usage, stock_name)

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
            "message": f"{stock_code} 分析完成",
            "_created": _stock_tasks[task_id]["_created"],
        }
    except Exception as e:
        import traceback, sys
        tb = traceback.format_exc()
        print(f"[_run_analysis ERROR] {tb}", file=sys.stderr)
        _stock_tasks[task_id] = {
            "status": "error",
            "message": f"{type(e).__name__}: {e}",
            "_created": _stock_tasks[task_id]["_created"],
        }


def _run_watchlist_analyze(task_id: str):
    """后台执行自选股分析：从数据库读取启用状态的自选股，逐只分析（不推送飞书）"""
    try:
        from stock_agent.skill.report import generate_report_sync
        from stock_agent.analyze import analyze_with_validation
        from stock_agent.render import render_markdown
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
                data_result = generate_report_sync(code)
                # 关门：关键维度失败的股票直接标记失败跳过，不浪费 LLM 调用
                if data_result.get("has_critical_failure"):
                    raise RuntimeError(_CRITICAL_FAIL_MSG)
                data_md = data_result["markdown"]
                stock_name = data_result.get("stock_name", code)
                report, usage = analyze_with_validation(data_md, code)
                md = render_markdown(code, report, usage, stock_name)
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
    search: str = Query("", description="模糊搜索股票代码或名称"),
    date_from: str = Query("", description="起始日期 YYYY-MM-DD"),
    date_to: str = Query("", description="截止日期 YYYY-MM-DD"),
    decision: str = Query("", description="判断筛选 看多/震荡/看空"),
):
    """分页获取历史报告列表（支持筛选）"""
    from database import get_stock_reports

    rows, total = get_stock_reports(
        page=page,
        page_size=page_size,
        search=search,
        date_from=date_from,
        date_to=date_to,
        decision=decision,
    )
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


@router.get("/watchlist/reports")
def watchlist_reports():
    """获取自选股各自的最新报告摘要（score/decision/时间）"""
    from database import get_watchlist, get_latest_report

    items = get_watchlist()
    result = {}
    for item in items:
        code = item.get("stock_code", "")
        if not code:
            continue
        report = get_latest_report(code)
        if report:
            result[code] = {
                "score": report.get("score", 0),
                "decision": report.get("decision", ""),
                "created_at": report.get("created_at", ""),
            }
        else:
            result[code] = None
    return {"code": 0, "data": result}


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


# ═══════════════════════════════════════════
# 新增：SKILL 驱动的 SSE 端点
# ═══════════════════════════════════════════

def _format_sse_invest(event_type: str, data: dict) -> str:
    """格式化为投研报告 SSE 消息"""
    import json as _json
    payload = {"type": event_type, **data}
    return f"data: {_json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/skill-report")
async def skill_report(req: AnalyzeRequest):
    """生成综合数据报告（SSE 流式，10 维度 SKILL 采集）

    前端通过 fetch + ReadableStream 接收 SSE 事件：
      - progress: {stage, label, status, current, total}
      - complete: {report: str (完整 Markdown)}
    """
    from stock_agent.skill.report import generate_report_stream

    return StreamingResponse(
        generate_report_stream(req.stock_code, req.dimensions),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/skill-report/invest")
async def skill_report_invest(req: AnalyzeRequest):
    """生成投研报告（SKILL 数据 → DeepSeek 分析，SSE 流式）

    两阶段 SSE：
      1. 数据采集进度（10 维度，与 skill-report 相同）
      2. DeepSeek 分析完成 → 推送投研报告 Markdown
    """
    from stock_agent.skill.report import generate_report_stream

    async def invest_gen():
        # Phase 1: 数据采集 — 只转发 progress 事件，不转发 complete
        # （complete 里是原始数据 Markdown，仅供 DeepSeek 分析，不展示给前端）
        report_md = ""
        stock_name = req.stock_code
        dim_count = 0
        has_critical_failure = False
        async for sse_msg in generate_report_stream(req.stock_code, req.dimensions):
            if '"type": "complete"' in sse_msg:
                try:
                    import json as _json
                    data_str = sse_msg.replace("data: ", "").strip()
                    payload = _json.loads(data_str)
                    report_md = payload.get("report", "")
                    stock_name = payload.get("stock_name", req.stock_code)
                    has_critical_failure = bool(payload.get("has_critical_failure"))
                except Exception:
                    pass
                continue  # 关键：不要把原始数据的 complete 事件发给前端
            # 只转发 progress / start 事件
            yield sse_msg
            if '"type": "progress"' in sse_msg and '"status": "done"' in sse_msg:
                dim_count += 1

        if not report_md:
            yield _format_sse_invest("error", {"message": "数据采集失败，无法生成投研报告"})
            return

        # 关门：关键维度（实时行情/基本信息）失败即硬终止 ——
        # 不调 DeepSeek、不存库，发 error 事件由前端 Toast 明确提示
        if has_critical_failure:
            yield _format_sse_invest("error", {
                "message": f"{_CRITICAL_FAIL_MSG}，已终止投研分析，请稍后重试",
            })
            return

        # Phase 2: DeepSeek 分析（单 LLM + 语义校验 + 历史记忆）
        yield _format_sse_invest("progress", {
            "stage": "llm",
            "label": "DeepSeek 分析",
            "status": "running",
            "current": dim_count,
            "total": dim_count,
        })

        try:
            from stock_agent.analyze import analyze_with_validation, render_markdown

            loop = asyncio.get_running_loop()
            report_json, usage = await loop.run_in_executor(
                None, analyze_with_validation, report_md, req.stock_code,
            )
            invest_md = render_markdown(req.stock_code, report_json, usage, stock_name)

            # 存库，前端跳转详情页需要 report_id
            report_id = None
            try:
                from database import save_stock_report
                report_id = await loop.run_in_executor(
                    None,
                    lambda: save_stock_report(
                        stock_code=req.stock_code,
                        stock_name=stock_name,
                        report=report_json,
                        markdown=invest_md,
                        token_used=usage.get("total", 0),
                    ),
                )
            except Exception:
                pass

            yield _format_sse_invest("complete", {
                "report": invest_md,
                "usage": usage,
                "score": report_json.get("score"),
                "decision": report_json.get("decision"),
                "report_id": report_id,
                "stock_code": req.stock_code,
                "stock_name": stock_name,
            })
        except Exception as e:
            yield _format_sse_invest("error", {"message": f"投研分析失败：{e}"})

    return StreamingResponse(
        invest_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
