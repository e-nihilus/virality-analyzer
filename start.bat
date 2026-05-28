@echo off
echo Starting Aurea Viral Intelligence...
echo.
echo [Backend] http://127.0.0.1:8000/docs
echo [Frontend] http://localhost:5173
echo.
start "Aurea Backend" cmd /k "cd /d %~dp0 && uvicorn app.main:app --reload --app-dir backend"
start "Aurea Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
