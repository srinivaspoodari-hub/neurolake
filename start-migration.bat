@echo off
REM NeuroLake Migration Module - Quick Start Script for Windows

echo ====================================
echo  NeuroLake Migration Module
echo  Docker Quick Start
echo ====================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Check for API key
if "%ANTHROPIC_API_KEY%"=="" (
    echo [WARNING] ANTHROPIC_API_KEY not set!
    echo.
    set /p API_KEY="Enter your Anthropic API key: "
    set ANTHROPIC_API_KEY=%API_KEY%
)

echo [OK] API key configured
echo.

REM Check if .env file exists
if not exist .env (
    echo Creating .env file...
    echo ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY%> .env
    echo ENV=development>> .env
    echo LOG_LEVEL=info>> .env
)

echo Starting NeuroLake Migration Dashboard...
echo.
echo This may take a few minutes on first run (downloading images)
echo.

docker-compose -f docker-compose.migration.yml up -d --build

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start containers!
    echo Check the logs with: docker-compose -f docker-compose.migration.yml logs
    pause
    exit /b 1
)

echo.
echo ====================================
echo  SUCCESS! Dashboard is starting...
echo ====================================
echo.
echo  Access the dashboard at:
echo  http://localhost:8501
echo.
echo  View logs: docker-compose -f docker-compose.migration.yml logs -f
echo  Stop:      docker-compose -f docker-compose.migration.yml down
echo.
echo  Opening browser in 5 seconds...
echo ====================================

timeout /t 5 /nobreak >nul
start http://localhost:8501

echo.
echo Dashboard opened in browser!
echo Press any key to view container logs (Ctrl+C to exit)...
pause >nul

docker-compose -f docker-compose.migration.yml logs -f
