@echo off
cd /d "%~dp0"
if not exist .venv (
    echo [!] Virtual environment .venv not found. Creating it...
    uv venv .venv --python 3.12
    uv pip install -r requirements.txt --python .venv
)
echo [*] Starting Rass Derb Cup Discord Bot...
.\.venv\Scripts\python.exe -m rass_derb_bot
if errorlevel 1 (
    echo.
    echo [!] Bot stopped with an error. Check the logs above.
    pause
)
