@echo off
REM Start PHP server for th_poller project
cd /d "%~dp0"

REM Try to find PHP - check XAMPP first, then PATH
set PHP_EXE=
if exist "C:\xampp\php\php.exe" (
    set PHP_EXE=C:\xampp\php\php.exe
) else (
    where php >nul 2>&1
    if %errorlevel%==0 (
        set PHP_EXE=php
    )
)

if "%PHP_EXE%"=="" (
    echo ERROR: PHP not found!
    echo Please install PHP or XAMPP
    pause
    exit /b 1
)

echo Found PHP: %PHP_EXE%
echo Starting PHP server on http://localhost:8000/
echo Serving from: %CD%\htdocs
echo Press Ctrl+C to stop
echo.
"%PHP_EXE%" -S localhost:8000 -t htdocs
pause
