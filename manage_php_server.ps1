# Manage PHP Server
# Quick commands to start, stop, or check the PHP server status

param(
    [Parameter(Position=0)]
    [ValidateSet('start', 'stop', 'restart', 'status')]
    [string]$Action = 'status'
)

$phpPath = "C:\xampp\php\php.exe"
$webRoot = "C:\Users\dokul\Desktop\robot\th_poller\htdocs"
$port = 8000
$taskName = "TH_Poller_PHP_Server"

function Show-Status {
    $process = Get-Process -Name php -ErrorAction SilentlyContinue
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    
    Write-Host ""
    Write-Host "PHP Server Status:" -ForegroundColor Cyan
    Write-Host ("=" * 50) -ForegroundColor DarkGray
    
    if ($process) {
        Write-Host "✓ Server Process: RUNNING (PID: $($process.Id))" -ForegroundColor Green
    } else {
        Write-Host "✗ Server Process: NOT RUNNING" -ForegroundColor Red
    }
    
    if ($task) {
        $taskState = $task.State
        Write-Host "✓ Scheduled Task: $taskState" -ForegroundColor Green
    } else {
        Write-Host "✗ Scheduled Task: NOT CONFIGURED" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Configuration:" -ForegroundColor Cyan
    Write-Host "  URL: http://localhost:$port" -ForegroundColor Gray
    Write-Host "  Web Root: $webRoot" -ForegroundColor Gray
    Write-Host ("=" * 50) -ForegroundColor DarkGray
    Write-Host ""
}

function Start-Server {
    Write-Host "Starting PHP server..." -ForegroundColor Cyan
    
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($task) {
        Start-ScheduledTask -TaskName $taskName
        Start-Sleep -Seconds 2
        Show-Status
    } else {
        Write-Host "⚠ Scheduled task not found. Run setup_php_autostart.ps1 first." -ForegroundColor Yellow
        Write-Host "Starting manually..." -ForegroundColor Cyan
        
        # Kill any existing
        Stop-Process -Name php -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        
        # Start new process in background
        Start-Process -FilePath $phpPath `
            -ArgumentList "-S localhost:$port" `
            -WorkingDirectory $webRoot `
            -WindowStyle Hidden
        
        Start-Sleep -Seconds 2
        Show-Status
    }
}

function Stop-Server {
    Write-Host "Stopping PHP server..." -ForegroundColor Cyan
    
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($task) {
        Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    }
    
    Stop-Process -Name php -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    
    Write-Host "✓ Server stopped" -ForegroundColor Green
    Show-Status
}

function Restart-Server {
    Write-Host "Restarting PHP server..." -ForegroundColor Cyan
    Stop-Server
    Start-Sleep -Seconds 1
    Start-Server
}

# Execute action
switch ($Action) {
    'start'   { Start-Server }
    'stop'    { Stop-Server }
    'restart' { Restart-Server }
    'status'  { Show-Status }
}
