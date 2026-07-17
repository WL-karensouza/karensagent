"""Karens Agent —— FastAPI 入口

启动命令: uvicorn main:app --host 0.0.0.0 --port 8900 --reload
"""

import sys
import os
import atexit

# Windows 控制台 UTF-8 编码（防止 emoji 导致启动崩溃）
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, seed_keywords


# ── 生命周期管理 ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭时的初始化与清理"""
    # 启动
    print("[main] 🚀 Karens Agent 启动中...")
    init_db()
    seed_keywords()
    print("[main] ✅ 数据库初始化完成")

    # 启动定时任务
    from scheduler import start_scheduler
    start_scheduler()

    print("[main] ✅ 全部就绪")
    yield
    # 关闭
    from scheduler import stop_scheduler
    stop_scheduler()
    print("[main] 🛑 Karens Agent 已关闭")


app = FastAPI(
    title="Karens Agent",
    description="多智能体平台 — GitHub 热榜 + 股票分析",
    version="1.2.0",
    lifespan=lifespan,
)

# ── CORS 中间件 ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API 路由注册 ──
from routers.dashboard import router as dashboard_router
from routers.history import router as history_router
from routers.preview import router as preview_router
from routers.trigger import router as trigger_router
from routers.config_api import router as config_router
from routers.stock_api import router as stock_router

app.include_router(dashboard_router)
app.include_router(history_router)
app.include_router(preview_router)
app.include_router(trigger_router)
app.include_router(config_router)
app.include_router(stock_router)


# ── 根路径 ──
@app.get("/api/health")
def health_check():
    """健康检查 — 含 iFinD MCP 连通性探测"""
    ifind_ok = False
    try:
        from stock_agent.skill import call_skill
        call_skill("stock", "stock_highfreq_quotes", {
            "symbols": "600519.SH",
            "indicators": "latest",
            "data_mode": "latest",
        })
        ifind_ok = True
    except Exception:
        pass
    return {"status": "ok", "ifind": ifind_ok}


# ── 前端静态文件（前后端一体部署） ──
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# ── 直接运行入口 ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8900)
