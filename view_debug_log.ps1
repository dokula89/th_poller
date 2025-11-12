# View the debug log file
$logFile = Join-Path $PSScriptRoot "debug_queue.log"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "DEBUG LOG VIEWER" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Log file location: $logFile" -ForegroundColor Yellow
Write-Host ""

if (Test-Path $logFile) {
    Write-Host "LOG CONTENTS:" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Gray
    Get-Content $logFile
    Write-Host "============================================" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To continuously monitor:" -ForegroundColor Cyan
    Write-Host "Get-Content '$logFile' -Wait -Tail 20" -ForegroundColor White
} else {
    Write-Host "Log file does not exist yet." -ForegroundColor Red
    Write-Host "Run the worker first, then check this file." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
