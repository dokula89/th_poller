# Daily Capture Processor Runner
# Run this script to process today's captures

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Daily Capture Processor" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if OpenAI API key is set
if (-not $env:OPENAI_API_KEY) {
    Write-Host "❌ OPENAI_API_KEY not set!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please set it first:" -ForegroundColor Yellow
    Write-Host '  $env:OPENAI_API_KEY = "sk-your-key-here"' -ForegroundColor White
    Write-Host ""
    Write-Host "Or set it permanently:" -ForegroundColor Yellow
    Write-Host '  [System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-your-key-here", "User")' -ForegroundColor White
    Write-Host ""
    exit 1
}

# Change to script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "📁 Working directory: $scriptDir" -ForegroundColor Gray
Write-Host ""

# Run the processor
Write-Host "🚀 Starting processor..." -ForegroundColor Green
Write-Host ""

python process_daily_captures.py

Write-Host ""
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Processing complete!" -ForegroundColor Green
} else {
    Write-Host "❌ Processing failed with exit code: $LASTEXITCODE" -ForegroundColor Red
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
