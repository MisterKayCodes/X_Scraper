@echo off
title X Media Scraper Bot
echo [*] Waking up the organism...

if not exist "venv" (
    echo [*] Virtual environment not found. Initializing...
    python -m venv venv
)

call venv\Scripts\activate

:: ── Dependency Management ──
call :check_deps
if errorlevel 1 (
    echo [X] Dependency install failed. Fix errors above and retry.
    pause
    exit /b 1
)

echo [*] Starting bot...
python main.py
pause
exit /b 0

:: ── Subroutine: Check and install dependencies ──
:check_deps
if not exist "requirements.txt" (
    echo [*] requirements.txt not found. Skipping dependency check.
    exit /b 0
)

set "REQ_HASH_FILE=venv\req_hash.txt"

:: Get current hash of requirements.txt
for /f "tokens=*" %%a in ('certutil -hashfile requirements.txt MD5 ^| find /v ":"') do set "NEW_HASH=%%a"

:: Get stored hash (or NONE on first run)
if exist "%REQ_HASH_FILE%" (
    set /p OLD_HASH=<"%REQ_HASH_FILE%"
) else (
    set "OLD_HASH=NONE"
)

:: Compare - use CALL SET trick to force runtime evaluation
call set "COMPARE_NEW=%%NEW_HASH%%"
call set "COMPARE_OLD=%%OLD_HASH%%"

if "%COMPARE_NEW%"=="%COMPARE_OLD%" (
    echo [OK] Dependencies up to date.
    exit /b 0
)

echo [*] Dependencies changed or first run. Installing...
pip install -r requirements.txt
if errorlevel 1 exit /b 1

:: Save new hash
echo %NEW_HASH%> "%REQ_HASH_FILE%"
echo [OK] Dependencies installed and hash saved.
exit /b 0
