# Setup PHP Server to Auto-Start with Windows
# This script creates a scheduled task to start the PHP server at login

$taskName = "TH_Poller_PHP_Server"
$phpPath = "C:\xampp\php\php.exe"
$webRoot = "C:\Users\dokul\Desktop\robot\th_poller\htdocs"
$port = 8000

Write-Host "Setting up PHP Server Auto-Start..." -ForegroundColor Cyan
Write-Host ""

# Remove existing task if it exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create the action (what to run)
$action = New-ScheduledTaskAction -Execute $phpPath `
    -Argument "-S localhost:$port" `
    -WorkingDirectory $webRoot

# Create the trigger (when to run - at user login)
$trigger = New-ScheduledTaskTrigger -AtLogOn

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

# Create the principal (run as current user)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

# Register the task
Register-ScheduledTask -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Automatically starts PHP development server for TH Poller on localhost:$port" | Out-Null

Write-Host "✓ Task created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Task Details:" -ForegroundColor Cyan
Write-Host "  Name: $taskName" -ForegroundColor Gray
Write-Host "  Trigger: At user login" -ForegroundColor Gray
Write-Host "  Server: http://localhost:$port" -ForegroundColor Gray
Write-Host "  Web Root: $webRoot" -ForegroundColor Gray
Write-Host ""

# Start the task immediately
Write-Host "Starting PHP server now..." -ForegroundColor Cyan
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 2

# Check if it's running
$process = Get-Process -Name php -ErrorAction SilentlyContinue
if ($process) {
    Write-Host "✓ PHP server is running!" -ForegroundColor Green
    Write-Host ""
    Write-Host "The server will now start automatically every time you log in." -ForegroundColor Green
    Write-Host "You can manage it in Task Scheduler or use these commands:" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Stop:  Stop-ScheduledTask -TaskName '$taskName'" -ForegroundColor Yellow
    Write-Host "  Start: Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Yellow
    Write-Host "  Remove: Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false" -ForegroundColor Yellow
} else {
    Write-Host "⚠ Server may not have started. Check Task Scheduler." -ForegroundColor Yellow
}

Write-Host ""
Read-Host "Press Enter to close"
