#!/usr/bin/env bash
# =============================================================================
# Agentic Memory System — One-Command Setup (Linux / macOS)
# =============================================================================
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}"
echo "============================================"
echo "  Agentic Memory System — Setup"
echo "============================================"
echo -e "${NC}"

# ── Prerequisites check ──────────────────────────────────────────────────────
echo -e "${CYAN}[0/3] Checking prerequisites...${NC}"
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 not found. Install Python 3.10+"; exit 1; }
command -v node    >/dev/null 2>&1 || { echo "Error: node not found. Install Node.js 16+"; exit 1; }
command -v npm     >/dev/null 2>&1 || { echo "Error: npm not found."; exit 1; }
echo -e "  ${GREEN}✓${NC} Python: $(python3 --version)"
echo -e "  ${GREEN}✓${NC} Node:   $(node --version)"

# ── Python Backend ────────────────────────────────────────────────────────────
echo -e "\n${CYAN}[1/3] Setting up Python backend...${NC}"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "  ${GREEN}✓${NC} Virtual environment created"
else
    echo -e "  ${YELLOW}→${NC} venv already exists — skipping"
fi

source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo -e "  ${GREEN}✓${NC} Python dependencies installed (including official Endee SDK)"

# ── Node.js Frontend ──────────────────────────────────────────────────────────
echo -e "\n${CYAN}[2/3] Setting up Node.js frontend...${NC}"

if [ ! -d "node_modules" ]; then
    npm install --silent
    echo -e "  ${GREEN}✓${NC} Node dependencies installed"
else
    echo -e "  ${YELLOW}→${NC} node_modules already exists — skipping"
fi

# ── Environment file ──────────────────────────────────────────────────────────
echo -e "\n${CYAN}[3/3] Verifying .env...${NC}"

if [ ! -f ".env" ]; then
    cat > .env <<EOF
OLLAMA_BASE_URL=http://localhost:11434
ENDEE_BASE_URL=http://localhost:8080
ENDEE_AUTH_TOKEN=
LLM_MODEL=glm-5
EMBEDDING_MODEL=nomic-embed-text
PORT=3000
BACKEND_URL=http://localhost:8000
EOF
    echo -e "  ${GREEN}✓${NC} Default .env created"
else
    echo -e "  ${YELLOW}→${NC} .env already exists — skipping"
fi

echo -e "\n${GREEN}============================================"
echo "  Setup complete!"
echo ""
echo "  Start services:"
echo "    Terminal 1: source venv/bin/activate && python agent_backend.py"
echo "    Terminal 2: npm start"
echo ""
echo "  Then open: http://localhost:3000"
echo -e "============================================${NC}\n"
