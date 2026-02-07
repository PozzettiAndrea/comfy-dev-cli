# =============================================================================
# 02-DEV-TOOLS.PS1
# Installs Git, Claude Code, uv, GitHub CLI, zstd, 7-Zip, tar, Docker
# =============================================================================

$ErrorActionPreference = "Stop"

# Helper: refresh PATH from registry (picks up changes from installers)
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
}

# ============================================================================
# CHOCOLATEY
# Package manager - needed for packages not available via winget
# ============================================================================
if (Get-Command choco -ErrorAction SilentlyContinue) {
    Write-Host "Chocolatey already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Chocolatey..." -ForegroundColor Yellow
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    Refresh-Path
    Write-Host "Chocolatey installed" -ForegroundColor Green
}

# ============================================================================
# NVIDIA DISPLAY DRIVER
# GPU driver - installed via Chocolatey (not available on winget)
# Non-fatal: may fail on VMs or systems without NVIDIA hardware
# ============================================================================
$nvidiaDriver = choco list --local-only nvidia-display-driver 2>$null
if ($nvidiaDriver -match "nvidia-display-driver") {
    Write-Host "NVIDIA display driver already installed via Chocolatey" -ForegroundColor DarkGray
} else {
    Write-Host "Installing NVIDIA display driver..." -ForegroundColor Yellow
    try {
        choco install nvidia-display-driver -y
        Write-Host "NVIDIA display driver installed" -ForegroundColor Green
    } catch {
        Write-Host "WARNING: NVIDIA display driver installation failed. This is non-fatal." -ForegroundColor Yellow
        Write-Host "  You may need to install the driver manually if you have NVIDIA hardware." -ForegroundColor Yellow
    }
}

# ============================================================================
# GIT
# Version control - installed via winget (--source winget skips msstore)
# ============================================================================
if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Host "Git already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Git..." -ForegroundColor Yellow
    winget install -e --id Git.Git --source winget --silent --accept-package-agreements --accept-source-agreements
    Refresh-Path
    Write-Host "Git installed" -ForegroundColor Green
}

# Git config - sensible defaults (only if git is available)
if (Get-Command git -ErrorAction SilentlyContinue) {
    git config --global core.autocrlf false 2>$null
    git config --global core.longpaths true 2>$null
}

# ============================================================================
# CLONE COMFY-DEV-CLI TO DESKTOP
# Clone early -- before Docker/RSC changes that can disrupt networking
# ============================================================================
if (Get-Command git -ErrorAction SilentlyContinue) {
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $repoDir = "$desktopPath\comfy-dev-cli"
    if (Test-Path "$repoDir\.git") {
        Write-Host "comfy-dev-cli already cloned on Desktop" -ForegroundColor DarkGray
    } else {
        Write-Host "Cloning comfy-dev-cli to Desktop..." -ForegroundColor Yellow
        if (Test-Path $repoDir) { Remove-Item $repoDir -Recurse -Force }
        git clone https://github.com/PozzettiAndrea/comfy-dev-cli.git $repoDir
        Write-Host "comfy-dev-cli cloned to $repoDir" -ForegroundColor Green
    }
}

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
    winget install -e --id GitHub.cli --source winget --silent --accept-package-agreements --accept-source-agreements
    Refresh-Path
    Write-Host "GitHub CLI installed" -ForegroundColor Green
}

# ============================================================================
# ZSTD
# Fast compression tool - installed via winget
# ============================================================================
if (Get-Command zstd -ErrorAction SilentlyContinue) {
    Write-Host "zstd already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing zstd..." -ForegroundColor Yellow
    winget install -e --id Facebook.zstd --source winget --silent --accept-package-agreements --accept-source-agreements
    Refresh-Path
    Write-Host "zstd installed" -ForegroundColor Green
}

# ============================================================================
# 7-ZIP
# Archive utility for .7z files - installed via winget
# ============================================================================
if (Test-Path "C:\Program Files\7-Zip\7z.exe") {
    Write-Host "7-Zip already installed" -ForegroundColor DarkGray
} else {
    Write-Host "Installing 7-Zip..." -ForegroundColor Yellow
    winget install -e --id 7zip.7zip --source winget --silent --accept-package-agreements --accept-source-agreements
    Write-Host "7-Zip installed" -ForegroundColor Green
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
    winget install -e --id Docker.DockerDesktop --source winget --silent --accept-package-agreements --accept-source-agreements
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
