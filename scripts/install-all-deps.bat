@echo off
REM AI CV Agent - Complete Dependency Installation Script for Windows
REM This script installs all dependencies for both backend and frontend

setlocal enabledelayedexpansion

echo 🚀 AI CV Agent - Complete Dependency Installation (Windows)
echo ===========================================================
echo.

REM Check Python
echo [STEP] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [INFO] Python found: %PYTHON_VERSION%

REM Check if Python version is acceptable (3.10+)
python -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.10+ required, found %PYTHON_VERSION%
    echo [INFO] Your Python version should work, but 3.11+ is recommended
    pause
    exit /b 1
) else (
    echo [INFO] Python version is compatible
)

REM Check Node.js
echo [STEP] Checking Node.js installation...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)

for /f %%i in ('node --version') do set NODE_VERSION=%%i
echo [INFO] Node.js found: %NODE_VERSION%

REM Check npm
echo [STEP] Checking npm installation...
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm not found. Please install npm
    pause
    exit /b 1
)

for /f %%i in ('npm --version') do set NPM_VERSION=%%i
echo [INFO] npm found: %NPM_VERSION%

echo.
echo [INFO] All system requirements met! Proceeding with installation...
echo.

REM Setup Python environment
echo [STEP] Setting up Python virtual environment...
cd agent

if not exist "venv" (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
) else (
    echo [INFO] Virtual environment already exists
)

echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

REM Install Python dependencies
echo [STEP] Installing Python dependencies...
if exist "requirements.txt" (
    echo [INFO] Installing from requirements.txt...
    pip install -r requirements.txt
) else (
    echo [WARN] requirements.txt not found, installing individual packages...
    pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 python-multipart==0.0.6 pydantic==2.5.0 pydantic-settings==2.1.0 supabase==2.3.0 crewai==0.28.8 python-dotenv==1.0.0 pypdf==3.17.4 jinja2==3.1.2 requests==2.31.0 aiofiles==23.2.1 python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4 beautifulsoup4==4.12.2 schedule==1.2.0
    pip install pytest==7.4.3 pytest-asyncio==0.21.1 black==23.11.0 flake8==6.1.0 mypy==1.7.1
)

cd ..

REM Install Node.js dependencies
echo [STEP] Installing Node.js dependencies...
cd web

if exist "package-lock.json" (
    echo [INFO] Found package-lock.json, running clean install...
    npm ci
) else (
    echo [INFO] Running npm install...
    npm install
)

cd ..

REM Create necessary directories
echo [STEP] Setting up development environment...
if not exist "logs" mkdir logs
if not exist "temp_storage" mkdir temp_storage
if not exist "backups" mkdir backups
if not exist "monitoring" mkdir monitoring

REM Copy environment files
if not exist "agent\.env" (
    if exist "agent\.env.example" (
        echo [INFO] Creating agent\.env from example...
        copy "agent\.env.example" "agent\.env"
        echo [WARN] Please update agent\.env with your configuration
    )
)

if not exist "web\.env.local" (
    if exist "web\.env.local.example" (
        echo [INFO] Creating web\.env.local from example...
        copy "web\.env.local.example" "web\.env.local"
        echo [WARN] Please update web\.env.local with your configuration
    )
)

REM Generate installation report
echo [STEP] Generating installation report...
echo # AI CV Agent - Installation Report > INSTALLATION_REPORT.md
echo. >> INSTALLATION_REPORT.md
echo **Installation Date:** %date% %time% >> INSTALLATION_REPORT.md
echo **Operating System:** Windows >> INSTALLATION_REPORT.md
echo **User:** %username% >> INSTALLATION_REPORT.md
echo. >> INSTALLATION_REPORT.md
echo ## Next Steps >> INSTALLATION_REPORT.md
echo 1. Configure environment variables in: >> INSTALLATION_REPORT.md
echo    - `agent\.env` >> INSTALLATION_REPORT.md
echo    - `web\.env.local` >> INSTALLATION_REPORT.md
echo. >> INSTALLATION_REPORT.md
echo 2. Start the development servers: >> INSTALLATION_REPORT.md
echo    ```bash >> INSTALLATION_REPORT.md
echo    # Backend >> INSTALLATION_REPORT.md
echo    cd agent >> INSTALLATION_REPORT.md
echo    venv\Scripts\activate >> INSTALLATION_REPORT.md
echo    python main.py >> INSTALLATION_REPORT.md
echo. >> INSTALLATION_REPORT.md
echo    # Frontend (in another terminal) >> INSTALLATION_REPORT.md
echo    cd web >> INSTALLATION_REPORT.md
echo    npm run dev >> INSTALLATION_REPORT.md
echo    ``` >> INSTALLATION_REPORT.md

echo.
echo 🎉 Installation completed successfully!
echo.
echo Next steps:
echo 1. Configure your environment variables
echo 2. Set up your Supabase project  
echo 3. Run the development servers
echo.
echo For detailed instructions, see: INSTALLATION_REPORT.md
echo.
pause