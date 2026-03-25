@echo off
REM ═══════════════════════════════════════════════════════
REM  SafeStep — One-Command Setup (Windows)
REM  Double-click this file OR run: start.bat
REM ═══════════════════════════════════════════════════════

echo.
echo ╔══════════════════════════════════════════╗
echo ║   🦶  SafeStep Backend Setup             ║
echo ╚══════════════════════════════════════════╝
echo.

REM ── Check Python ─────────────────────────────────────
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Download it from https://python.org/downloads
    echo Make sure to check "Add Python to PATH" during install!
    pause
    exit /b 1
)
echo       OK - Python found
echo.

REM ── Create virtual environment ───────────────────────
echo [2/5] Creating virtual environment...
if not exist venv (
    python -m venv venv
    echo       OK - Virtual environment created
) else (
    echo       OK - Virtual environment already exists
)
echo.

REM ── Activate venv ────────────────────────────────────
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
echo       OK - Activated
echo.

REM ── Install dependencies ─────────────────────────────
echo [4/5] Installing dependencies (30-60 seconds)...
pip install -q -r requirements.txt
echo       OK - All packages installed
echo.

REM ── Create .env if missing ───────────────────────────
echo [5/5] Setting up environment...
if not exist .env (
    copy .env.example .env >nul
    echo       OK - .env file created
    echo       IMPORTANT: Open .env and change SECRET_KEY to something random!
) else (
    echo       OK - .env already exists
)
echo.

REM ── Create db directory ──────────────────────────────
if not exist db mkdir db

REM ── Launch ───────────────────────────────────────────
echo ═══════════════════════════════════════════
echo   ✅  Setup complete! Starting server...
echo ═══════════════════════════════════════════
echo.
echo   Website:  http://localhost:8000
echo   API Docs: http://localhost:8000/api/docs
echo.
echo   Press Ctrl+C to stop the server
echo.

uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
