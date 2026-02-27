# Push updates to existing GitHub repo
# Run: Set-ExecutionPolicy Bypass -Scope Process -Force; .\github_push_update.ps1

$ErrorActionPreference = "Continue"
$sourcePath = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "=== Pushing updates to GitHub ===" -ForegroundColor Cyan
Write-Host ""

$githubUser = gh api user --jq '.login' 2>&1
Write-Host "GitHub user: $githubUser" -ForegroundColor Cyan

$tempPath = "$env:USERPROFILE\upbit-trading-system-temp"

# Remove previous temp
if (Test-Path $tempPath) { Remove-Item -Recurse -Force $tempPath }
New-Item -ItemType Directory -Path $tempPath | Out-Null

# Copy files
$excludeDirs = @(".git", "__pycache__", "node_modules", "logs", ".pytest_cache")
Get-ChildItem -Path $sourcePath -Force | Where-Object { $excludeDirs -notcontains $_.Name } | ForEach-Object {
    if ($_.PSIsContainer) { Copy-Item -Recurse -Force $_.FullName "$tempPath\$($_.Name)" }
    else { Copy-Item -Force $_.FullName "$tempPath\$($_.Name)" }
}
Get-ChildItem -Path $tempPath -Recurse -Force -Directory | Where-Object { $excludeDirs -contains $_.Name } | Sort-Object FullName -Descending | ForEach-Object {
    Remove-Item -Recurse -Force $_.FullName -ErrorAction SilentlyContinue
}

Set-Location $tempPath

# Git init and commit
git init
git branch -M main
git config user.email "challychoi@live.co.kr"
git config user.name $githubUser
git add .
git commit -m "docs: add setup.ps1 one-click installer and update README"

# Push (force to overwrite if repo already has initial commit)
$repoUrl = "https://github.com/$githubUser/upbit-trading-system.git"
git remote add origin $repoUrl
git push -u origin main --force

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "OK: Pushed!" -ForegroundColor Green
    Write-Host "https://github.com/$githubUser/upbit-trading-system" -ForegroundColor Cyan
} else {
    Write-Host "Push failed." -ForegroundColor Red
}

Set-Location $sourcePath
Remove-Item -Recurse -Force $tempPath
Write-Host "Done." -ForegroundColor Green
Read-Host "Press Enter to exit"
