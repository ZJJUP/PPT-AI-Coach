@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [PPT-AI-Coach] Missing virtual environment.
  echo Run: py -3.11 -m venv .venv
  echo Then: .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 11) else 1)"
if errorlevel 1 (
  echo [PPT-AI-Coach] Python 3.11 is required. Please recreate .venv with py -3.11.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m ppt_ai_coach
if errorlevel 1 (
  echo [PPT-AI-Coach] Startup failed. Read the message above and README.md.
  pause
  exit /b 1
)
endlocal
