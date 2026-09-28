<#
.SYNOPSIS
    Cross-platform Windows PowerShell task runner for Hilly-Region EWS.
.DESCRIPTION
    Provides exact equivalents of Makefile targets on Windows:
    ./scripts/run.ps1 up
    ./scripts/run.ps1 down
    ./scripts/run.ps1 test
    ./scripts/run.ps1 seed
#>

param (
    [Parameter(Position=0, Mandatory=$false)]
    [ValidateSet("up", "down", "test", "seed", "clean", "help")]
    [string]$Target = "help"
)

$ErrorActionPreference = "Stop"

switch ($Target) {
    "up" {
        Write-Host ">>> Launching Docker Compose services..." -ForegroundColor Cyan
        if (Get-Command docker -ErrorAction SilentlyContinue) {
            docker compose up -d --build
        } else {
            Write-Host "[!] Docker CLI is not installed or running on this machine." -ForegroundColor Yellow
            Write-Host ">>> Running in native local offline mode with SQLite and Uvicorn:" -ForegroundColor Green
            python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
        }
    }
    "down" {
        Write-Host ">>> Stopping Docker Compose services..." -ForegroundColor Cyan
        if (Get-Command docker -ErrorAction SilentlyContinue) {
            docker compose down
        } else {
            Write-Host "Docker is not running." -ForegroundColor Yellow
        }
    }
    "test" {
        Write-Host ">>> Running test suite..." -ForegroundColor Cyan
        python -m pytest tests/ -v
    }
    "seed" {
        Write-Host ">>> Seeding 25 Uttarkashi pilot villages..." -ForegroundColor Cyan
        python scripts/seed_data.py
    }
    "clean" {
        Write-Host ">>> Cleaning containers and volumes..." -ForegroundColor Cyan
        if (Get-Command docker -ErrorAction SilentlyContinue) {
            docker compose down -v
        }
        if (Test-Path "data/ews.db") {
            Remove-Item "data/ews.db" -Force
            Write-Host "Removed local SQLite database: data/ews.db" -ForegroundColor Green
        }
    }
    "help" {
        Write-Host "Hilly-Region Flash Flood & Landslide EWS (Windows PowerShell Runner)" -ForegroundColor Green
        Write-Host "Usage: ./scripts/run.ps1 [command]"
        Write-Host "  up    : Build and start Docker services (or run locally if no Docker)"
        Write-Host "  down  : Stop Docker services"
        Write-Host "  test  : Run pytest test suite"
        Write-Host "  seed  : Seed 25 synthetic Uttarkashi pilot villages"
        Write-Host "  clean : Clean containers, volumes, and local SQLite db"
    }
}
