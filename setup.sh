#!/usr/bin/env bash
#
# MiroFish — Interactive setup script
# Usage: bash setup.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=================================================="
echo "  MiroFish — Setup"
echo "=================================================="
echo ""

# ---------- Colors ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
warn() { echo -e "  ${YELLOW}[!]${NC} $1"; }
fail() { echo -e "  ${RED}[X]${NC} $1"; }

# ---------- 1. Check Node.js ----------
echo "Checking prerequisites..."
echo ""

if ! command -v node &> /dev/null; then
    fail "Node.js not found."
    echo "     Install Node.js >= 18: https://nodejs.org/"
    echo "     Or via nvm: nvm install 18"
    exit 1
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    fail "Node.js >= 18 required (found: $(node -v))"
    exit 1
fi
ok "Node.js $(node -v)"

# ---------- 2. Check Python ----------
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &> /dev/null; then
        PY_VERSION=$("$cmd" --version 2>&1 | sed 's/Python //')
        PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
        if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    fail "Python >= 3.11 not found."
    echo "     Install Python 3.11+: https://www.python.org/downloads/"
    exit 1
fi
ok "Python $($PYTHON_CMD --version 2>&1 | sed 's/Python //')"

# ---------- 3. Check / install uv ----------
if ! command -v uv &> /dev/null; then
    warn "uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add to PATH for this session
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if ! command -v uv &> /dev/null; then
        fail "uv installation failed. Install manually: https://docs.astral.sh/uv/"
        exit 1
    fi
fi
ok "uv $(uv --version 2>&1 | head -1)"

# ---------- 4. Check Claude CLI (optional, for bridge mode) ----------
CLAUDE_CLI_AVAILABLE=false
if command -v claude &> /dev/null; then
    CLAUDE_CLI_AVAILABLE=true
    ok "Claude CLI available (bridge mode supported)"
else
    warn "Claude CLI not found (bridge mode unavailable)"
    echo "     To install: npm install -g @anthropic-ai/claude-code"
fi

echo ""

# ---------- 5. Install dependencies ----------
echo "Installing dependencies..."
echo ""
npm run setup:all
echo ""
ok "Dependencies installed"
echo ""

# ---------- 6. Configure .env ----------
if [ -f .env ]; then
    warn ".env file already exists. Keeping existing configuration."
    echo ""
else
    cp .env.example .env
    ok ".env file created from .env.example"
    echo ""

    echo "=================================================="
    echo "  Configuration"
    echo "=================================================="
    echo ""

    # --- Operation mode ---
    echo "How would you like to use MiroFish?"
    echo ""
    echo "  1) Bridge Mode (recommended) — Via Claude Code CLI"
    echo "     No API key required. Requires Claude CLI + Max subscription."
    echo ""
    echo "  2) API Mode — With an external LLM API key"
    echo "     Compatible with OpenAI, Qwen, GLM, etc."
    echo ""

    read -p "Choice [1/2] (default: 1): " MODE_CHOICE
    MODE_CHOICE=${MODE_CHOICE:-1}

    if [ "$MODE_CHOICE" = "1" ]; then
        # Bridge mode via Claude Code Proxy
        if [ "$CLAUDE_CLI_AVAILABLE" = false ]; then
            warn "Claude CLI not found. Install it first:"
            echo "     npm install -g @anthropic-ai/claude-code"
            echo "     claude login"
            echo ""
        fi

        # Configure .env for bridge mode
        # Use sed compatible with both macOS and Linux
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' 's|^LLM_API_KEY=.*|LLM_API_KEY=not-needed|' .env
            sed -i '' 's|^LLM_BASE_URL=.*|LLM_BASE_URL=http://localhost:8082/v1|' .env
            sed -i '' 's|^LLM_MODEL_NAME=.*|LLM_MODEL_NAME=claude-sonnet-4-6|' .env
        else
            sed -i 's|^LLM_API_KEY=.*|LLM_API_KEY=not-needed|' .env
            sed -i 's|^LLM_BASE_URL=.*|LLM_BASE_URL=http://localhost:8082/v1|' .env
            sed -i 's|^LLM_MODEL_NAME=.*|LLM_MODEL_NAME=claude-sonnet-4-6|' .env
        fi
        ok "LLM configured via Claude Code Bridge (port 8082)"
        USE_BRIDGE=true
    else
        # External API mode
        echo ""
        read -p "LLM API Key: " LLM_KEY
        if [ -n "$LLM_KEY" ]; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|^LLM_API_KEY=.*|LLM_API_KEY=$LLM_KEY|" .env
            else
                sed -i "s|^LLM_API_KEY=.*|LLM_API_KEY=$LLM_KEY|" .env
            fi
            ok "LLM_API_KEY configured"
        else
            warn "LLM_API_KEY not set — fill it manually in .env"
        fi

        read -p "LLM Base URL (default: https://dashscope.aliyuncs.com/compatible-mode/v1): " LLM_URL
        if [ -n "$LLM_URL" ]; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|^LLM_BASE_URL=.*|LLM_BASE_URL=$LLM_URL|" .env
            else
                sed -i "s|^LLM_BASE_URL=.*|LLM_BASE_URL=$LLM_URL|" .env
            fi
        fi

        read -p "LLM Model Name (default: qwen-plus): " LLM_MODEL
        if [ -n "$LLM_MODEL" ]; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|^LLM_MODEL_NAME=.*|LLM_MODEL_NAME=$LLM_MODEL|" .env
            else
                sed -i "s|^LLM_MODEL_NAME=.*|LLM_MODEL_NAME=$LLM_MODEL|" .env
            fi
        fi
        USE_BRIDGE=false
    fi

    echo ""

    # --- Zep Cloud (optional) ---
    read -p "Zep Cloud API Key (press Enter to skip — lite mode): " ZEP_KEY
    if [ -n "$ZEP_KEY" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^ZEP_API_KEY=.*|ZEP_API_KEY=$ZEP_KEY|" .env
        else
            sed -i "s|^ZEP_API_KEY=.*|ZEP_API_KEY=$ZEP_KEY|" .env
        fi
        ok "ZEP_API_KEY configured (full mode)"
    else
        echo "LITE_MODE=true" >> .env
        ok "Lite mode enabled (without Zep Cloud)"
    fi

    echo ""
fi

# ---------- 7. Summary ----------
echo "=================================================="
echo "  Setup complete!"
echo "=================================================="
echo ""

# Detect configured mode
if grep -q "LITE_MODE=true" .env 2>/dev/null; then
    IS_LITE=true
else
    IS_LITE=false
fi

if grep -q "LLM_BASE_URL=http://localhost:8082" .env 2>/dev/null; then
    IS_BRIDGE=true
else
    IS_BRIDGE=false
fi

echo "  To launch MiroFish:"
echo ""

if [ "$IS_BRIDGE" = true ] && [ "$IS_LITE" = true ]; then
    echo "    npm run dev:bridge"
    echo ""
    echo "  This starts: Claude Proxy (8082) + Backend (5001) + Frontend (3000)"
elif [ "$IS_BRIDGE" = true ]; then
    echo "    npm run dev:claude"
    echo ""
    echo "  This starts: Claude Proxy (8082) + Backend (5001) + Frontend (3000)"
elif [ "$IS_LITE" = true ]; then
    echo "    npm run dev:lite"
    echo ""
    echo "  This starts: Backend (5001) + Frontend (3000)"
else
    echo "    npm run dev"
    echo ""
    echo "  This starts: Backend (5001) + Frontend (3000)"
fi

echo "  Or use the shortcut: bash start.sh"
echo ""
