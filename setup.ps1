# =============================================================
#  upbit-trading-system - One-Click Setup Script
#  Run as Administrator:
#  Set-ExecutionPolicy Bypass -Scope Process -Force; .\setup.ps1
# =============================================================

$ErrorActionPreference = "Continue"
$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectPath

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   Upbit Auto Trading System - Setup" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# ── Helper: check if command exists ──────────────────────────
function Test-Command($cmd) {
    $null = Get-Command $cmd -ErrorAction SilentlyContinue
    return $?
}

# ── Helper: refresh PATH without restarting PowerShell ───────
function Refresh-Path {
    $mp = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
    $up = [System.Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = $mp + ';' + $up
}

# =============================================================
# STEP 1: winget 확인
# =============================================================
Write-Host "[1/5] Checking winget..." -ForegroundColor Yellow
if (-not (Test-Command "winget")) {
    Write-Host "  winget not found." -ForegroundColor Red
    Write-Host "  Please install App Installer from Microsoft Store:" -ForegroundColor Yellow
    Write-Host "  https://apps.microsoft.com/detail/9NBLGGH4NNS1" -ForegroundColor Cyan
    Start-Process "https://apps.microsoft.com/detail/9NBLGGH4NNS1"
    Read-Host "  After installing, press Enter to continue"
    Refresh-Path
}
Write-Host "  OK: winget available" -ForegroundColor Green

# =============================================================
# STEP 2: Git 설치
# =============================================================
Write-Host ""
Write-Host "[2/5] Checking Git..." -ForegroundColor Yellow
if (-not (Test-Command "git")) {
    Write-Host "  Git not found. Installing..." -ForegroundColor Red
    winget install --id Git.Git --silent --accept-source-agreements --accept-package-agreements
    Refresh-Path
    if (-not (Test-Command "git")) {
        Write-Host "  Please open a new PowerShell window and run setup.ps1 again." -ForegroundColor Red
        Read-Host "Press Enter to exit"; exit 1
    }
    Write-Host "  OK: Git installed" -ForegroundColor Green
} else {
    $gv = git --version
    Write-Host "  OK: $gv" -ForegroundColor Green
}

# =============================================================
# STEP 3: Docker Desktop 설치
# =============================================================
Write-Host ""
Write-Host "[3/5] Checking Docker Desktop..." -ForegroundColor Yellow
if (-not (Test-Command "docker")) {
    Write-Host "  Docker not found. Installing Docker Desktop..." -ForegroundColor Red
    Write-Host "  (This may take a few minutes)" -ForegroundColor Gray
    winget install --id Docker.DockerDesktop --silent --accept-source-agreements --accept-package-agreements
    Refresh-Path

    if (-not (Test-Command "docker")) {
        Write-Host ""
        Write-Host "  Docker Desktop installed but requires a REBOOT." -ForegroundColor Yellow
        Write-Host "  Please:" -ForegroundColor Yellow
        Write-Host "   1. Reboot your computer" -ForegroundColor White
        Write-Host "   2. Launch Docker Desktop and wait for it to start" -ForegroundColor White
        Write-Host "   3. Run setup.ps1 again" -ForegroundColor White
        Read-Host "Press Enter to exit"; exit 0
    }
} else {
    $dv = docker --version
    Write-Host "  OK: $dv" -ForegroundColor Green
}

# Docker daemon running?
docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Docker Desktop is not running. Starting..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
    Write-Host "  Waiting for Docker to start (30s)..." -ForegroundColor Gray
    Start-Sleep -Seconds 30
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Docker is still not ready. Please start Docker Desktop manually and run setup.ps1 again." -ForegroundColor Red
        Read-Host "Press Enter to exit"; exit 1
    }
}
Write-Host "  OK: Docker is running" -ForegroundColor Green

# =============================================================
# STEP 4: .env 파일 생성
# =============================================================
Write-Host ""
Write-Host "[4/5] Setting up .env file..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "  .env already exists, skipping." -ForegroundColor Green
} else {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "  Created .env from .env.example" -ForegroundColor Green
        Write-Host ""
        Write-Host "  *** IMPORTANT: Edit .env and fill in your settings ***" -ForegroundColor Yellow
        Write-Host "  Required:" -ForegroundColor White
        Write-Host "    UPBIT_ACCESS_KEY  - Your Upbit API access key" -ForegroundColor Gray
        Write-Host "    UPBIT_SECRET_KEY  - Your Upbit API secret key" -ForegroundColor Gray
        Write-Host "  Optional:" -ForegroundColor White
        Write-Host "    TELEGRAM_BOT_TOKEN - For trade notifications" -ForegroundColor Gray
        Write-Host "    TELEGRAM_CHAT_ID   - Your Telegram chat ID" -ForegroundColor Gray
        Write-Host ""
        $editNow = Read-Host "  Open .env in Notepad now? (y/n)"
        if ($editNow -eq 'y' -or $editNow -eq 'Y') {
            notepad ".env"
            Read-Host "  After editing .env, press Enter to continue"
        }
    } else {
        Write-Host "  .env.example not found! Please create .env manually." -ForegroundColor Red
    }
}

# =============================================================
# STEP 5: Docker Compose 빌드 및 실행
# =============================================================
Write-Host ""
Write-Host "[5/5] Building and starting services with Docker Compose..." -ForegroundColor Yellow
Write-Host "  (First build may take 5-10 minutes)" -ForegroundColor Gray
Write-Host ""
docker compose up -d --build
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "  OK: All services started!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  docker compose up failed. Check errors above." -ForegroundColor Red
    Read-Host "Press Enter to exit"; exit 1
}

# =============================================================
# Done
# =============================================================
Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "   Setup Complete!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Access URLs:" -ForegroundColor Cyan
Write-Host "   Frontend  -> http://localhost:3000" -ForegroundColor White
Write-Host "   API Docs  -> http://localhost:8000/docs" -ForegroundColor White
Write-Host "   Admin     -> admin@example.com / Admin1234!" -ForegroundColor White
Write-Host ""
Write-Host "  Useful commands:" -ForegroundColor Cyan
Write-Host "   docker compose ps          # check service status" -ForegroundColor Gray
Write-Host "   docker compose logs -f     # view live logs" -ForegroundColor Gray
Write-Host "   docker compose down        # stop all services" -ForegroundColor Gray
Write-Host ""

$openFrontend = Read-Host "Open http://localhost:3000 in browser? (y/n)"
if ($openFrontend -eq 'y' -or $openFrontend -eq 'Y') {
    Start-Process "http://localhost:3000"
}
$openDocs = Read-Host "Open API docs (http://localhost:8000/docs) in browser? (y/n)"
if ($openDocs -eq 'y' -or $openDocs -eq 'Y') {
    Start-Process "http://localhost:8000/docs"
}

Read-Host "Press Enter to exit"
