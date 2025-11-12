@echo off
echo ================================================
echo PHPMailer Setup Script for XAMPP
echo ================================================
echo.

:: Check if Composer is installed
where composer >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Composer is not installed!
    echo Please download and install Composer from:
    echo https://getcomposer.org/download/
    echo.
    pause
    exit /b 1
)

echo [OK] Composer is installed
echo.

:: Check if XAMPP htdocs exists
if not exist "C:\xampp\htdocs" (
    echo [ERROR] XAMPP htdocs folder not found at C:\xampp\htdocs
    echo Please make sure XAMPP is installed
    echo.
    pause
    exit /b 1
)

echo [OK] XAMPP htdocs found
echo.

:: Navigate to htdocs
cd /d C:\xampp\htdocs

:: Check if vendor folder already exists
if exist "vendor" (
    echo [INFO] vendor folder already exists, skipping installation
) else (
    echo Installing PHPMailer via Composer...
    echo This may take a few minutes...
    echo.
    composer require phpmailer/phpmailer
    
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install PHPMailer
        pause
        exit /b 1
    )
    
    echo [OK] PHPMailer installed successfully
)

echo.
echo Copying API file to htdocs...

:: Copy the PHP API file
copy /Y "%~dp0send_email_api.php" "C:\xampp\htdocs\send_email_api.php"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to copy API file
    pause
    exit /b 1
)

echo [OK] API file copied
echo.

echo ================================================
echo Setup Complete!
echo ================================================
echo.
echo Next steps:
echo 1. Start Apache in XAMPP Control Panel
echo 2. Run: python setup_newsletter_tables.py
echo 3. Test by visiting: http://localhost/send_email_api.php
echo.
echo You should see: {"success":false,"error":"Only POST requests are allowed"}
echo.
pause
