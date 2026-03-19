#!/usr/bin/env bash
#
# MiroFish — Script d'installation interactive
# Usage: bash setup.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=================================================="
echo "  MiroFish — Installation"
echo "=================================================="
echo ""

# ---------- Couleurs ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
warn() { echo -e "  ${YELLOW}[!]${NC} $1"; }
fail() { echo -e "  ${RED}[X]${NC} $1"; }

# ---------- 1. Vérifier Node.js ----------
echo "Vérification des prérequis..."
echo ""

if ! command -v node &> /dev/null; then
    fail "Node.js introuvable."
    echo "     Installez Node.js >= 18 : https://nodejs.org/"
    echo "     Ou via nvm : nvm install 18"
    exit 1
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    fail "Node.js >= 18 requis (trouvé: $(node -v))"
    exit 1
fi
ok "Node.js $(node -v)"

# ---------- 2. Vérifier Python ----------
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
    fail "Python >= 3.11 introuvable."
    echo "     Installez Python 3.11+ : https://www.python.org/downloads/"
    exit 1
fi
ok "Python $($PYTHON_CMD --version 2>&1 | sed 's/Python //')"

# ---------- 3. Vérifier / installer uv ----------
if ! command -v uv &> /dev/null; then
    warn "uv introuvable. Installation en cours..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Ajouter au PATH pour cette session
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if ! command -v uv &> /dev/null; then
        fail "Installation de uv échouée. Installez manuellement : https://docs.astral.sh/uv/"
        exit 1
    fi
fi
ok "uv $(uv --version 2>&1 | head -1)"

# ---------- 4. Vérifier Claude CLI (optionnel, pour le bridge) ----------
CLAUDE_CLI_AVAILABLE=false
if command -v claude &> /dev/null; then
    CLAUDE_CLI_AVAILABLE=true
    ok "Claude CLI disponible (mode bridge possible)"
else
    warn "Claude CLI non trouvé (mode bridge non disponible)"
    echo "     Pour l'installer : npm install -g @anthropic-ai/claude-code"
fi

echo ""

# ---------- 5. Installer les dépendances ----------
echo "Installation des dépendances..."
echo ""
npm run setup:all
echo ""
ok "Dépendances installées"
echo ""

# ---------- 6. Configurer .env ----------
if [ -f .env ]; then
    warn "Le fichier .env existe déjà. Configuration conservée."
    echo ""
else
    cp .env.example .env
    ok "Fichier .env créé depuis .env.example"
    echo ""

    echo "=================================================="
    echo "  Configuration"
    echo "=================================================="
    echo ""

    # --- Mode de fonctionnement ---
    echo "Comment voulez-vous utiliser MiroFish ?"
    echo ""
    echo "  1) Mode Bridge (recommandé) — Via Claude Code CLI"
    echo "     Aucune clé API requise. Nécessite Claude CLI + abonnement Max."
    echo ""
    echo "  2) Mode API — Avec une clé API LLM externe"
    echo "     Compatible OpenAI, Qwen, GLM, etc."
    echo ""

    read -p "Choix [1/2] (défaut: 1): " MODE_CHOICE
    MODE_CHOICE=${MODE_CHOICE:-1}

    if [ "$MODE_CHOICE" = "1" ]; then
        # Mode Bridge via Claude Code Proxy
        if [ "$CLAUDE_CLI_AVAILABLE" = false ]; then
            warn "Claude CLI non trouvé. Installez-le d'abord :"
            echo "     npm install -g @anthropic-ai/claude-code"
            echo "     claude login"
            echo ""
        fi

        # Configurer .env pour le bridge
        # Utiliser sed compatible macOS et Linux
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' 's|^LLM_API_KEY=.*|LLM_API_KEY=not-needed|' .env
            sed -i '' 's|^LLM_BASE_URL=.*|LLM_BASE_URL=http://localhost:8082/v1|' .env
            sed -i '' 's|^LLM_MODEL_NAME=.*|LLM_MODEL_NAME=claude-sonnet-4-6|' .env
        else
            sed -i 's|^LLM_API_KEY=.*|LLM_API_KEY=not-needed|' .env
            sed -i 's|^LLM_BASE_URL=.*|LLM_BASE_URL=http://localhost:8082/v1|' .env
            sed -i 's|^LLM_MODEL_NAME=.*|LLM_MODEL_NAME=claude-sonnet-4-6|' .env
        fi
        ok "LLM configuré via Claude Code Bridge (port 8082)"
        USE_BRIDGE=true
    else
        # Mode API externe
        echo ""
        read -p "LLM API Key: " LLM_KEY
        if [ -n "$LLM_KEY" ]; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|^LLM_API_KEY=.*|LLM_API_KEY=$LLM_KEY|" .env
            else
                sed -i "s|^LLM_API_KEY=.*|LLM_API_KEY=$LLM_KEY|" .env
            fi
            ok "LLM_API_KEY configuré"
        else
            warn "LLM_API_KEY non configuré — à remplir manuellement dans .env"
        fi

        read -p "LLM Base URL (défaut: https://dashscope.aliyuncs.com/compatible-mode/v1): " LLM_URL
        if [ -n "$LLM_URL" ]; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|^LLM_BASE_URL=.*|LLM_BASE_URL=$LLM_URL|" .env
            else
                sed -i "s|^LLM_BASE_URL=.*|LLM_BASE_URL=$LLM_URL|" .env
            fi
        fi

        read -p "LLM Model Name (défaut: qwen-plus): " LLM_MODEL
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

    # --- Zep Cloud (optionnel) ---
    read -p "Zep Cloud API Key (Entrée pour passer — mode lite): " ZEP_KEY
    if [ -n "$ZEP_KEY" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^ZEP_API_KEY=.*|ZEP_API_KEY=$ZEP_KEY|" .env
        else
            sed -i "s|^ZEP_API_KEY=.*|ZEP_API_KEY=$ZEP_KEY|" .env
        fi
        ok "ZEP_API_KEY configuré (mode complet)"
    else
        echo "LITE_MODE=true" >> .env
        ok "Mode lite activé (sans Zep Cloud)"
    fi

    echo ""
fi

# ---------- 7. Résumé ----------
echo "=================================================="
echo "  Installation terminée !"
echo "=================================================="
echo ""

# Détecter le mode configuré
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

echo "  Pour lancer MiroFish :"
echo ""

if [ "$IS_BRIDGE" = true ] && [ "$IS_LITE" = true ]; then
    echo "    npm run dev:bridge"
    echo ""
    echo "  Cela lance : Claude Proxy (8082) + Backend (5001) + Frontend (3000)"
elif [ "$IS_BRIDGE" = true ]; then
    echo "    npm run dev:claude"
    echo ""
    echo "  Cela lance : Claude Proxy (8082) + Backend (5001) + Frontend (3000)"
elif [ "$IS_LITE" = true ]; then
    echo "    npm run dev:lite"
    echo ""
    echo "  Cela lance : Backend (5001) + Frontend (3000)"
else
    echo "    npm run dev"
    echo ""
    echo "  Cela lance : Backend (5001) + Frontend (3000)"
fi

echo "  Ou utilisez le raccourci : bash start.sh"
echo ""
