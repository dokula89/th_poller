# PHP Server Auto-Start Guide

## Quick Start

The PHP server now starts automatically with the poller watchdog:

```powershell
.\always_restart_poller.ps1
```

This will:
- ✓ Start PHP server on http://localhost:8000
- ✓ Monitor and restart PHP server if it crashes
- ✓ Start and monitor the main poller application

## Manual Control

```powershell
# Check status
.\manage_php_server.ps1 status

# Start/Stop/Restart
.\manage_php_server.ps1 start
.\manage_php_server.ps1 stop
.\manage_php_server.ps1 restart
```

## Windows Startup (Optional)

To start PHP server automatically when Windows starts:

```powershell
# Run as Administrator:
.\setup_php_autostart.ps1
```

## Server Info
- URL: http://localhost:8000
- Web Root: C:\Users\dokul\Desktop\robot\th_poller\htdocs
- PHP: C:\xampp\php\php.exe

## Troubleshooting

**Check if running:**
```powershell
Get-Process -Name php
```

**Kill and restart:**
```powershell
Stop-Process -Name php -Force
.\manage_php_server.ps1 start
```
