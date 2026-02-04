# =============================================================================
# COMFY-DEV-CLI WINDOWS SETUP
# One-liner: irm https://raw.githubusercontent.com/PozzettiAndrea/comfy-dev-cli/main/scripts/windows-runner-setup/windows_setup.ps1 | iex
# =============================================================================

$ErrorActionPreference = "Stop"
$baseUrl = "https://raw.githubusercontent.com/PozzettiAndrea/comfy-dev-cli/main/scripts/windows-runner-setup"
$setupDir = "$env:TEMP\comfy-dev-setup"

Write-Host "=== Comfy Dev CLI - Windows Setup ===" -ForegroundColor Cyan
Write-Host "Downloading setup scripts..." -ForegroundColor Yellow

# Create temp directory
New-Item -ItemType Directory -Force -Path $setupDir | Out-Null

# Download all scripts
$scripts = @(
    "01-windows-features.ps1",
    "02-dev-tools.ps1",
    "03-github-runners.ps1",
    "04-wsl-setup.sh",
    "Register-Runner.bat",
    "Stop-Runners.bat"
)

foreach ($script in $scripts) {
    Write-Host "  Downloading $script..." -ForegroundColor DarkGray
    Invoke-WebRequest -Uri "$baseUrl/$script" -OutFile "$setupDir\$script"
}

Write-Host "Scripts downloaded to $setupDir" -ForegroundColor Green
Write-Host ""

# =============================================================================
# PHASE 1: Windows Features (may require reboot)
# =============================================================================
Write-Host "=== Phase 1: Windows Features ===" -ForegroundColor Cyan
& "$setupDir\01-windows-features.ps1"

# Check if reboot is needed
$rebootFlag = "$setupDir\.reboot-needed"
if (Test-Path $rebootFlag) {
    Write-Host ""
    Write-Host "*** REBOOT REQUIRED ***" -ForegroundColor Red
    Write-Host ""
    Write-Host "After reboot, run this again:" -ForegroundColor Yellow
    Write-Host "  irm https://raw.githubusercontent.com/PozzettiAndrea/comfy-dev-cli/main/scripts/windows-runner-setup/windows_setup.ps1 | iex" -ForegroundColor Cyan
    Write-Host ""
    $restart = Read-Host "Restart now? (y/n)"
    if ($restart -eq "y") {
        Restart-Computer -Force
    }
    exit 0
}

# =============================================================================
# PHASE 2: Dev Tools
# =============================================================================
Write-Host ""
Write-Host "=== Phase 2: Dev Tools ===" -ForegroundColor Cyan
& "$setupDir\02-dev-tools.ps1"

# =============================================================================
# PHASE 3: GitHub Runners
# =============================================================================
Write-Host ""
Write-Host "=== Phase 3: GitHub Runners ===" -ForegroundColor Cyan
& "$setupDir\03-github-runners.ps1" -SetupDir $setupDir

# =============================================================================
# DONE
# =============================================================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Open Ubuntu from Start Menu (first-time setup)" -ForegroundColor Cyan
Write-Host "  2. In Ubuntu, run:" -ForegroundColor Cyan
Write-Host "     bash /mnt/c/Users/$env:USERNAME/github-runners/04-wsl-setup.sh" -ForegroundColor White
Write-Host "  3. Back in Windows, run: gh auth login" -ForegroundColor Cyan
Write-Host "  4. Double-click 'Register-Runner.bat' on Desktop" -ForegroundColor Cyan
Write-Host ""
