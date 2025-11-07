@echo off
REM NeuroLake Dashboard Quick Start Script
REM Starts the unified dashboard with NDM + NUIC integration

echo ================================================================
echo  NeuroLake Dashboard - NDM + NUIC Integration
echo ================================================================
echo.
echo Starting dashboard server...
echo.
echo Once started, access at:
echo   - Main Dashboard: http://localhost:8000
echo   - Data Ingestion: http://localhost:8000/ndm-nuic
echo   - Migration: http://localhost:8000/migration
echo   - Notebooks: http://localhost:8000/notebook
echo.
echo Press Ctrl+C to stop the server
echo.
echo ================================================================
echo.

python advanced_databricks_dashboard.py

pause
