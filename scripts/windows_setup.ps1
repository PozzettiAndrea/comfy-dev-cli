$ErrorActionPreference = "Stop"

$global:needsRestart = $false

Write-Host "=== TensorDock Dev Environment Setup ===" -ForegroundColor Cyan

# Windows edition detection
$edition = (Get-ComputerInfo).WindowsEditionId

Write-Host "Windows edition: $edition" -ForegroundColor DarkGray

if ($edition -in @("Professional","Enterprise","Education","Server")) {
    Write-Host "Checking Hyper-V + Containers..." -ForegroundColor Cyan
    $hyperv = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -ErrorAction SilentlyContinue
    $containers = Get-WindowsOptionalFeature -Online -FeatureName Containers -ErrorAction SilentlyContinue

    if (($hyperv.State -ne "Enabled") -or ($containers.State -ne "Enabled")) {
        Write-Host "Enabling Hyper-V and Containers..." -ForegroundColor Yellow
        Enable-WindowsOptionalFeature -Online `
            -FeatureName Microsoft-Hyper-V-All, Containers `
            -All -NoRestart
        Write-Host "Hyper-V and Containers enabled" -ForegroundColor Green
        $global:needsRestart = $true
    } else {
        Write-Host "Hyper-V and Containers already enabled, skipping" -ForegroundColor DarkGray
    }
} else {
    Write-Host "Windows Home detected - using WSL2 backend only (Docker-supported)" -ForegroundColor Yellow
    Write-Host "Skipping Hyper-V / Containers (not available on Home)" -ForegroundColor DarkGray
}

# Update WSL
Write-Host "Updating WSL..." -ForegroundColor Yellow
wsl --update
Write-Host "WSL updated" -ForegroundColor Green

# Git installation
if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Host "Git already installed, skipping" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Git..." -ForegroundColor Yellow
    $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-64-bit.exe"
    $gitInstaller = "$env:TEMP\Git-installer.exe"
    Invoke-WebRequest -Uri $gitUrl -OutFile $gitInstaller
    Start-Process $gitInstaller -ArgumentList "/VERYSILENT","/NORESTART","/NOCANCEL","/SP-" -Wait
    Remove-Item $gitInstaller
    Write-Host "Git installed" -ForegroundColor Green
}

# Node.js installation
if (Get-Command node -ErrorAction SilentlyContinue) {
    Write-Host "Node.js already installed, skipping" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Node.js LTS..." -ForegroundColor Yellow
    $nodeUrl = "https://nodejs.org/dist/v22.12.0/node-v22.12.0-x64.msi"
    $nodeInstaller = "$env:TEMP\node-installer.msi"
    Invoke-WebRequest -Uri $nodeUrl -OutFile $nodeInstaller
    Start-Process "msiexec.exe" -ArgumentList "/i",$nodeInstaller,"/qn","/norestart" -Wait
    Remove-Item $nodeInstaller
    Write-Host "Node.js installed" -ForegroundColor Green
}

# Refresh PATH
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
    [Environment]::GetEnvironmentVariable("Path","User")

# Claude Code installation
if (Get-Command claude -ErrorAction SilentlyContinue) {
    Write-Host "Claude Code already installed, skipping" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Claude Code..." -ForegroundColor Yellow
    & "C:\Program Files\nodejs\npm.cmd" install -g @anthropic-ai/claude-code --ignore-scripts
    & "C:\Program Files\nodejs\npm.cmd" install -g win-claude-code
    Write-Host "Claude Code installed" -ForegroundColor Green
}

# Miniconda installation
if (Test-Path "$env:USERPROFILE\miniconda3\condabin\conda.bat") {
    Write-Host "Miniconda already installed, skipping" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Miniconda..." -ForegroundColor Yellow
    $url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
    $exe = "$env:TEMP\Miniconda3.exe"
    Invoke-WebRequest $url -OutFile $exe
    Start-Process $exe -ArgumentList "/InstallationType=JustMe","/RegisterPython=0","/S","/D=$env:USERPROFILE\miniconda3" -Wait
    Remove-Item $exe
    [Environment]::SetEnvironmentVariable(
        "Path",
        "$env:USERPROFILE\miniconda3\condabin;" + [Environment]::GetEnvironmentVariable("Path","User"),
        "User"
    )
    Write-Host "Miniconda installed" -ForegroundColor Green
}

# uv installation
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "uv already installed, skipping" -ForegroundColor DarkGray
} else {
    Write-Host "Installing uv..." -ForegroundColor Yellow
    powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
    Write-Host "uv installed" -ForegroundColor Green
}

# GitHub CLI installation
if (Get-Command gh -ErrorAction SilentlyContinue) {
    Write-Host "GitHub CLI already installed, skipping" -ForegroundColor DarkGray
} else {
    Write-Host "Installing GitHub CLI..." -ForegroundColor Yellow
    $url = "https://github.com/cli/cli/releases/download/v2.63.2/gh_2.63.2_windows_amd64.msi"
    $msi = "$env:TEMP\gh.msi"
    Invoke-WebRequest $url -OutFile $msi
    Start-Process "msiexec.exe" -ArgumentList "/i",$msi,"/qn","/norestart" -Wait
    Remove-Item $msi
    Write-Host "GitHub CLI installed" -ForegroundColor Green
}

# Docker Desktop installation
$dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerExe) {
    Write-Host "Docker Desktop already installed, skipping" -ForegroundColor DarkGray
} else {
    Write-Host "Installing Docker Desktop..." -ForegroundColor Yellow
    $url = "https://desktop.docker.com/win/stable/Docker%20Desktop%20Installer.exe"
    $exe = "$env:TEMP\DockerDesktopInstaller.exe"
    Invoke-WebRequest $url -OutFile $exe
    Start-Process $exe -ArgumentList "install","--quiet","--accept-license" -Wait
    Remove-Item $exe
    Write-Host "Docker Desktop installed" -ForegroundColor Green
    $global:needsRestart = $true
}

# Networking fix
Write-Host "Disabling RSC (container networking fix)..." -ForegroundColor Yellow
Get-NetAdapterRsc | Disable-NetAdapterRsc -ErrorAction SilentlyContinue
$global:needsRestart = $true

# act installation
if (Get-Command act -ErrorAction SilentlyContinue) {
    Write-Host "act already installed, skipping" -ForegroundColor DarkGray
} else {
    Write-Host "Installing act..." -ForegroundColor Yellow
    $zip = "$env:TEMP\act.zip"
    Invoke-WebRequest "https://github.com/nektos/act/releases/latest/download/act_Windows_x86_64.zip" -OutFile $zip
    Expand-Archive $zip "$env:ProgramFiles\act" -Force
    [Environment]::SetEnvironmentVariable(
        "Path",
        "$env:ProgramFiles\act;" + [Environment]::GetEnvironmentVariable("Path","Machine"),
        "Machine"
    )
    Remove-Item $zip
    Write-Host "act installed" -ForegroundColor Green
}

# Git configuration
git config --global core.autocrlf false 2>$null
git config --global core.longpaths true 2>$null

# Completion message
Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green

if ($global:needsRestart) {
    Write-Host "*** RESTART YOUR COMPUTER ***" -ForegroundColor Red
    Write-Host "After restart, start Docker Desktop manually." -ForegroundColor Yellow
} else {
    Write-Host "Restart this terminal, then run:" -ForegroundColor Yellow
    Write-Host " gh auth login" -ForegroundColor Cyan
    Write-Host " win-claude-code" -ForegroundColor Cyan
}
