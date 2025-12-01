@echo off
REM Batch file to start XAMPP services on Windows startup
REM This runs the PowerShell script that starts Apache and MySQL

echo Starting XAMPP services...
powershell.exe -ExecutionPolicy Bypass -File "%~dp0start_xampp.ps1"
