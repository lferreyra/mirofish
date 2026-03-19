#!/usr/bin/env bash
#
# MiroFish — Lancement rapide (one-command)
# Usage: bash start.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ---------- Premier lancement : exécuter setup ----------
if [ ! -d "node_modules" ] || [ ! -d "frontend/node_modules" ] || [ ! -f ".env" ]; then
    echo "Premier lancement détecté, exécution de setup.sh..."
    echo ""
    bash setup.sh
    echo ""
fi

# ---------- Détecter le mode depuis .env ----------
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

# ---------- Lancer le bon mode ----------
if [ "$IS_BRIDGE" = true ] && [ "$IS_LITE" = true ]; then
    echo "Lancement en mode Bridge + Lite (Claude Proxy + Backend + Frontend)..."
    echo ""
    npm run dev:bridge
elif [ "$IS_BRIDGE" = true ]; then
    echo "Lancement en mode Bridge (Claude Proxy + Backend + Frontend)..."
    echo ""
    npm run dev:claude
elif [ "$IS_LITE" = true ]; then
    echo "Lancement en mode Lite (Backend + Frontend)..."
    echo ""
    npm run dev:lite
else
    echo "Lancement en mode complet (Backend + Frontend)..."
    echo ""
    npm run dev
fi
