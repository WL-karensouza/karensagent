"""GitHub Agent —— FastAPI 入口

启动命令: uvicorn main:app --host 0.0.0.0 --port 8900 --reload
"""

import os
import atexit
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
    print("[main] 🚀 GitHub Agent 启动中...")
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
    print("[main] 🛑 GitHub Agent 已关闭")


app = FastAPI(
    title="GitHub Agent",
    description="每日 GitHub 热榜 + AI 前沿资讯推送",
    version="1.1.0",
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

app.include_router(dashboard_router)
app.include_router(history_router)
app.include_router(preview_router)
app.include_router(trigger_router)
app.include_router(config_router)


# ── 根路径 ──
@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "GitHub Agent", "version": "1.1.0"}


# ── 前端静态文件（前后端一体部署） ──
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# ── 直接运行入口 ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8900)
