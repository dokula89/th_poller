@echo off
REM NordVPN CLI Wrapper for Windows
REM Usage: nordvpn.bat [command]

cd /d "%~dp0"

REM Use virtual environment python directly
.venv\Scripts\python.exe nordvpn_controller.py %*
