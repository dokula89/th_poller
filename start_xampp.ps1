# Start XAMPP Apache and MySQL on system startup
# This script opens XAMPP Control Panel and starts both services with admin rights

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️ Not running as administrator. Restarting with admin rights..."
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

# Path to XAMPP Control Panel
$xamppPath = "C:\xampp\xampp-control.exe"

# Check if XAMPP exists
if (-not (Test-Path $xamppPath)) {
    Write-Host "❌ XAMPP not found at $xamppPath"
    Write-Host "Please update the path in this script to match your XAMPP installation"
    pause
    exit
}

Write-Host "🚀 Starting XAMPP services as Administrator..."

# Check if Apache is already running
$apacheRunning = Get-Process -Name "httpd" -ErrorAction SilentlyContinue
if ($apacheRunning) {
    Write-Host "✅ Apache is already running"
} else {
    Write-Host "▶️ Starting Apache..."
    $apacheBat = "C:\xampp\apache_start.bat"
    if (Test-Path $apacheBat) {
        Start-Process "cmd.exe" -ArgumentList "/c `"$apacheBat`"" -WindowStyle Hidden
        Start-Sleep -Seconds 3
        Write-Host "✅ Apache started"
    } else {
        Write-Host "❌ Apache start script not found at $apacheBat"
    }
}

# Check if MySQL is already running
$mysqlRunning = Get-Process -Name "mysqld" -ErrorAction SilentlyContinue
if ($mysqlRunning) {
    Write-Host "✅ MySQL is already running"
} else {
    Write-Host "▶️ Starting MySQL..."
    $mysqlBat = "C:\xampp\mysql_start.bat"
    if (Test-Path $mysqlBat) {
        Start-Process "cmd.exe" -ArgumentList "/c `"$mysqlBat`"" -WindowStyle Hidden
        Start-Sleep -Seconds 3
        Write-Host "✅ MySQL started"
    } else {
        Write-Host "❌ MySQL start script not found at $mysqlBat"
    }
}

Start-Sleep -Seconds 1

# Check if PHP development server is already running on port 8000
$phpRunning = Get-Process -Name "php" -ErrorAction SilentlyContinue
if ($phpRunning) {
    Write-Host "✅ PHP server is already running"
} else {
    Write-Host "▶️ Starting PHP development server on port 8000..."
    $phpExe = "C:\xampp\php\php.exe"
    $webRoot = "C:\Users\dokul\Desktop\robot\th_poller\htdocs"
    
    if ((Test-Path $phpExe) -and (Test-Path $webRoot)) {
        # Start PHP server in background
        Start-Process $phpExe -ArgumentList "-S", "localhost:8000", "-t", "`"$webRoot`"" -WindowStyle Hidden
        Start-Sleep -Seconds 2
        Write-Host "✅ PHP server started on http://localhost:8000"
    } else {
        Write-Host "❌ PHP or web root not found"
        Write-Host "    PHP: $phpExe"
        Write-Host "    Web Root: $webRoot"
    }
}

# Open XAMPP Control Panel for monitoring
Write-Host "Opening XAMPP Control Panel..."
Start-Process $xamppPath

Write-Host ""
Write-Host "All services started!"
Write-Host "   - Apache (port 80)"
Write-Host "   - MySQL (port 3306)"
Write-Host "   - PHP Dev Server (port 8000)"
Write-Host ""
Write-Host "Check the XAMPP Control Panel to verify services are running."
