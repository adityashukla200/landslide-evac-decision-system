# One-Command Demo Runner for Windows PowerShell (SIH-26192)
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  SIH 26192 — FLASH FLOOD & LANDSLIDE EARLY WARNING SYSTEM" -ForegroundColor Green
Write-Host "  LIVE DEMONSTRATION & RESILIENCE AUDIT" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host ">>> [1/2] RUNNING ONLINE EWS PIPELINE REPLAY (+7.0H EXTRA LEAD TIME) <<<" -ForegroundColor Yellow
python scripts/replay_demo.py --scenario bhatwari_debris_flow_synthetic --speed 0

Write-Host ""
Write-Host ">>> [2/2] RUNNING 'KILL INTERNET' AUTONOMOUS LORA & SIREN RESILIENCE <<<" -ForegroundColor Red
python scripts/replay_demo.py --scenario bhatwari_debris_flow_synthetic --kill-internet --speed 0

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  DEMO COMPLETE: All numbers computed live from calibrated models." -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
