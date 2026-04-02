#!/bin/bash
#=============================================================================
# MiroFish + BettaFish 完整部署指令
# 伺服器: 139.180.189.56 (Vultr Singapore, 12vCPU / 24GB RAM)
#
# 使用方式:
#   ssh root@139.180.189.56
#   然後複製下面的指令分段執行
#=============================================================================

#-----------------------------------------------------------------------------
# Part 1: 系統準備 (複製整段執行)
#-----------------------------------------------------------------------------
apt-get update -qq && \
apt-get install -y -qq git curl wget unzip > /dev/null 2>&1 && \
echo "✓ 系統更新完成"

# 安裝 Docker
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh > /dev/null 2>&1
    systemctl enable docker && systemctl start docker
fi
echo "✓ Docker: $(docker --version)"

#-----------------------------------------------------------------------------
# Part 2: Clone 專案 (複製整段執行)
#-----------------------------------------------------------------------------
git clone https://github.com/666ghj/MiroFish.git /opt/mirofish
git clone https://github.com/virus11456/BettaFish.git /opt/bettafish
echo "✓ 兩個專案已 clone"

#-----------------------------------------------------------------------------
# Part 3: 建立 MiroFish .env (複製整段執行)
#-----------------------------------------------------------------------------
cat > /opt/mirofish/.env << 'EOF'
LLM_API_KEY=sk-ebc1d137772040cabc536dd17d2bf7b6
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus
ZEP_API_KEY=z_1dWlkIjoiNmYxYjRlY2UtNTA4Yy00YmU5LThmMDktNDRjNGQxYjAyN2FkIn0.FVCYTUmdtwvZK4bLAR0Q_oN488JjeAVxL-GuK0F_fwv2eCDQwpoHAL_DHLHiDROxI5oVqJ90Hnwo9sXHlaXgMQ
EOF
echo "✓ MiroFish .env 已建立"

#-----------------------------------------------------------------------------
# Part 4: 建立 BettaFish .env (複製整段執行)
#-----------------------------------------------------------------------------
if [ -f /opt/bettafish/.env.example ]; then
    cp /opt/bettafish/.env.example /opt/bettafish/.env
fi
# 追加/覆寫關鍵配置
cat >> /opt/bettafish/.env << 'EOF'

# === 手動追加的配置 ===
QUERY_API_KEY=sk-6fdfebecdea74a4a8d8fa6aeb0a94d2e
QUERY_BASE_URL=https://api.deepseek.com
QUERY_MODEL_NAME=deepseek-chat

INSIGHT_API_KEY=sk-6fdfebecdea74a4a8d8fa6aeb0a94d2e
INSIGHT_BASE_URL=https://api.deepseek.com
INSIGHT_MODEL_NAME=deepseek-chat

REPORT_API_KEY=sk-ebc1d137772040cabc536dd17d2bf7b6
REPORT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
REPORT_MODEL_NAME=qwen-plus

TAVILY_API_KEY=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
EOF
echo "✓ BettaFish .env 已建立"

#-----------------------------------------------------------------------------
# Part 5: 建立統一 docker-compose.yml (複製整段執行)
#-----------------------------------------------------------------------------
cat > /opt/docker-compose.yml << 'DCEOF'
services:
  # MiroFish — AI 預測引擎
  # 前端: http://139.180.189.56:3000
  # 後端 API: http://139.180.189.56:5001
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

  # BettaFish — 輿情監控系統
  # 前端: http://139.180.189.56:5000
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
echo "✓ docker-compose.yml 已建立"

#-----------------------------------------------------------------------------
# Part 6: 啟動服務 (複製整段執行)
#-----------------------------------------------------------------------------
cd /opt

# 先啟動 MiroFish（直接拉映像，最快）
docker compose up -d mirofish
echo "✓ MiroFish 啟動中..."

# 再啟動 BettaFish（需要 build，較慢）
docker compose up -d --build bettafish-db bettafish
echo "✓ BettaFish 啟動中..."

# 查看狀態
docker compose ps

#-----------------------------------------------------------------------------
# Part 7: 防火牆 (複製整段執行)
#-----------------------------------------------------------------------------
if command -v ufw &> /dev/null; then
    ufw allow 22/tcp > /dev/null 2>&1
    ufw allow 3000/tcp > /dev/null 2>&1
    ufw allow 5000/tcp > /dev/null 2>&1
    ufw allow 5001/tcp > /dev/null 2>&1
    ufw --force enable > /dev/null 2>&1
    echo "✓ 防火牆已開放端口"
fi

#-----------------------------------------------------------------------------
# 完成！
#-----------------------------------------------------------------------------
echo ""
echo "============================================"
echo "  部署完成！"
echo "============================================"
echo ""
echo "  MiroFish:  http://139.180.189.56:3000"
echo "  BettaFish: http://139.180.189.56:5000"
echo ""
echo "  常用命令："
echo "    查看日誌: cd /opt && docker compose logs -f"
echo "    查看狀態: cd /opt && docker compose ps"
echo "    重啟:     cd /opt && docker compose restart"
echo "    停止:     cd /opt && docker compose down"
echo ""
echo "  ⚠ 請立即更改 root 密碼: passwd"
echo "============================================"
