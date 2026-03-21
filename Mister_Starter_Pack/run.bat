@echo off
title X Media Scraper Bot
echo [!] Waking up the organism...

if not exist "venv" (
    echo [!] Virtual environment not found. Initializing...
    python -m venv venv
)

call venv\Scripts\activate

:: Automatic Dependency Management
set "REQ_HASH_FILE=venv\req_hash.txt"
if not exist "requirements.txt" (
    echo [!] requirements.txt not found. Skipping dependency check.
) else (
    for /f "tokens=*" %%a in ('certutil -hashfile requirements.txt MD5 ^| find /v ":"') do set "NH=%%a"
    if exist "%REQ_HASH_FILE%" ( set /p OH=<"%REQ_HASH_FILE%" ) else ( set "OH=NONE" )
    if not "%NH%"=="%OH%" (
        echo [!] Dependencies outdated or missing. Installing...
        pip install -r requirements.txt
        echo %NH% > "%REQ_HASH_FILE%"
    )
)

echo [!] Starting bot...
python main.py
pause
