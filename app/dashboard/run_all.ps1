# DriftGuards AI - Unified Launcher (PowerShell)
# Runs both Streamlit Dashboard and Auto-Scheduler

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "🚀 DriftGuards AI - Unified Launcher" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting both Streamlit Dashboard and Auto-Scheduler..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop both processes" -ForegroundColor Yellow
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Start Streamlit in background
Write-Host "🌐 Starting Streamlit Dashboard..." -ForegroundColor Green
$streamlitJob = Start-Job -Name "DriftGuards-Streamlit" -ScriptBlock {
    param($path)
    Set-Location $path
    python -m streamlit run app.py
} -ArgumentList $scriptPath

Start-Sleep -Seconds 3

# Start Auto-Scheduler in background
Write-Host "🤖 Starting Auto-Scheduler..." -ForegroundColor Green
$schedulerJob = Start-Job -Name "DriftGuards-Scheduler" -ScriptBlock {
    param($path)
    Set-Location $path
    python auto_scheduler.py
} -ArgumentList $scriptPath

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "✅ Both services started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Streamlit Dashboard: http://localhost:8501" -ForegroundColor Cyan
Write-Host "🤖 Auto-Scheduler: Running in background" -ForegroundColor Cyan
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Commands:" -ForegroundColor Yellow
Write-Host "  View Streamlit output:     Receive-Job -Name 'DriftGuards-Streamlit'" -ForegroundColor White
Write-Host "  View Scheduler output:     Receive-Job -Name 'DriftGuards-Scheduler'" -ForegroundColor White
Write-Host "  Check job status:          Get-Job" -ForegroundColor White
Write-Host "  Stop all services:         Press Ctrl+C or run stop_all.ps1" -ForegroundColor White
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

try {
    Write-Host "Press Ctrl+C to stop all services..." -ForegroundColor Yellow
    Write-Host ""
    
    # Monitor jobs and display output
    while ($true) {
        # Check if jobs are still running
        $streamlitState = (Get-Job -Name "DriftGuards-Streamlit").State
        $schedulerState = (Get-Job -Name "DriftGuards-Scheduler").State
        
        if ($streamlitState -eq "Failed" -or $schedulerState -eq "Failed") {
            Write-Host ""
            Write-Host "❌ One or more services failed!" -ForegroundColor Red
            Write-Host ""
            Write-Host "Streamlit output:" -ForegroundColor Yellow
            Receive-Job -Name "DriftGuards-Streamlit"
            Write-Host ""
            Write-Host "Scheduler output:" -ForegroundColor Yellow
            Receive-Job -Name "DriftGuards-Scheduler"
            break
        }
        
        Start-Sleep -Seconds 5
    }
}
catch {
    Write-Host ""
    Write-Host "⚠️  Stopping services..." -ForegroundColor Yellow
}
finally {
    # Stop all jobs
    Write-Host ""
    Write-Host "🛑 Stopping Streamlit..." -ForegroundColor Yellow
    Stop-Job -Name "DriftGuards-Streamlit" -ErrorAction SilentlyContinue
    Remove-Job -Name "DriftGuards-Streamlit" -Force -ErrorAction SilentlyContinue
    
    Write-Host "🛑 Stopping Auto-Scheduler..." -ForegroundColor Yellow
    Stop-Job -Name "DriftGuards-Scheduler" -ErrorAction SilentlyContinue
    Remove-Job -Name "DriftGuards-Scheduler" -Force -ErrorAction SilentlyContinue
    
    Write-Host ""
    Write-Host "✅ All services stopped" -ForegroundColor Green
    Write-Host "👋 Goodbye!" -ForegroundColor Cyan
    Write-Host ""
}
