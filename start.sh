#!/usr/bin/env bash
#
# MiroFish — Quick launch (one-command)
# Usage: bash start.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ---------- First launch: run setup ----------
if [ ! -d "node_modules" ] || [ ! -d "frontend/node_modules" ] || [ ! -f ".env" ]; then
    echo "First launch detected, running setup.sh..."
    echo ""
    bash setup.sh
    echo ""
fi

# ---------- Detect mode from .env ----------
IS_BRIDGE=false
IS_LITE=false

if grep -q "LLM_BASE_URL=http://localhost:8082" .env 2>/dev/null; then
    IS_BRIDGE=true
fi

if grep -q "LITE_MODE=true" .env 2>/dev/null; then
    IS_LITE=true
elif ! grep -q "ZEP_API_KEY" .env 2>/dev/null || grep -q "ZEP_API_KEY=your_zep_api_key_here" .env 2>/dev/null; then
    IS_LITE=true
fi

# ---------- Launch the appropriate mode ----------
if [ "$IS_BRIDGE" = true ] && [ "$IS_LITE" = true ]; then
    echo "Starting in Bridge + Lite mode (Claude Proxy + Backend + Frontend)..."
    echo ""
    npm run dev:bridge
elif [ "$IS_BRIDGE" = true ]; then
    echo "Starting in Bridge mode (Claude Proxy + Backend + Frontend)..."
    echo ""
    npm run dev:claude
elif [ "$IS_LITE" = true ]; then
    echo "Starting in Lite mode (Backend + Frontend)..."
    echo ""
    npm run dev:lite
else
    echo "Starting in full mode (Backend + Frontend)..."
    echo ""
    npm run dev
fi
