# Start PHP Development Server
# This script ensures the PHP server is always running on localhost:8000

$phpPath = "C:\xampp\php\php.exe"
$webRoot = "C:\Users\dokul\Desktop\robot\th_poller\htdocs"
$port = 8000

Write-Host "Starting PHP Development Server..." -ForegroundColor Cyan
Write-Host "Web Root: $webRoot" -ForegroundColor Gray
Write-Host "Port: $port" -ForegroundColor Gray
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Kill any existing PHP processes on this port
$existingProcesses = Get-Process -Name php -ErrorAction SilentlyContinue
if ($existingProcesses) {
    Write-Host "Stopping existing PHP processes..." -ForegroundColor Yellow
    Stop-Process -Name php -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Change to web root directory
Set-Location $webRoot

# Start PHP server
Write-Host "Server running at http://localhost:$port" -ForegroundColor Green
Write-Host "Logs will appear below:" -ForegroundColor Gray
Write-Host ("=" * 80) -ForegroundColor DarkGray

& $phpPath -S "localhost:$port"
