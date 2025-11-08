@echo off
echo.
echo ================================================================================
echo DriftGuards AI - Quick Launcher
echo ================================================================================
echo.
echo Starting both Streamlit Dashboard and Auto-Scheduler...
echo.
echo Press Ctrl+C to stop
echo.
echo ================================================================================
echo.

cd /d %~dp0

:: Start Streamlit in new window
start "DriftGuards - Streamlit Dashboard" cmd /k "python -m streamlit run app.py"

:: Wait a bit for Streamlit to start
timeout /t 3 /nobreak > nul

:: Start Auto-Scheduler in new window
start "DriftGuards - Auto-Scheduler" cmd /k "python auto_scheduler.py"

echo.
echo ✅ Both services started in separate windows!
echo.
echo 📊 Streamlit Dashboard: http://localhost:8501
echo 🤖 Auto-Scheduler: Check the second window
echo.
echo Close the windows to stop the services
echo.
pause
