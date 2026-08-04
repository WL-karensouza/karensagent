"""滑动窗口滚动删除测试

验证 save_stock_report 的滑动窗口机制：
- 存量超 STOCK_REPORT_MAX 时，删除最旧报告，窗口恒保持在最近 MAX 份
- 未超上限时，报告全部保留，不误删

为避免污染真实数据库（karens_agent.db），本测试使用独立内存库，
并在测试内临时调低 STOCK_REPORT_MAX 以方便构造超量场景。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows 控制台 UTF-8 编码兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def isolated_db(monkeypatch):
    """独立内存库：替换 database.SessionLocal，测试后自动还原"""
    import database
    from models import Base

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(engine)

    monkeypatch.setattr(database, "SessionLocal", TestSession)
    return TestSession


def test_slide_window_keeps_most_recent(isolated_db):
    """存量超上限时，删除最旧报告，窗口保持最近 MAX 份"""
    import database
    from database import save_stock_report

    # 调低窗口容量为 3，方便构造超量场景
    database.STOCK_REPORT_MAX = 3

    # 依次插入 5 条
    inserted = []
    for i in range(5):
        rid = save_stock_report(f"SW{i}", f"滑窗股{i}", {"score": i})
        inserted.append(rid)

    # 窗口应为最近 3 条：id 最大的 3 条保留，前 2 条被删
    from models import StockReport
    s = isolated_db()
    total = s.query(StockReport).count()
    remaining_ids = [r.id for r in s.query(StockReport).order_by(StockReport.id.asc()).all()]
    s.close()

    assert total == 3, f"存量应恒为 3，实际 {total}"
    assert remaining_ids == inserted[-3:], f"应保留最近 3 条 {inserted[-3:]}，实际 {remaining_ids}"


def test_no_trim_when_under_limit(isolated_db):
    """未超上限时，报告全部保留，不误删"""
    import database
    from database import save_stock_report

    database.STOCK_REPORT_MAX = 5

    inserted = []
    for i in range(3):
        rid = save_stock_report(f"UL{i}", f"未超限股{i}", {"score": i})
        inserted.append(rid)

    from models import StockReport
    s = isolated_db()
    total = s.query(StockReport).count()
    remaining_ids = [r.id for r in s.query(StockReport).order_by(StockReport.id.asc()).all()]
    s.close()

    assert total == 3, f"未超限应全部保留，实际 {total}"
    assert remaining_ids == inserted, f"应保留全部 {inserted}，实际 {remaining_ids}"


def test_slide_window_exact_boundary(isolated_db):
    """存量恰好等于上限时，不触发删除"""
    import database
    from database import save_stock_report

    database.STOCK_REPORT_MAX = 3

    inserted = []
    for i in range(3):
        rid = save_stock_report(f"BD{i}", f"边界股{i}", {"score": i})
        inserted.append(rid)

    from models import StockReport
    s = isolated_db()
    total = s.query(StockReport).count()
    s.close()

    assert total == 3, f"恰好等于上限应不删，实际 {total}"


def test_trim_exactly_over_by_one(isolated_db):
    """存量 4、上限 3：只删最旧 1 条，窗口回到 3"""
    import database
    from database import save_stock_report

    database.STOCK_REPORT_MAX = 3

    inserted = []
    for i in range(4):
        rid = save_stock_report(f"OV{i}", f"超1条股{i}", {"score": i})
        inserted.append(rid)

    from models import StockReport
    s = isolated_db()
    total = s.query(StockReport).count()
    remaining_ids = [r.id for r in s.query(StockReport).order_by(StockReport.id.asc()).all()]
    s.close()

    assert total == 3, f"超 1 条应删最旧 1 条，实际 {total}"
    assert remaining_ids == inserted[-3:], f"应保留最近 3 条，实际 {remaining_ids}"
