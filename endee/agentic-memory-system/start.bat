@echo off
setlocal enabledelayedexpansion

echo ==============================================================
echo        AGENTIC MEMORY SYSTEM - AUTOMATED STARTUP
echo ==============================================================
echo.

:: 0. Kill Stale Processes on ports 3000 and 8000
echo [0/4] Clearing any stale processes on ports 3000 and 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTEN"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTEN"') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo [Y] Ports cleared.

:: 1. Docker Check
echo.
echo [1/4] Checking Docker daemon...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Docker is not running. Launching Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    
    echo Waiting for Docker daemon to start ^(this may take a minute^)...
    set WAIT_COUNT=0
    :wait_docker
    timeout /t 5 /nobreak >nul
    docker info >nul 2>&1
    if !errorlevel! neq 0 (
        set /a WAIT_COUNT+=1
        if !WAIT_COUNT! lss 24 (
            goto wait_docker
        ) else (
            echo [X] Timed out waiting for Docker. Please start it manually.
            pause
            exit /b 1
        )
    )
    echo [Y] Docker is now running.
) else (
    echo [Y] Docker is already running.
)

:: 2. Endee Container Start
echo.
echo [2/4] Starting Endee Vector Database...
docker start endee-server >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Endee container not found or failed to start. Creating new instance...
    docker run --ulimit nofile=100000:100000 -p 8080:8080 -v endee-data-vol:/data --name endee-server --restart unless-stopped -d endeeio/endee-server:latest >nul
    if !errorlevel! neq 0 (
        echo [X] Failed to create Endee container. Ensure Docker is working correctly.
        pause
        exit /b 1
    )
    echo [Y] Endee container created and started.
) else (
    echo [Y] Endee server is running.
)

:: Wait a few seconds for Endee to fully initialise
echo [!] Waiting for Endee to become healthy...
set ENDEE_WAIT=0
:wait_endee
timeout /t 3 /nobreak >nul
curl -s http://localhost:8080/api/v1/health >nul 2>&1
if %errorlevel% neq 0 (
    set /a ENDEE_WAIT+=1
    if !ENDEE_WAIT! lss 10 (
        goto wait_endee
    ) else (
        echo [X] Endee did not become healthy in time. Check Docker logs.
        pause
        exit /b 1
    )
)
echo [Y] Endee is healthy.

:: 3. Python Backend
echo.
echo [3/4] Setup / Starting Python Backend...
if not exist "venv" (
    echo [!] Creating virtual environment...
    python -m venv venv
)
echo [!] Installing/Updating Python requirements...
call venv\Scripts\pip.exe install -r requirements.txt --quiet

echo Launching Backend...
start "Backend - Agentic Memory" cmd /k "venv\Scripts\activate.bat && echo Starting Uvicorn Server... && python agent_backend.py"

:: Give backend a moment to bind its port
timeout /t 5 /nobreak >nul

:: 4. Node Frontend
echo.
echo [4/4] Setup / Starting Node Frontend...
if not exist "node_modules" (
    echo [!] Installing Node modules...
    call npm install --silent
)

echo Launching Frontend...
start "Frontend - Agentic Memory" cmd /k "echo Starting HTTP Server... && npm start"

echo.
echo ==============================================================
echo [Y] All systems launched!
echo Access the UI at: http://localhost:3000
echo ==============================================================
pause
