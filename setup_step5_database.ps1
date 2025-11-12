# Setup step5 database for Queue Poller statistics tracking
Write-Host "Creating step5 database..." -ForegroundColor Cyan

$mysqlPath = "mysql"
$sqlFile = Join-Path $PSScriptRoot "create_step5_database.sql"

# MySQL credentials (update these if different)
$mysqlHost = "127.0.0.1"
$mysqlUser = "local_uzr"
$mysqlPassword = "fuck"

# Execute the SQL file
try {
    Write-Host "Executing SQL file: $sqlFile" -ForegroundColor Yellow
    
    # Use mysql command with password
    $env:MYSQL_PWD = $mysqlPassword
    & $mysqlPath -h $mysqlHost -u $mysqlUser -e "source $sqlFile"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ step5 database created successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Database: step5" -ForegroundColor Cyan
        Write-Host "Table: apartment_changes" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "The Networks tab will now track:" -ForegroundColor Yellow
        Write-Host "  - Price changes (Δ$ column)" -ForegroundColor White
        Write-Host "  - New listings (+ column)" -ForegroundColor White
        Write-Host "  - Removed listings (- column)" -ForegroundColor White
    } else {
        Write-Host "✗ Failed to create database. Error code: $LASTEXITCODE" -ForegroundColor Red
        Write-Host "Please create the database manually using MySQL Workbench or command line." -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Alternative: Run this SQL manually in MySQL:" -ForegroundColor Yellow
    Write-Host (Get-Content $sqlFile -Raw) -ForegroundColor Gray
} finally {
    # Clear password from environment
    Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
