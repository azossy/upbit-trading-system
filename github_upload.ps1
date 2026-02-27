# GitHub Upload Script for upbit-trading-system
# Run: Set-ExecutionPolicy Bypass -Scope Process -Force; .\github_upload.ps1

$ErrorActionPreference = "Continue"
$sourcePath = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "=== upbit-trading-system GitHub Upload ===" -ForegroundColor Cyan
Write-Host ""

# STEP 1: Check / install gh CLI
Write-Host "[1/6] Checking GitHub CLI..." -ForegroundColor Yellow
gh --version 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Installing gh via winget..." -ForegroundColor Red
    winget install --id GitHub.cli --silent --accept-source-agreements --accept-package-agreements
    $mp = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
    $up = [System.Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = $mp + ';' + $up
    gh --version 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Open a new PowerShell window and run again." -ForegroundColor Red
        Read-Host "Press Enter to exit"; exit 1
    }
}
Write-Host "  OK" -ForegroundColor Green

# STEP 2: GitHub login + get username
Write-Host ""
Write-Host "[2/6] Checking GitHub login..." -ForegroundColor Yellow
gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    gh auth login --web --git-protocol https
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Login failed." -ForegroundColor Red
        exit 1
    }
}
$githubUser = gh api user --jq '.login' 2>&1
Write-Host "  OK: Logged in as $githubUser" -ForegroundColor Green

# STEP 3: Copy project to new user-owned folder (bypass VM ownership issue)
Write-Host ""
Write-Host "[3/6] Copying project to user-owned temp folder..." -ForegroundColor Yellow
$tempPath = "$env:USERPROFILE\upbit-trading-system-temp"

# Remove previous temp if exists
if (Test-Path $tempPath) {
    Remove-Item -Recurse -Force $tempPath
}
New-Item -ItemType Directory -Path $tempPath | Out-Null

# Copy all files except .git, __pycache__, node_modules, logs
$excludeDirs = @(".git", "__pycache__", "node_modules", "logs", ".pytest_cache")
Get-ChildItem -Path $sourcePath -Force | Where-Object {
    $excludeDirs -notcontains $_.Name
} | ForEach-Object {
    if ($_.PSIsContainer) {
        Copy-Item -Recurse -Force $_.FullName "$tempPath\$($_.Name)"
    } else {
        Copy-Item -Force $_.FullName "$tempPath\$($_.Name)"
    }
}
# Also remove nested __pycache__ and .git inside copied folders
Get-ChildItem -Path $tempPath -Recurse -Force -Directory | Where-Object {
    $excludeDirs -contains $_.Name
} | Sort-Object FullName -Descending | ForEach-Object {
    Remove-Item -Recurse -Force $_.FullName -ErrorAction SilentlyContinue
}

Set-Location $tempPath
Write-Host "  OK: Copied to $tempPath" -ForegroundColor Green

# STEP 4: Git init, add, commit
Write-Host ""
Write-Host "[4/6] Git init and commit..." -ForegroundColor Yellow
git init
git branch -M main
git config user.email "challychoi@live.co.kr"
git config user.name $githubUser
git add .
$fileCount = (git diff --cached --name-only).Count
Write-Host "  Staged $fileCount files" -ForegroundColor Cyan
git commit -m "feat: initial commit - upbit auto trading system"
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK: Committed" -ForegroundColor Green
} else {
    Write-Host "  Commit failed!" -ForegroundColor Red
    Read-Host "Press Enter to exit"; exit 1
}

# STEP 5: Create GitHub repo
Write-Host ""
Write-Host "[5/6] Creating GitHub repo..." -ForegroundColor Yellow
$vis = Read-Host "  Public repo? (y=public, n=private)"
if ($vis -eq 'y' -or $vis -eq 'Y') { $visFlag = '--public' } else { $visFlag = '--private' }
gh repo create upbit-trading-system $visFlag --description "Upbit auto trading system - FastAPI + React + Docker"
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK: Repo created" -ForegroundColor Green
} else {
    Write-Host "  (Repo may already exist, continuing...)" -ForegroundColor Yellow
}

# STEP 6: Push
Write-Host ""
Write-Host "[6/6] Pushing to GitHub..." -ForegroundColor Yellow
$repoUrl = "https://github.com/$githubUser/upbit-trading-system.git"
git remote remove origin 2>&1 | Out-Null
git remote add origin $repoUrl
git push -u origin main
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK: Pushed!" -ForegroundColor Green
} else {
    Write-Host "  Push failed." -ForegroundColor Red
}

# Done
$finalUrl = "https://github.com/$githubUser/upbit-trading-system"
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Done! --> $finalUrl" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green

# Clean up temp folder
Set-Location $sourcePath
Remove-Item -Recurse -Force $tempPath
Write-Host "  Temp folder cleaned up." -ForegroundColor Gray

Write-Host ""
$open = Read-Host "Open in browser? (y/n)"
if ($open -eq 'y' -or $open -eq 'Y') { Start-Process $finalUrl }
Read-Host "Press Enter to exit"
