@echo off
echo 🚀 Starting AI CV Agent (Simple Mode)
echo ======================================

call venv\Scripts\activate.bat

echo Testing core packages...
python -c "import fastapi, supabase, jinja2; print('✅ Core packages ready')"

if %errorlevel% neq 0 (
    echo ❌ Core packages missing
    pause
    exit /b 1
)

echo.
echo Starting simple server...
python simple-main.py