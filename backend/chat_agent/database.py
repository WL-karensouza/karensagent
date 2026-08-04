"""投研 AI 问答 —— 数据库操作"""
import json
from database import SessionLocal, _model_to_dict


def get_or_create_session(stock_code: str, stock_name: str = "") -> dict:
    """按股票代码获取会话，不存在则创建（每只股票一个活跃会话）

    返回 _model_to_dict 后的会话 dict。
    """
    from models import ChatSession

    db = SessionLocal()
    try:
        row = db.query(ChatSession).filter(ChatSession.stock_code == stock_code).first()
        if row is None:
            row = ChatSession(stock_code=stock_code, stock_name=stock_name)
            db.add(row)
            db.commit()
            db.refresh(row)
        return _model_to_dict(row)
    finally:
        db.close()


def get_session(session_id: int) -> dict | None:
    """按 ID 获取会话"""
    from models import ChatSession

    db = SessionLocal()
    try:
        row = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        return _model_to_dict(row) if row else None
    finally:
        db.close()


def update_session_report(session_id: int, report_id: int | None) -> None:
    """更新会话锚定的报告 ID（进入报告页时调用）"""
    from models import ChatSession

    db = SessionLocal()
    try:
        row = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if row:
            row.report_id = report_id
            db.commit()
    finally:
        db.close()


def add_message(session_id: int, role: str, content: str,
                tool_calls: list | None = None) -> dict:
    """追加一条消息，返回 _model_to_dict 结果"""
    from models import ChatMessage

    db = SessionLocal()
    try:
        obj = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _model_to_dict(obj)
    finally:
        db.close()


def list_messages(session_id: int, limit: int = 100) -> list[dict]:
    """获取会话消息列表（按时间正序，limit 默认 100 条）"""
    from models import ChatMessage

    db = SessionLocal()
    try:
        rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
            .limit(limit)
            .all()
        )
        return [_model_to_dict(r) for r in rows]
    finally:
        db.close()
