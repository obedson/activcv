@echo off
echo Installing missing packages...
call venv\Scripts\activate.bat
pip install redis celery
echo Done!