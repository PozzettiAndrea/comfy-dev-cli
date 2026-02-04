# =============================================================================
# 02-DEV-TOOLS.PS1
# Installs Git, Claude Code, Miniconda, uv, GitHub CLI, Docker, act
# =============================================================================

$ErrorActionPreference = "Stop"

# ============================================================================
# GIT
# Version control - silent install with sensible defaults
# ============================================================================
if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Host "Git already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Git..." -ForegroundColor Yellow
    $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-64-bit.exe"
    $gitInstaller = "$env:TEMP\Git-installer.exe"
    Invoke-WebRequest -Uri $gitUrl -OutFile $gitInstaller
    Start-Process $gitInstaller -ArgumentList "/VERYSILENT","/NORESTART","/NOCANCEL","/SP-" -Wait
    Remove-Item $gitInstaller
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
if (Get-Command claude -ErrorAction SilentlyContinue) {
    Write-Host "Claude Code already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Claude Code..." -ForegroundColor Yellow
    irm https://claude.ai/install.ps1 | iex
    Write-Host "Claude Code installed" -ForegroundColor Green
}

# ============================================================================
# MINICONDA
# Python environment management - keeps system Python clean
# ============================================================================
if (Test-Path "$env:USERPROFILE\miniconda3\condabin\conda.bat") {
    Write-Host "Miniconda already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Miniconda..." -ForegroundColor Yellow
    $url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
    $exe = "$env:TEMP\Miniconda3.exe"
    Invoke-WebRequest $url -OutFile $exe
    Start-Process $exe -ArgumentList "/InstallationType=JustMe","/RegisterPython=0","/S","/D=$env:USERPROFILE\miniconda3" -Wait
    Remove-Item $exe
    [Environment]::SetEnvironmentVariable("Path", "$env:USERPROFILE\miniconda3\condabin;" + [Environment]::GetEnvironmentVariable("Path","User"), "User")
    Write-Host "Miniconda installed" -ForegroundColor Green
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
# Authenticate and manage repos from terminal
# ============================================================================
if (Get-Command gh -ErrorAction SilentlyContinue) {
    Write-Host "GitHub CLI already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing GitHub CLI..." -ForegroundColor Yellow
    $url = "https://github.com/cli/cli/releases/download/v2.63.2/gh_2.63.2_windows_amd64.msi"
    $msi = "$env:TEMP\gh.msi"
    Invoke-WebRequest $url -OutFile $msi
    Start-Process "msiexec.exe" -ArgumentList "/i",$msi,"/qn","/norestart" -Wait
    Remove-Item $msi
    Write-Host "GitHub CLI installed" -ForegroundColor Green
}

# ============================================================================
# DOCKER DESKTOP
# Container runtime - uses Hyper-V on Pro+, WSL2 on Home
# ============================================================================
$dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerExe) {
    Write-Host "Docker Desktop already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Docker Desktop..." -ForegroundColor Yellow
    $url = "https://desktop.docker.com/win/stable/Docker%20Desktop%20Installer.exe"
    $exe = "$env:TEMP\DockerDesktopInstaller.exe"
    Invoke-WebRequest $url -OutFile $exe
    Start-Process $exe -ArgumentList "install","--quiet","--accept-license" -Wait
    Remove-Item $exe
    Write-Host "Docker Desktop installed" -ForegroundColor Green
}

# ============================================================================
# NETWORKING FIX
# Disable RSC - fixes container networking issues on some systems
# ============================================================================
Write-Host "Disabling RSC (container networking fix)..." -ForegroundColor Yellow
Get-NetAdapterRsc | Disable-NetAdapterRsc -ErrorAction SilentlyContinue

# ============================================================================
# ACT
# Run GitHub Actions locally - great for testing CI before pushing
# ============================================================================
if (Get-Command act -ErrorAction SilentlyContinue) {
    Write-Host "act already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing act..." -ForegroundColor Yellow
    $zip = "$env:TEMP\act.zip"
    Invoke-WebRequest "https://github.com/nektos/act/releases/latest/download/act_Windows_x86_64.zip" -OutFile $zip
    Expand-Archive $zip "$env:ProgramFiles\act" -Force
    [Environment]::SetEnvironmentVariable("Path", "$env:ProgramFiles\act;" + [Environment]::GetEnvironmentVariable("Path","Machine"), "Machine")
    Remove-Item $zip
    Write-Host "act installed" -ForegroundColor Green
}

Write-Host "Dev tools setup complete" -ForegroundColor Green
