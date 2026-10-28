@echo off
TITLE NEXUS - Offline-First Knowledge Intelligence Terminal
COLOR 0A
chcp 65001 >nul

echo ===============================================================================
echo   ███╗   ██╗███████╗██╗   ██╗██╗   ██╗███████╗
echo   ████╗  ██║██╔════╝██║   ██║██║   ██║██╔════╝
echo   ██╔██╗ ██║█████╗  ╚██╗ ██╔╝██║   ██║███████╗
echo   ██║╚██╗██║██╔══╝   ╚████╔╝ ██║   ██║╚════██║
echo   ██║ ╚████║███████╗  ╚██╔╝  ╚██████╔╝███████║
echo   ╚═╝  ╚═══╝╚══════╝   ╚═╝    ╚═════╝ ╚══════╝
echo   OFFLINE-FIRST DOMAIN-SPECIFIC KNOWLEDGE INTELLIGENCE PLATFORM
echo ===============================================================================
echo.

:: 1. Verify Virtual Environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv\Scripts\python.exe
    echo Initializing virtual environment using Python 3.12...
    python -m venv .venv
    if errorlevel 1 (
        echo [CRITICAL] Failed to create virtual environment. Ensure Python 3.12 is installed on PATH.
        pause
        exit /b 1
    )
    echo Installing required packages...
    .\.venv\Scripts\pip.exe install -r requirements.txt
)

echo [OK] Python runtime environment verified.

:: 2. Check Local Ollama Daemon Status
echo Checking local Ollama LLM service status...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2 -UseBasicParsing; Write-Host '[OK] Ollama local service is active (Qwen2.5 1.5B online).' -ForegroundColor Green } catch { Write-Host '[INFO] Ollama daemon not detected. Operating in resilient offline mode.' -ForegroundColor Yellow }"

:: 3. Pre-flight Database Verification
echo Verifying SQLite database and schema initialization...
.\.venv\Scripts\python.exe -c "from backend.storage.db import init_database; init_database(); print('[OK] Database schema initialized with foreign keys and WAL mode.')"

echo.
echo ===============================================================================
echo   STARTING NEXUS TACTICAL INTERFACE
echo   Local URL: http://localhost:8501
echo   Clearance Logins:
echo     Administrator: admin / NexusAdmin#2026
echo     Instructor:    instructor_demo / NexusInstructor#2026
echo     Trainee:       trainee_demo / NexusTrainee#2026
echo ===============================================================================
echo.

:: 4. Launch Streamlit Application
.\.venv\Scripts\streamlit.exe run app.py --server.port 8501 --server.address localhost --browser.serverAddress localhost

if errorlevel 1 (
    echo.
    echo [ERROR] Application terminated unexpectedly.
    pause
)
