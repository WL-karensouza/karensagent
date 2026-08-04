"""测试全局配置 —— 将所有测试切换到 SQLite，隔离真实 MySQL

关键点：config._load_env() 在导入时会把 .env 的 MySQL 地址写进 os.environ，
因此仅 setenv 会失效。这里通过直接改 config.DATABASE_URL 模块属性强制切到
sqlite 文件库（conftest 顶层先于所有测试模块加载，保证生效）。

测试库：backend/tests/_test_karens.db（*.db 已被根 .gitignore 忽略）
"""

import os
import sys
import pytest

# 让测试能 import backend 包内模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试专用 SQLite 文件库路径
_TEST_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_karens.db")
_TEST_DB_URL = f"sqlite:///{_TEST_DB.replace(os.sep, '/')}"

# ① 改 config 模块属性（决定性，config._load_env 覆盖 env 也无效）
import config
config.DATABASE_URL = _TEST_DB_URL

# ② 双保险：同时写入环境变量（其他模块若直接读 os.environ 也拿到 sqlite）
os.environ["DATABASE_URL"] = _TEST_DB_URL

# ③ 立即建表（sqlite 引擎），保证后续测试直接可用
from database import init_db
init_db()

# ④ 禁用 ai_news 后台调度器：main.py lifespan 会启动 APScheduler 定时任务，
#    测试环境不应启动真实调度器（否则后台线程在 pytest 关闭捕获后写 stdout，
#    触发 "I/O operation on closed file" 错误）
import ai_news_agent.scheduler as _sched
_sched.start_scheduler = lambda: None
_sched.stop_scheduler = lambda: None


@pytest.fixture(autouse=True)
def _clean_tables():
    """每个测试前清空报告与自选股表，防止测试间残留数据相互干扰"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        from models import StockReport, StockWatchlist
        db.query(StockReport).delete()
        db.query(StockWatchlist).delete()
        db.commit()
    finally:
        db.close()
    yield
