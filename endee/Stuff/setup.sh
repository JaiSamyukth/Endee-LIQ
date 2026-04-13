#!/bin/bash
# ============================================
# Agentic Memory System - One-Command Setup
# ============================================

set -e

echo "🧠 Setting up Agentic Memory System..."
echo ""

# ---- Python Backend Setup ----
echo "📦 Setting up Python backend..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✓ Virtual environment created"
else
    echo "  ✓ Virtual environment exists"
fi

source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
pip install -q -r requirements.txt
echo "  ✓ Python dependencies installed"

# ---- Node.js Frontend Setup ----
echo ""
echo "📦 Setting up Node.js frontend..."

if [ ! -d "node_modules" ]; then
    npm install --silent
    echo "  ✓ Node dependencies installed"
else
    echo "  ✓ Node dependencies exist"
fi

# ---- Create public directory if needed ----
if [ ! -d "public" ]; then
    mkdir -p public
    if [ -f "index.html" ]; then
        cp index.html public/index.html
        echo "  ✓ Copied index.html to public/"
    fi
fi

# ---- Verify .env ----
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠ No .env file found. Creating default..."
    cat > .env << 'EOF'
OLLAMA_BASE_URL=http://localhost:11434
ENDEE_BASE_URL=http://localhost:8080
PORT=3000
BACKEND_URL=http://localhost:8000
EOF
    echo "  ✓ Default .env created"
fi

echo ""
echo "============================================"
echo "✅ Setup complete!"
echo ""
echo "Start services:"
echo "  Terminal 1: source venv/bin/activate && python agent_backend.py"
echo "  Terminal 2: npm start"
echo ""
echo "Then open: http://localhost:3000"
echo "============================================"
