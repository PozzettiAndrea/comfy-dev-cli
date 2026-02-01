# =============================================================================
# 01-WINDOWS-FEATURES.PS1
# Enables Hyper-V, Containers, WSL2, and installs Ubuntu
# =============================================================================

$ErrorActionPreference = "Stop"
$rebootNeeded = $false
$setupDir = "$env:USERPROFILE\.comfy-dev-setup"

# ============================================================================
# HYPER-V + CONTAINERS
# Only available on Pro/Enterprise/Education - enables native Docker backend
# ============================================================================
$edition = (Get-ComputerInfo).WindowsEditionId
Write-Host "Windows edition: $edition" -ForegroundColor DarkGray

if ($edition -in @("Professional","Enterprise","Education","Server")) {
    Write-Host "Checking Hyper-V + Containers..." -ForegroundColor Cyan
    $hyperv = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -ErrorAction SilentlyContinue
    $containers = Get-WindowsOptionalFeature -Online -FeatureName Containers -ErrorAction SilentlyContinue
    
    if (($hyperv.State -ne "Enabled") -or ($containers.State -ne "Enabled")) {
        Write-Host "Enabling Hyper-V and Containers..." -ForegroundColor Yellow
        Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All, Containers -All -NoRestart
        Write-Host "Hyper-V and Containers enabled" -ForegroundColor Green
        $rebootNeeded = $true
    } else {
        Write-Host "Hyper-V and Containers already enabled" -ForegroundColor DarkGray
    }
} else {
    Write-Host "Windows Home detected - using WSL2 backend only" -ForegroundColor Yellow
}

# ============================================================================
# WSL2
# Required for Docker on Windows Home, useful everywhere
# ============================================================================
Write-Host "Configuring WSL2..." -ForegroundColor Yellow
wsl --update 2>$null
wsl --set-default-version 2 2>$null
Write-Host "WSL2 configured" -ForegroundColor Green

# ============================================================================
# UBUNTU
# Linux environment for Docker GPU passthrough and Linux runner
# ============================================================================
$wslDistros = wsl --list --quiet 2>$null
if ($wslDistros -match "Ubuntu") {
    Write-Host "Ubuntu already installed in WSL2" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Ubuntu in WSL2..." -ForegroundColor Yellow
    wsl --install -d Ubuntu --no-launch
    Write-Host "Ubuntu installed" -ForegroundColor Green
    $rebootNeeded = $true
}

# ============================================================================
# REBOOT FLAG
# Signal to main script that reboot is needed
# ============================================================================
if ($rebootNeeded) {
    New-Item -ItemType File -Force -Path "$setupDir\.reboot-needed" | Out-Null
}

Write-Host "Windows features setup complete" -ForegroundColor Green
