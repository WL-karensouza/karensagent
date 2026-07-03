#!/bin/bash
# ========================================
# Karens Agent 一键部署脚本
# 使用: bash deploy.sh
# ========================================
set -e

PROJECT_DIR="/opt/karens-agent"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
SERVICE_NAME="karens-agent"

echo "🚀 Karens Agent 部署开始..."

# ── 1. 安装系统依赖 ──
echo "[1/6] 安装系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv nginx

# ── 2. 创建虚拟环境并安装 Python 依赖 ──
echo "[2/6] 安装 Python 依赖..."
cd "$BACKEND_DIR"
python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt

# ── 3. 初始化数据库 ──
echo "[3/6] 初始化数据库..."
python3 -c "from database import init_db, seed_keywords; init_db(); seed_keywords()"
echo "✅ 数据库初始化完成"

# ── 4. 构建前端 ──
if [ -d "$FRONTEND_DIR" ]; then
    echo "[4/6] 构建前端..."
    cd "$FRONTEND_DIR"
    npm install --silent
    npm run build
    echo "✅ 前端构建完成"
else
    echo "[4/6] 跳过前端（无前端目录）"
fi

# ── 5. 配置 systemd 服务 ──
echo "[5/6] 配置 systemd 服务..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Karens Agent - 每日热榜推送
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin:/usr/bin"
ExecStart=$BACKEND_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8900
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME
echo "✅ systemd 服务已配置"

# ── 6. 配置 Nginx 反代 ──
echo "[6/6] 配置 Nginx..."
sudo tee /etc/nginx/sites-available/$SERVICE_NAME > /dev/null <<'NGINX'
server {
    listen 80;
    server_name _;  # 替换为你的域名

    location / {
        proxy_pass http://127.0.0.1:8900;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/$SERVICE_NAME /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
echo "✅ Nginx 配置完成"

# ── 完成 ──
echo ""
echo "========================================"
echo "🎉 Karens Agent 部署完成！"
echo ""
echo "📍 后端 API: http://localhost:8900"
echo "📍 健康检查: http://localhost:8900/api/health"
echo "📍 仪表盘:   http://localhost:8900/api/dashboard/stats"
echo ""
echo "📋 常用命令:"
echo "  sudo systemctl status $SERVICE_NAME   # 查看状态"
echo "  sudo systemctl restart $SERVICE_NAME  # 重启服务"
echo "  sudo journalctl -u $SERVICE_NAME -f   # 查看日志"
echo ""
echo "⚙️  编辑配置: vim $BACKEND_DIR/.env"
echo "========================================"
