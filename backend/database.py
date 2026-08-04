"""数据库操作 —— SQLAlchemy + MySQL"""

from datetime import date, datetime, timedelta
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

from config import DATABASE_URL

# ── 引擎与会话工厂 ──
_engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,   # 使用前 ping 连接，防 MySQL 断连
    "pool_recycle": 3600,    # 1 小时后回收连接
}
# SQLite 兼容（本地开发/测试用）
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
# MySQL 需要 pymysql 驱动
elif "mysql" in DATABASE_URL:
    import pymysql
    pymysql.install_as_MySQLdb()

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 个股报告全局存量上限（滑动窗口容量）
# 每存一份新报告，若存量超出该值，即删除最旧的报告，使窗口恒保持在最近 80 份
STOCK_REPORT_MAX = 80

# 滑动窗口防御保护下限：STOCK_REPORT_MAX 若被污染成低于此值（如测试残留的小值），
# 视为配置损坏，跳过删除防止误删真实数据
STOCK_REPORT_MIN_TRIM = 10


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖注入：获取数据库会话，请求结束后自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有表"""
    from models import Base as ModelsBase
    from ai_news_agent.models import AiNewsReport
    ModelsBase.metadata.create_all(bind=engine)


# ═══════════════════════════════════════════
# 股票分析报告
# ═══════════════════════════════════════════

def _extract_summary(report: dict) -> str:
    """从报告 JSON 中提取摘要文本，兼容新旧两种格式"""
    # 新格式（9模块）：从模块1提取 rating_sentence
    m1 = report.get("module_1_核心结论", {})
    if m1 and m1.get("rating_sentence"):
        return m1["rating_sentence"]
    # 旧格式兼容：直接取 summary 字段
    return report.get("summary", "")


def save_stock_report(stock_code: str, stock_name: str, report: dict,
                      markdown: str = "", token_used: int = 0,
                      debate_stats: str | None = None) -> int:
    """保存个股分析报告，返回报告 ID

    debate_stats: 双模型辩论过程 JSON 串（标准分析/降级报告为 null，前端角标据此显示）

    滑动窗口机制：全局报告存量按 STOCK_REPORT_MAX 封顶。
    新报告写入 = 右指针前进；若存量超出上限，左指针滑出最旧报告并删除，
    使窗口恒保持在最近 STOCK_REPORT_MAX 份。
    """
    import json
    from models import StockReport

    db = SessionLocal()
    try:
        obj = StockReport(
            stock_code=stock_code,
            stock_name=stock_name,
            score=report.get("score", 0),
            decision=report.get("decision", ""),
            summary=_extract_summary(report),
            report_json=json.dumps(report, ensure_ascii=False),
            markdown=markdown,
            token_used=token_used,
            debate_stats=debate_stats,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)

        # ── 滑动窗口：存量超上限时，删除最旧报告，保持窗口恒 ≤ STOCK_REPORT_MAX ──
        _trim_stock_reports(db)

        return obj.id
    finally:
        db.close()


def _trim_stock_reports(db: Session) -> int:
    """滑动窗口左指针：存量超上限时删除最旧报告，返回删除条数

    报告按 id 递增即按时间递增（新报告 id 更大）；删除最旧的 =
    按 id 升序删前 over 条，等价于窗口左边界右移。

    防御保护：若 STOCK_REPORT_MAX 被污染成异常小值（< 10），
    视为配置损坏，跳过删除，防止误删真实数据。
    """
    from models import StockReport

    if STOCK_REPORT_MAX < STOCK_REPORT_MIN_TRIM:
        print(f"[database] ⚠️ STOCK_REPORT_MAX={STOCK_REPORT_MAX} 低于下限 {STOCK_REPORT_MIN_TRIM}，跳过滑动窗口删除")
        return 0

    total = db.query(StockReport).count()
    over = total - STOCK_REPORT_MAX
    if over <= 0:
        return 0

    # 取最旧的 over 条（id 升序），滑出窗口并删除
    oldest = db.query(StockReport).order_by(StockReport.id.asc()).limit(over).all()
    for row in oldest:
        db.delete(row)
    db.commit()
    return len(oldest)


def get_stock_report_by_id(report_id: int) -> dict | None:
    """按 ID 获取报告"""
    from models import StockReport

    db = SessionLocal()
    try:
        row = db.query(StockReport).filter(StockReport.id == report_id).first()
        if row is None:
            return None
        return _model_to_dict(row)
    finally:
        db.close()


def get_latest_report(stock_code: str) -> dict | None:
    """获取指定股票的最新一份报告"""
    from models import StockReport

    db = SessionLocal()
    try:
        row = (
            db.query(StockReport)
            .filter(StockReport.stock_code == stock_code)
            .order_by(StockReport.id.desc())
            .first()
        )
        if row is None:
            return None
        return _model_to_dict(row)
    finally:
        db.close()


def get_recent_reports(stock_code: str, limit: int = 9) -> list[dict]:
    """获取某只股票最近 limit 份报告（按 id 倒序，最新在前）

    供 stock_agent/history.py 历史对比采样用；limit 默认 9 恰好覆盖
    奇数位采样最远位置（N≥6 时取 [1,3,5,7,9]）。
    """
    from models import StockReport

    db = SessionLocal()
    try:
        rows = (
            db.query(StockReport)
            .filter(StockReport.stock_code == stock_code)
            .order_by(StockReport.id.desc())
            .limit(limit)
            .all()
        )
        return [_model_to_dict(r) for r in rows]
    finally:
        db.close()


def get_stock_reports(
    page: int = 1,
    page_size: int = 10,
    search: str = "",
    date_from: str = "",
    date_to: str = "",
    decision: str = "",
) -> tuple[list, int]:
    """分页获取报告列表（按创建时间倒序，支持筛选）"""
    from models import StockReport

    db = SessionLocal()
    try:
        offset = (page - 1) * page_size
        query = db.query(StockReport)

        if search:
            query = query.filter(
                StockReport.stock_code.like(f"%{search}%")
                | StockReport.stock_name.like(f"%{search}%")
            )
        if date_from:
            query = query.filter(
                StockReport.created_at >= datetime.strptime(date_from, "%Y-%m-%d")
            )
        if date_to:
            next_day = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(StockReport.created_at < next_day)
        if decision:
            query = query.filter(StockReport.decision.like(f"%{decision}%"))

        total = query.count()
        rows = (
            query.order_by(StockReport.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return [_model_to_dict(r) for r in rows], total
    finally:
        db.close()


def delete_stock_report(stock_code: str, stock_name: str | None = None):
    """删除指定股票代码的所有报告（测试清理用）"""
    from models import StockReport

    db = SessionLocal()
    try:
        q = db.query(StockReport).filter(StockReport.stock_code == stock_code)
        if stock_name:
            q = q.filter(StockReport.stock_name == stock_name)
        deleted = q.delete()
        db.commit()
        return deleted
    finally:
        db.close()


# ═══════════════════════════════════════════
# 自选股管理
# ═══════════════════════════════════════════

def add_watchlist(stock_code: str, stock_name: str = "", notes: str = "") -> bool:
    """添加自选股，重复返回 False"""
    from models import StockWatchlist
    from sqlalchemy.exc import IntegrityError

    db = SessionLocal()
    try:
        db.add(StockWatchlist(
            stock_code=stock_code,
            stock_name=stock_name,
            notes=notes,
        ))
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False
    finally:
        db.close()


def get_watchlist() -> list[dict]:
    """获取自选股列表（按 sort_order 排序）"""
    from models import StockWatchlist

    db = SessionLocal()
    try:
        rows = (
            db.query(StockWatchlist)
            .order_by(StockWatchlist.sort_order.asc(), StockWatchlist.added_at.desc())
            .all()
        )
        return [_model_to_dict(r) for r in rows]
    finally:
        db.close()


def update_watchlist(stock_code: str, updates: dict) -> bool:
    """更新自选股字段（notes/enabled/sort_order/stock_name）"""
    from models import StockWatchlist

    db = SessionLocal()
    try:
        row = db.query(StockWatchlist).filter(StockWatchlist.stock_code == stock_code).first()
        if row is None:
            return False
        allowed = {"notes", "enabled", "sort_order", "stock_name"}
        for key, value in updates.items():
            if key in allowed and hasattr(row, key):
                setattr(row, key, value)
        db.commit()
        return True
    finally:
        db.close()


def delete_watchlist(stock_code: str) -> bool:
    """删除自选股"""
    from models import StockWatchlist

    db = SessionLocal()
    try:
        row = db.query(StockWatchlist).filter(StockWatchlist.stock_code == stock_code).first()
        if row is None:
            return False
        db.delete(row)
        db.commit()
        return True
    finally:
        db.close()


# ═══════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════

def _model_to_dict(obj) -> dict:
    """将 ORM 模型对象转为 dict"""
    d = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.key)
        if isinstance(val, (date, datetime)):
            val = str(val)
        d[col.key] = val
    return d
