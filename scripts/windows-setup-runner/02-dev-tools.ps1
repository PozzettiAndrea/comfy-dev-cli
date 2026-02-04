# =============================================================================
# 02-DEV-TOOLS.PS1
# Installs Git, Claude Code, uv, GitHub CLI, zstd, tar, Docker
# =============================================================================

$ErrorActionPreference = "Stop"

# ============================================================================
# GIT
# Version control - installed via winget
# ============================================================================
if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Host "Git already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Git..." -ForegroundColor Yellow
    winget install -e --id Git.Git --silent --accept-package-agreements --accept-source-agreements
    # Refresh PATH
    $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
    Write-Host "Git installed" -ForegroundColor Green
}

# Git config - sensible defaults
git config --global core.autocrlf false 2>$null
git config --global core.longpaths true 2>$null

# ============================================================================
# CLAUDE CODE
# AI coding assistant - native installer with auto-updates
# ============================================================================
$claudeExe = "$env:USERPROFILE\.local\bin\claude.exe"
if ((Get-Command claude -ErrorAction SilentlyContinue) -or (Test-Path $claudeExe)) {
    Write-Host "Claude Code already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Claude Code..." -ForegroundColor Yellow
    irm https://claude.ai/install.ps1 | iex
    Write-Host "Claude Code installed" -ForegroundColor Green
}

# ============================================================================
# UV
# Fast Python package installer from Astral (replaces pip for speed)
# ============================================================================
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "uv already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing uv..." -ForegroundColor Yellow
    powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
    Write-Host "uv installed" -ForegroundColor Green
}

# ============================================================================
# GITHUB CLI
# Authenticate and manage repos from terminal - installed via winget
# ============================================================================
if (Get-Command gh -ErrorAction SilentlyContinue) {
    Write-Host "GitHub CLI already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing GitHub CLI..." -ForegroundColor Yellow
    winget install -e --id GitHub.cli --silent --accept-package-agreements --accept-source-agreements
    Write-Host "GitHub CLI installed" -ForegroundColor Green
}

# ============================================================================
# ZSTD
# Fast compression tool - used by many package managers and build systems
# ============================================================================
if (Get-Command zstd -ErrorAction SilentlyContinue) {
    Write-Host "zstd already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing zstd..." -ForegroundColor Yellow
    $url = "https://github.com/facebook/zstd/releases/download/v1.5.6/zstd-v1.5.6-win64.zip"
    $zip = "$env:TEMP\zstd.zip"
    Invoke-WebRequest $url -OutFile $zip
    Expand-Archive $zip "$env:ProgramFiles\zstd" -Force
    [Environment]::SetEnvironmentVariable("Path", "$env:ProgramFiles\zstd\zstd-v1.5.6-win64;" + [Environment]::GetEnvironmentVariable("Path","Machine"), "Machine")
    $env:Path = "$env:ProgramFiles\zstd\zstd-v1.5.6-win64;" + $env:Path
    Remove-Item $zip
    Write-Host "zstd installed" -ForegroundColor Green
}

# ============================================================================
# TAR
# Archive utility - built into Windows 10+, verify it's available
# ============================================================================
if (Get-Command tar -ErrorAction SilentlyContinue) {
    Write-Host "tar already available" -ForegroundColor DarkGray
} else {
    Write-Host "WARNING: tar not found. This should be built into Windows 10+." -ForegroundColor Red
    Write-Host "  Please ensure you are running Windows 10 version 1803 or later." -ForegroundColor Yellow
}

# ============================================================================
# DOCKER DESKTOP
# Container runtime - installed via winget
# ============================================================================
$dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerExe) {
    Write-Host "Docker Desktop already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Docker Desktop..." -ForegroundColor Yellow
    winget install -e --id Docker.DockerDesktop --silent --accept-package-agreements --accept-source-agreements
    Write-Host "Docker Desktop installed" -ForegroundColor Green
}

# ============================================================================
# NETWORKING FIX
# Disable RSC - fixes container networking issues on some systems
# ============================================================================
$rscAdapters = Get-NetAdapterRsc | Where-Object { $_.IPv4Enabled -or $_.IPv6Enabled }
if ($rscAdapters) {
    Write-Host "Disabling RSC (container networking fix)..." -ForegroundColor Yellow
    Get-NetAdapterRsc | Disable-NetAdapterRsc -ErrorAction SilentlyContinue
    Write-Host "RSC disabled" -ForegroundColor Green
} else {
    Write-Host "RSC already disabled" -ForegroundColor DarkGray
}

Write-Host "Dev tools setup complete" -ForegroundColor Green
