@echo off
setlocal enabledelayedexpansion

echo ============================================
echo  Agentic Memory System - Setup (Windows)
echo ============================================
echo.

:: ---- Python Backend Setup ----
echo [1/3] Setting up Python backend...

if not exist "venv" (
    python -m venv venv
    echo   Created virtual environment
) else (
    echo   Virtual environment already exists
)

call venv\Scripts\activate.bat
pip install -q -r requirements.txt
echo   Python dependencies installed

:: ---- Node.js Frontend Setup ----
echo.
echo [2/3] Setting up Node.js frontend...

if not exist "node_modules" (
    npm install --silent
    echo   Node dependencies installed
) else (
    echo   Node dependencies already exist
)

:: ---- Create public dir if needed ----
if not exist "public" (
    mkdir public
    if exist "index.html" (
        copy index.html public\index.html
        echo   Copied index.html to public\
    )
)

:: ---- Verify .env ----
if not exist ".env" (
    echo.
    echo [!] No .env file found. Creating default...
    (
        echo OLLAMA_BASE_URL=http://localhost:11434
        echo ENDEE_BASE_URL=http://localhost:8080
        echo PORT=3000
        echo BACKEND_URL=http://localhost:8000
    ) > .env
    echo   Default .env created
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