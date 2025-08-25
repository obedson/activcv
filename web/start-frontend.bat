@echo off
echo 🌐 Starting AI CV Agent Frontend
echo =================================

echo Checking Node.js dependencies...
if not exist "node_modules" (
    echo ❌ Frontend dependencies not installed
    echo Installing dependencies...
    npm install
)

echo.
echo 🚀 Starting Next.js development server...
echo.
echo Frontend will be available at:
echo - Application: http://localhost:3000
echo.
echo Press Ctrl+C to stop the server
echo.

npm run dev