"""投研 AI 问答 —— FastAPI 路由"""
import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from database import get_stock_report_by_id
from ..database import (
    get_or_create_session, update_session_report, add_message, list_messages,
)
from ..graph import run_qa_agent
from ..tools import TOOL_FRIENDLY_NAMES

router = APIRouter(prefix="/api/chat", tags=["chat"])


class AskRequest(BaseModel):
    question: str
    report_id: int | None = None   # 可选，用于锚定会话
    stock_name: str = ""


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/session/{stock_code}")
def get_chat_session(stock_code: str):
    """获取会话 + 历史消息"""
    session = get_or_create_session(stock_code)
    messages = list_messages(session["id"])
    return {"code": 0, "data": {"session": session, "messages": messages}}


@router.get("/session/{stock_code}/messages")
def get_chat_messages(stock_code: str, limit: int = 100):
    """分页拉历史消息"""
    session = get_or_create_session(stock_code)
    messages = list_messages(session["id"], limit=limit)
    return {"code": 0, "data": messages}


@router.post("/{stock_code}/ask")
async def ask(stock_code: str, req: AskRequest):
    """SSE 流式提问"""
    session = get_or_create_session(stock_code, req.stock_name)

    # 锚定报告（可选）
    if req.report_id:
        update_session_report(session["id"], req.report_id)

    # 构建报告上下文（固定锚点：取最新报告结论摘要）
    report_context = _build_report_context(req.report_id, stock_code)

    # 取最近 8 轮对话历史（每轮含 user+assistant 两条，共 16 条；不含当前提问）
    # 先取历史再落库当前问题，避免把本轮问题混入上下文；顺序为时间正序（越早在前）
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in list_messages(session["id"])[-16:]
    ]

    # 记录用户消息
    add_message(session["id"], "user", req.question)

    async def gen():
        async for evt in _stream_events(session, req, stock_code, report_context, history):
            yield _sse(evt)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_events(session, req, stock_code, report_context, history):
    """产事件 dict 的异步生成器：后台线程跑问答，主协程实时转发队列事件

    - 线程内 on_event 发出 phase/tool_start/tool_done（实时）
    - 线程结束后由主协程发 error（失败）或 delta×N + done（成功）
    """
    queue = asyncio.Queue()

    def emit(evt):
        queue.put_nowait(evt)  # put_nowait 线程安全

    loop = asyncio.get_running_loop()
    task = loop.run_in_executor(
        None,
        lambda: run_qa_agent(
            req.question, stock_code, req.stock_name or session["stock_name"],
            report_context, [], history, on_event=emit,
        ),
    )

    # 实时转发线程内事件，直到线程结束且队列排空
    while not task.done() or not queue.empty():
        try:
            evt = queue.get_nowait()
        except asyncio.QueueEmpty:
            await asyncio.sleep(0.02)
            continue
        yield evt

    result = task.result()
    if not result["success"]:
        yield {"type": "error", "message": result["answer"]}
        add_message(session["id"], "assistant", result["answer"], None)
        return

    # tool_start/tool_done 已在线程内实时发出，此处不再重发
    answer = result["answer"]
    for chunk in _chunk_text(answer):
        yield {"type": "delta", "text": chunk}
        await asyncio.sleep(0.02)
    yield {"type": "done", "full": answer}
    add_message(session["id"], "assistant", answer, result["tool_calls"] or None)


def _build_report_context(report_id: int | None, stock_code: str) -> str:
    """构建注入报告上下文：优先指定报告，否则取该股最新报告"""
    row = None
    if report_id:
        row = get_stock_report_by_id(report_id)
    if row is None:
        from database import get_latest_report
        row = get_latest_report(stock_code)
    if row is None:
        return "（暂无报告）"
    # 提取报告结论摘要：summary 字段 + 评分/判断
    parts = [f"评分：{row.get('score', '')}", f"判断：{row.get('decision', '')}"]
    if row.get("summary"):
        parts.append(f"摘要：{row['summary']}")
    return "\n".join(parts)


def _chunk_text(text: str, size: int = 6) -> list[str]:
    """把回答切成小块（近似流式；中文字符按 6 字一块）"""
    if not text:
        return []
    return [text[i:i + size] for i in range(0, len(text), size)]
