#!/bin/bash
#=============================================================================
# MiroFish + BettaFish 一鍵部署腳本 (Vultr VPS)
#
# 使用方式：
#   1. SSH 連上你的伺服器: ssh root@139.180.189.56
#   2. 複製貼上這整個腳本執行，或：
#      curl -sSL <raw_url> | bash
#   3. 部署完成後編輯 .env 填入你的 API Key
#
# 部署內容：
#   - MiroFish (port 3000 前端 + port 5001 後端)
#   - BettaFish (port 5000)
#   - 2GB Swap (防止記憶體不足)
#=============================================================================

set -e

echo "============================================"
echo "  MiroFish + BettaFish 一鍵部署腳本"
echo "  目標伺服器: $(hostname) ($(curl -s ifconfig.me 2>/dev/null || echo 'unknown'))"
echo "============================================"
echo ""

#-----------------------------------------------------------------------------
# Step 0: 系統更新 & 基礎工具
#-----------------------------------------------------------------------------
echo "[0/7] 系統更新 & 安裝基礎工具..."
apt-get update -qq
apt-get install -y -qq git curl wget unzip software-properties-common > /dev/null 2>&1
echo "  ✓ 基礎工具安裝完成"

#-----------------------------------------------------------------------------
# Step 1: 加 Swap (僅記憶體 < 8G 時需要)
#-----------------------------------------------------------------------------
TOTAL_MEM_MB=$(free -m | awk '/^Mem:/{print $2}')
echo "[1/7] 檢查記憶體 (${TOTAL_MEM_MB}MB)..."
if [ "$TOTAL_MEM_MB" -lt 8192 ] && [ ! -f /swapfile ]; then
    echo "  記憶體 < 8GB，建立 2GB Swap..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile > /dev/null
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "  ✓ 2GB Swap 已建立並啟用"
else
    echo "  ✓ 記憶體充足 (${TOTAL_MEM_MB}MB)，無需 Swap"
fi

#-----------------------------------------------------------------------------
# Step 2: 安裝 Docker & Docker Compose
#-----------------------------------------------------------------------------
echo "[2/7] 安裝 Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh > /dev/null 2>&1
    systemctl enable docker
    systemctl start docker
    echo "  ✓ Docker 安裝完成 ($(docker --version))"
else
    echo "  ✓ Docker 已安裝 ($(docker --version))"
fi

#-----------------------------------------------------------------------------
# Step 3: Clone MiroFish
#-----------------------------------------------------------------------------
echo "[3/7] 部署 MiroFish..."
MIROFISH_DIR="/opt/mirofish"
if [ ! -d "$MIROFISH_DIR" ]; then
    git clone https://github.com/666ghj/MiroFish.git "$MIROFISH_DIR"
    echo "  ✓ MiroFish clone 完成"
else
    cd "$MIROFISH_DIR" && git pull origin main
    echo "  ✓ MiroFish 已存在，已更新"
fi

# 建立 .env（佔位符）
cat > "$MIROFISH_DIR/.env" << 'ENVEOF'
# ===== MiroFish 環境變數 =====
# 部署完成後請填入你的 API Key！

# LLM API 配置（支援 OpenAI SDK 格式的任意 LLM API）
# 推薦選項：
#   阿里雲百煉 (qwen-plus): https://bailian.console.aliyun.com/
#   OpenAI (gpt-4o-mini):    https://platform.openai.com/api-keys
#   DeepSeek (deepseek-chat): https://platform.deepseek.com/
LLM_API_KEY=your_llm_api_key_here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus

# Zep 記憶圖譜配置
# 免費註冊：https://app.getzep.com/
ZEP_API_KEY=your_zep_api_key_here

# 加速 LLM（可選，不需要就刪掉下面三行）
# LLM_BOOST_API_KEY=
# LLM_BOOST_BASE_URL=
# LLM_BOOST_MODEL_NAME=
ENVEOF
echo "  ✓ MiroFish .env 已建立（需填入 API Key）"

#-----------------------------------------------------------------------------
# Step 4: Clone BettaFish
#-----------------------------------------------------------------------------
echo "[4/7] 部署 BettaFish..."
BETTAFISH_DIR="/opt/bettafish"
if [ ! -d "$BETTAFISH_DIR" ]; then
    git clone https://github.com/virus11456/BettaFish.git "$BETTAFISH_DIR"
    echo "  ✓ BettaFish clone 完成"
else
    cd "$BETTAFISH_DIR" && git pull origin main 2>/dev/null || git pull
    echo "  ✓ BettaFish 已存在，已更新"
fi

# 建立 BettaFish .env（佔位符）
if [ -f "$BETTAFISH_DIR/.env.example" ]; then
    cp "$BETTAFISH_DIR/.env.example" "$BETTAFISH_DIR/.env"
    echo "  ✓ BettaFish .env 已從 .env.example 建立（需填入配置）"
else
    cat > "$BETTAFISH_DIR/.env" << 'ENVEOF'
# ===== BettaFish 環境變數 =====
# 請參考 BettaFish README 填入配置

# 資料庫配置
DB_HOST=db
DB_PORT=5432
DB_USER=bettafish
DB_PASSWORD=bettafish
DB_NAME=bettafish

# LLM 配置（各 Engine 可獨立配置）
# InsightEngine - 推薦 Moonshot/Kimi
INSIGHT_API_KEY=your_key_here
# QueryEngine - 推薦 DeepSeek
QUERY_API_KEY=your_key_here
# ReportEngine - 推薦 Gemini
REPORT_API_KEY=your_key_here

# 搜索 API（擇一即可）
TAVILY_API_KEY=your_tavily_key_here
ENVEOF
    echo "  ✓ BettaFish .env 已建立（需填入配置）"
fi

#-----------------------------------------------------------------------------
# Step 5: 建立統一 docker-compose（同時跑兩個服務）
#-----------------------------------------------------------------------------
echo "[5/7] 建立統一 Docker Compose..."
cat > /opt/docker-compose.yml << 'DCEOF'
#=============================================================================
# MiroFish + BettaFish 統一 Docker Compose
#=============================================================================
services:

  #---------------------------------------------------------------------------
  # MiroFish — AI 預測引擎
  #   前端: http://<your-ip>:3000
  #   後端: http://<your-ip>:5001
  #---------------------------------------------------------------------------
  mirofish:
    image: ghcr.io/666ghj/mirofish:latest
    container_name: mirofish
    env_file:
      - /opt/mirofish/.env
    ports:
      - "3000:3000"
      - "5001:5001"
    restart: unless-stopped
    volumes:
      - /opt/mirofish/backend/uploads:/app/backend/uploads

  #---------------------------------------------------------------------------
  # BettaFish — 輿情監控系統
  #   前端: http://<your-ip>:5000
  #---------------------------------------------------------------------------
  bettafish-db:
    image: postgres:15-alpine
    container_name: bettafish-db
    environment:
      POSTGRES_USER: bettafish
      POSTGRES_PASSWORD: bettafish
      POSTGRES_DB: bettafish
    volumes:
      - bettafish_pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  bettafish:
    build:
      context: /opt/bettafish
      dockerfile: Dockerfile
    container_name: bettafish
    env_file:
      - /opt/bettafish/.env
    ports:
      - "5000:5000"
    depends_on:
      - bettafish-db
    restart: unless-stopped
    volumes:
      - /opt/bettafish/final_reports:/app/final_reports
      - /opt/bettafish/logs:/app/logs

volumes:
  bettafish_pgdata:
DCEOF
echo "  ✓ 統一 docker-compose.yml 已建立"

#-----------------------------------------------------------------------------
# Step 6: 啟動 MiroFish（先啟動，BettaFish 等填完配置再啟動）
#-----------------------------------------------------------------------------
echo "[6/7] 拉取 MiroFish Docker 映像..."
cd /opt
docker compose pull mirofish 2>&1 | tail -3
echo "  ✓ MiroFish 映像拉取完成"

# 先只啟動 MiroFish（不需要額外 build）
# BettaFish 需要 build 且需要填配置，先不啟動
echo "  ⚠ 暫不啟動服務 — 需先填入 API Key"

#-----------------------------------------------------------------------------
# Step 7: 設定防火牆
#-----------------------------------------------------------------------------
echo "[7/7] 設定防火牆..."
if command -v ufw &> /dev/null; then
    ufw allow 22/tcp   > /dev/null 2>&1
    ufw allow 3000/tcp > /dev/null 2>&1  # MiroFish 前端
    ufw allow 5001/tcp > /dev/null 2>&1  # MiroFish 後端
    ufw allow 5000/tcp > /dev/null 2>&1  # BettaFish
    ufw --force enable > /dev/null 2>&1
    echo "  ✓ 防火牆已開放 22, 3000, 5000, 5001 端口"
else
    echo "  ✓ 未安裝 ufw，跳過（Vultr 請在控制台設定安全組）"
fi

#=============================================================================
# 完成！
#=============================================================================
echo ""
echo "============================================"
echo "  部署準備完成！"
echo "============================================"
echo ""
echo "  檔案位置："
echo "    MiroFish:  /opt/mirofish/"
echo "    BettaFish: /opt/bettafish/"
echo "    Compose:   /opt/docker-compose.yml"
echo ""
echo "  ⚡ 接下來你需要做的："
echo ""
echo "  1. 編輯 MiroFish 配置（必須）："
echo "     nano /opt/mirofish/.env"
echo "     → 填入 LLM_API_KEY 和 ZEP_API_KEY"
echo ""
echo "  2. 編輯 BettaFish 配置（必須）："
echo "     nano /opt/bettafish/.env"
echo "     → 填入各 Engine 的 API Key"
echo ""
echo "  3. 啟動所有服務："
echo "     cd /opt && docker compose up -d"
echo ""
echo "  4. 或只啟動 MiroFish："
echo "     cd /opt && docker compose up -d mirofish"
echo ""
echo "  5. 訪問："
echo "     MiroFish:  http://139.180.189.56:3000"
echo "     BettaFish: http://139.180.189.56:5000"
echo ""
echo "  📋 常用命令："
echo "     查看日誌:  cd /opt && docker compose logs -f"
echo "     停止服務:  cd /opt && docker compose down"
echo "     重啟服務:  cd /opt && docker compose restart"
echo "     查看狀態:  cd /opt && docker compose ps"
echo ""
echo "  ⚠ 安全提醒："
echo "     部署完成後請立即更改 root 密碼: passwd"
echo ""
echo "============================================"
