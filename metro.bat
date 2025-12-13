@echo off
REM Metro Manager CLI Wrapper
cd /d "%~dp0"
.venv\Scripts\python.exe metro_manager.py %*
