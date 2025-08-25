@echo off
echo 🚀 Starting AI CV Agent Backend Server
echo ======================================

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Checking server configuration...
python -c "import fastapi, supabase, jinja2; print('✅ All packages ready')"

if %errorlevel% neq 0 (
    echo.
    echo ❌ Server configuration failed
    echo Please run: pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo 🌐 Starting FastAPI server...
echo.
echo Server will be available at:
echo - API: http://localhost:8000
echo - Documentation: http://localhost:8000/docs
echo - Health Check: http://localhost:8000/health
echo.
echo Press Ctrl+C to stop the server
echo.

python main.py