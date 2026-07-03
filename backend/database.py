"""数据库操作 —— SQLAlchemy + MySQL"""

import re
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

# 匹配 4 字节 UTF-8 字符（emoji 等），MySQL utf8 不支持
_EMOJI_RE = re.compile(r'[\U00010000-\U0010FFFF]', re.UNICODE)


def _strip_emoji(val):
    """移除 4 字节 UTF-8 字符，MySQL utf8 无法存储"""
    if isinstance(val, str):
        return _EMOJI_RE.sub('', val)
    return val
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
    ModelsBase.metadata.create_all(bind=engine)


def seed_keywords():
    """初始化关键词数据（幂等操作）—— 纯列表无权重"""
    from models import Keyword
    from config import DEFAULT_KEYWORDS

    db = SessionLocal()
    try:
        for kw in DEFAULT_KEYWORDS:
            existing = db.query(Keyword).filter(Keyword.keyword == kw).first()
            if not existing:
                db.add(Keyword(keyword=kw, score=0, enabled=1))
        db.commit()
    finally:
        db.close()


# ═══════════════════════════════════════════
# 日榜操作
# ═══════════════════════════════════════════

def save_daily_trends(repos: list[dict], source: str = "daily", fetch_date: str = ""):
    """批量保存 Trend 数据（去重：同 repo_name + fetch_date + source 跳过）

    source 参数仅作为 fallback：如果记录自身没有 source 字段，则使用此参数。
    每条记录优先使用自身的 source（如 daily/weekly/monthly）。
    """
    from models import DailyTrend
    from sqlalchemy.exc import IntegrityError

    db = SessionLocal()
    try:
        added = 0
        fetch_d = datetime.strptime(fetch_date, "%Y-%m-%d").date()

        # 批量查询已存在的记录，避免 autoflush=False 带来的重复检测失效
        existing_keys = set(
            (row[0], row[2]) for row in db.query(
                DailyTrend.repo_name, DailyTrend.fetch_date, DailyTrend.source
            ).filter(
                DailyTrend.repo_name.in_([r["repo_name"] for r in repos]),
                DailyTrend.fetch_date == fetch_d,
            ).all()
        )
        seen = set(existing_keys)

        for r in repos:
            record_source = r.get("source", source)
            key = (r["repo_name"], record_source)
            if key in seen:
                continue
            seen.add(key)
            db.add(DailyTrend(
                repo_name=r["repo_name"],
                repo_url=r["repo_url"],
                description=_strip_emoji(r.get("description", "")),
                language=r.get("language", ""),
                stars_today=r.get("stars_today", 0),
                total_stars=r.get("total_stars", 0),
                rank=r.get("rank", 0),
                source=record_source,
                fetch_date=fetch_d,
            ))
            added += 1

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # 兜底：逐条插入
            added = 0
            for r in repos:
                record_source = r.get("source", source)
                try:
                    db.add(DailyTrend(
                        repo_name=r["repo_name"],
                        repo_url=r["repo_url"],
                        description=_strip_emoji(r.get("description", "")),
                        language=r.get("language", ""),
                        stars_today=r.get("stars_today", 0),
                        total_stars=r.get("total_stars", 0),
                        rank=r.get("rank", 0),
                        source=record_source,
                        fetch_date=fetch_d,
                    ))
                    db.flush()
                    added += 1
                except IntegrityError:
                    db.rollback()
                    continue
            db.commit()

        print(f"[db] save_daily_trends: 新增 {added} 条，跳过 {len(repos) - added} 条重复")
    finally:
        db.close()


def get_trends_by_source(source: str, fetch_date: str, top_n: int = 50):
    """直接读取 GitHub 官方排名（按 source 过滤，如 weekly/monthly）

    GitHub Trending 页面自身已按 stars 排序，这里直接读取原始排名，
    不做任何二次聚合或重算，保证与 GitHub 页面一致。
    """
    from models import DailyTrend

    db = SessionLocal()
    try:
        fetch_d = datetime.strptime(fetch_date, "%Y-%m-%d").date()
        rows = (
            db.query(DailyTrend)
            .filter(
                DailyTrend.source == source,
                DailyTrend.fetch_date == fetch_d,
            )
            .order_by(DailyTrend.stars_today.desc())
            .limit(top_n)
            .all()
        )
        return [_model_to_dict(r) for r in rows]
    finally:
        db.close()


def get_weekly_trends(end_date: str, top_n: int = 50, min_score: int = 0):
    """获取最近一周的 Trend，按周 stars 降序"""
    from models import DailyTrend

    db = SessionLocal()
    try:
        start = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=7)).date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        rows = (
            db.query(
                DailyTrend.repo_name,
                DailyTrend.repo_url,
                DailyTrend.description,
                DailyTrend.language,
                func.sum(DailyTrend.stars_today).label("week_stars"),
                func.max(DailyTrend.total_stars).label("max_total_stars"),
                func.count(DailyTrend.id).label("appear_days"),
            )
            .filter(DailyTrend.fetch_date >= start, DailyTrend.fetch_date <= end)
            .group_by(DailyTrend.repo_name)
            .order_by(func.sum(DailyTrend.stars_today).desc())
            .limit(top_n)
            .all()
        )
        return [_row_to_dict(r) for r in rows]
    finally:
        db.close()


def get_monthly_trends(end_date: str, top_n: int = 50, min_score: int = 0):
    """获取最近一个月的 Trend"""
    from models import DailyTrend

    db = SessionLocal()
    try:
        start = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=30)).date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        rows = (
            db.query(
                DailyTrend.repo_name,
                DailyTrend.repo_url,
                DailyTrend.description,
                DailyTrend.language,
                func.sum(DailyTrend.stars_today).label("month_stars"),
                func.max(DailyTrend.total_stars).label("max_total_stars"),
                func.count(DailyTrend.id).label("appear_days"),
            )
            .filter(DailyTrend.fetch_date >= start, DailyTrend.fetch_date <= end)
            .group_by(DailyTrend.repo_name)
            .order_by(func.sum(DailyTrend.stars_today).desc())
            .limit(top_n)
            .all()
        )
        return [_row_to_dict(r) for r in rows]
    finally:
        db.close()


# ═══════════════════════════════════════════
# AI 资讯操作
# ═══════════════════════════════════════════

def save_ai_news(news_items: list[dict], date: str = ""):
    """批量保存 AI 资讯（内存去重 + IntegrityError 兜底，幂等安全）"""
    from models import AiNews
    from sqlalchemy.exc import IntegrityError

    db = SessionLocal()
    try:
        added = 0
        fetch_d = datetime.strptime(date, "%Y-%m-%d").date()

        # 先批量查询数据库中已存在的 URL（一次查询替代 N 次）
        urls = [n["url"] for n in news_items if n.get("url")]
        existing_urls = set(
            row[0] for row in
            db.query(AiNews.url).filter(
                AiNews.url.in_(urls),
                AiNews.fetch_date == fetch_d,
            ).all()
        )

        # 内存中已加入本批次去重
        seen_in_batch = set(existing_urls)

        for n in news_items:
            url = n.get("url", "")
            if not url or url in seen_in_batch:
                continue
            seen_in_batch.add(url)
            db.add(AiNews(
                title=_strip_emoji(n["title"]),
                url=url,
                source=n["source"],
                score=n.get("score", 0),
                summary=_strip_emoji(n.get("summary", "")),
                fetch_date=fetch_d,
            ))
            added += 1

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # 兜底：逐条插入，遇到重复跳过
            added = 0
            for n in news_items:
                url = n.get("url", "")
                if not url:
                    continue
                try:
                    db.add(AiNews(
                        title=_strip_emoji(n["title"]),
                        url=url,
                        source=n["source"],
                        score=n.get("score", 0),
                        summary=_strip_emoji(n.get("summary", "")),
                        fetch_date=fetch_d,
                    ))
                    db.flush()
                    added += 1
                except IntegrityError:
                    db.rollback()
                    continue
            db.commit()

        print(f"[db] save_ai_news: 新增 {added} 条（跳过 {len(news_items) - added} 条重复）")
    finally:
        db.close()


def mark_news_pushed(news_urls: list[str], fetch_date: str):
    """标记已推送的 AI 资讯（按 URL + fetch_date 匹配）"""
    from models import AiNews

    db = SessionLocal()
    try:
        fetch_d = datetime.strptime(fetch_date, "%Y-%m-%d").date()
        updated = (
            db.query(AiNews)
            .filter(AiNews.url.in_(news_urls), AiNews.fetch_date == fetch_d)
            .update({AiNews.is_pushed: 1}, synchronize_session=False)
        )
        db.commit()
        print(f"[db] mark_news_pushed: 标记 {updated} 条已推送")
    finally:
        db.close()


def get_ai_news(end_date: str, top_n: int = 30):
    """获取最近一周的 AI 资讯"""
    from models import AiNews

    db = SessionLocal()
    try:
        start = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=7)).date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        rows = (
            db.query(AiNews)
            .filter(AiNews.fetch_date >= start, AiNews.fetch_date <= end)
            .order_by(AiNews.score.desc())
            .limit(top_n)
            .all()
        )
        return [_model_to_dict(r) for r in rows]
    finally:
        db.close()


# ═══════════════════════════════════════════
# 推送历史
# ═══════════════════════════════════════════

def save_push_history(platform: str, content_type: str, content: str,
                      repo_count: int = 0, news_count: int = 0,
                      status: str = "sent"):
    """记录推送历史"""
    from models import PushHistory

    db = SessionLocal()
    try:
        db.add(PushHistory(
            platform=platform,
            content_type=content_type,
            content=_strip_emoji(content),
            repo_count=repo_count,
            news_count=news_count,
            status=status,
        ))
        db.commit()
    finally:
        db.close()


def get_push_history(limit: int = 30):
    """获取推送历史列表"""
    from models import PushHistory

    db = SessionLocal()
    try:
        rows = (
            db.query(PushHistory)
            .order_by(PushHistory.push_time.desc())
            .limit(limit)
            .all()
        )
        return [_model_to_dict(r) for r in rows]
    finally:
        db.close()


# ═══════════════════════════════════════════
# 仪表盘统计
# ═══════════════════════════════════════════

def get_dashboard_stats():
    """仪表盘统计"""
    from models import DailyTrend, AiNews, PushHistory

    db = SessionLocal()
    try:
        today = date.today()
        week_ago = today - timedelta(days=7)

        today_cnt = db.query(func.count(DailyTrend.id)).filter(
            DailyTrend.fetch_date == today
        ).scalar() or 0

        today_news_cnt = db.query(func.count(AiNews.id)).filter(
            AiNews.fetch_date == today
        ).scalar() or 0

        week_news_cnt = db.query(func.count(AiNews.id)).filter(
            AiNews.fetch_date >= week_ago
        ).scalar() or 0

        today_pushes = db.query(func.count(PushHistory.id)).filter(
            func.date(PushHistory.push_time) == today
        ).scalar() or 0

        last_push = db.query(PushHistory.push_time).order_by(
            PushHistory.push_time.desc()
        ).first()
        last_push_str = last_push[0].strftime("%Y-%m-%d %H:%M") if last_push else None

        return {
            "today_repos": today_cnt,
            "week_unique_repos": None,   # 占位，后续版本实现
            "week_news": week_news_cnt,
            "last_push": last_push_str,
            "today_news": today_news_cnt,
            "today_pushes": today_pushes,
        }
    finally:
        db.close()


# ═══════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════

def _row_to_dict(row) -> dict:
    """将 SQLAlchemy 聚合查询结果转为 dict"""
    d = {}
    for field in row._mapping:
        val = row._mapping[field]
        if isinstance(val, (date, datetime)):
            val = str(val)
        d[field] = val
    return d


def _model_to_dict(obj) -> dict:
    """将 ORM 模型对象转为 dict"""
    d = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.key)
        if isinstance(val, (date, datetime)):
            val = str(val)
        d[col.key] = val
    return d
