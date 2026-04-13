@echo off
setlocal enabledelayedexpansion

echo ============================================
echo  Agentic Memory System - Setup (Windows)
echo ============================================
echo.

:: ── Prerequisites check ──
echo [0/3] Checking prerequisites...
python --version >nul 2>&1 || (echo Error: python not found. Install Python 3.10+ & exit /b 1)
node --version >nul 2>&1   || (echo Error: node not found. Install Node.js 16+   & exit /b 1)
echo   Done.

:: ── Python Backend ──
echo.
echo [1/3] Setting up Python backend...

if not exist "venv" (
    python -m venv venv
    echo   Created virtual environment
) else (
    echo   Virtual environment already exists
)

call venv\Scripts\activate.bat
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo   Python dependencies installed (includes official Endee SDK)

:: ── Node.js Frontend ──
echo.
echo [2/3] Setting up Node.js frontend...

if not exist "node_modules" (
    npm install --silent
    echo   Node dependencies installed
) else (
    echo   node_modules already exists
)

:: ── .env ──
echo.
echo [3/3] Verifying .env...

if not exist ".env" (
    (
        echo OLLAMA_BASE_URL=http://localhost:11434
        echo ENDEE_BASE_URL=http://localhost:8080
        echo ENDEE_AUTH_TOKEN=
        echo LLM_MODEL=glm-5
        echo EMBEDDING_MODEL=nomic-embed-text
        echo PORT=3000
        echo BACKEND_URL=http://localhost:8000
    ) > .env
    echo   Default .env created
) else (
    echo   .env already exists
)

echo.
echo ============================================
echo  Setup complete!
echo.
echo  Start services:
echo    Terminal 1: venv\Scripts\activate ^&^& python agent_backend.py
echo    Terminal 2: npm start
echo.
echo  Then open: http://localhost:3000
echo ============================================

pause
