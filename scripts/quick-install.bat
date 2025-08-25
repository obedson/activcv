@echo off
echo 🚀 AI CV Agent - Quick Installation for Windows
echo ===============================================
echo.

echo [1/6] Setting up Python backend...
cd agent

echo Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Python dependencies
    echo Trying individual package installation...
    pip install fastapi uvicorn pydantic supabase python-dotenv requests aiofiles
)

cd ..

echo.
echo [2/6] Setting up Node.js frontend...
cd web

echo Installing Node.js dependencies...
npm install
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Node.js dependencies
    echo Trying npm cache clean...
    npm cache clean --force
    npm install
)

cd ..

echo.
echo [3/6] Creating environment files...
if not exist "agent\.env" (
    if exist "agent\.env.example" (
        copy "agent\.env.example" "agent\.env"
        echo ✅ Created agent\.env from example
    )
)

if not exist "web\.env.local" (
    if exist "web\.env.local.example" (
        copy "web\.env.local.example" "web\.env.local"
        echo ✅ Created web\.env.local from example
    )
)

echo.
echo [4/6] Creating necessary directories...
if not exist "logs" mkdir logs
if not exist "temp_storage" mkdir temp_storage
if not exist "backups" mkdir backups

echo.
echo [5/6] Testing installations...
echo Testing Python setup...
cd agent
call venv\Scripts\activate.bat
python -c "import fastapi; print('✅ FastAPI imported successfully')"
python -c "import supabase; print('✅ Supabase imported successfully')"
cd ..

echo Testing Node.js setup...
cd web
npm list next >nul 2>&1 && echo ✅ Next.js installed successfully
cd ..

echo.
echo [6/6] Installation complete!
echo.
echo 📋 Next Steps:
echo 1. Configure your environment variables:
echo    - Edit agent\.env with your API keys
echo    - Edit web\.env.local with your frontend settings
echo.
echo 2. Start the development servers:
echo    Backend:  cd agent ^&^& venv\Scripts\activate ^&^& python main.py
echo    Frontend: cd web ^&^& npm run dev
echo.
echo 3. Access your application:
echo    - Frontend: http://localhost:3000
echo    - Backend:  http://localhost:8000
echo    - API Docs: http://localhost:8000/docs
echo.
echo ✅ Installation completed successfully!
pause