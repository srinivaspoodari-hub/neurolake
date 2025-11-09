@echo off
echo ================================================================================
echo  NEUROLAKE DOCKER DEPLOYMENT - E2E TESTING
echo ================================================================================
echo.

echo [STEP 1] Stopping any existing containers...
docker-compose -f docker-compose.test.yml down 2>nul

echo.
echo [STEP 2] Building NeuroLake Dashboard image...
docker-compose -f docker-compose.test.yml build dashboard

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [STEP 3] Starting all services...
docker-compose -f docker-compose.test.yml up -d

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to start services!
    pause
    exit /b 1
)

echo.
echo [STEP 4] Waiting for services to be healthy...
timeout /t 15 /nobreak >nul

echo.
echo ================================================================================
echo  DEPLOYMENT COMPLETE!
echo ================================================================================
echo.
echo Services running:
echo   - Dashboard:     http://localhost:5000
echo   - MinIO Console: http://localhost:9001 (user: neurolake, pass: dev_password)
echo   - PostgreSQL:    localhost:5432 (user: neurolake, pass: dev_password)
echo   - Redis:         localhost:6379
echo.
echo To view logs:
echo   docker-compose -f docker-compose.test.yml logs -f dashboard
echo.
echo To stop all services:
echo   docker-compose -f docker-compose.test.yml down
echo.
echo ================================================================================
echo.

echo Opening dashboard in browser...
timeout /t 5 /nobreak >nul
start http://localhost:5000

echo.
echo Press any key to view dashboard logs...
pause >nul

docker-compose -f docker-compose.test.yml logs -f dashboard
