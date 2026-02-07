# =============================================================================
# COMFY-DEV-CLI WINDOWS SETUP
# Launched by bootstrap.ps1 — do not run via irm | iex directly.
# One-liner: irm https://raw.githubusercontent.com/PozzettiAndrea/comfy-dev-cli/main/scripts/windows-setup-runner/bootstrap.ps1 | iex
# =============================================================================

$ErrorActionPreference = "Stop"
$setupDir = "$env:USERPROFILE\.comfy-dev-setup"
$progressFile = "$setupDir\progress.json"

# =============================================================================
# PROGRESS TRACKING
# Tracks completed phases so the script can resume after a reboot.
# =============================================================================
function Get-CompletedPhases {
    if (Test-Path $progressFile) {
        $progress = Get-Content $progressFile -Raw | ConvertFrom-Json
        return @($progress.completedPhases)
    }
    return @()
}

function Save-PhaseComplete([int]$phase) {
    $completed = @(Get-CompletedPhases)
    if ($phase -notin $completed) {
        $completed += $phase
    }
    @{ completedPhases = $completed } | ConvertTo-Json | Set-Content $progressFile
}

function Test-PhaseComplete([int]$phase) {
    return $phase -in @(Get-CompletedPhases)
}

# =============================================================================
# LOGGING - Capture all output to setup.log on Desktop
# =============================================================================
$desktopPath = [Environment]::GetFolderPath("Desktop")
$logFile = "$desktopPath\setup.log"
try {
    Start-Transcript -Path $logFile -Append
} catch {
    Write-Host "WARNING: Could not start transcript logging to $logFile" -ForegroundColor Yellow
    Write-Host "  Error: $_" -ForegroundColor Yellow
    Write-Host "  Setup will continue without file logging." -ForegroundColor Yellow
}

try {

Write-Host "=== Comfy Dev CLI - Windows Setup ===" -ForegroundColor Cyan

# Ensure setup directory exists (bootstrap.ps1 creates it, but handle direct runs)
New-Item -ItemType Directory -Force -Path $setupDir | Out-Null

# Clear previous reboot flag (allows clean re-runs)
Remove-Item "$setupDir\.reboot-needed" -ErrorAction SilentlyContinue

# If scripts aren't already downloaded (direct run without bootstrap), download them
if (-not (Test-Path "$setupDir\00-file-io-optimizations.ps1")) {
    $baseUrl = "https://raw.githubusercontent.com/PozzettiAndrea/comfy-dev-cli/main/scripts/windows-setup-runner"
    Write-Host "Downloading setup scripts..." -ForegroundColor Yellow
    $scripts = @(
        "00-file-io-optimizations.ps1",
        "01-windows-features.ps1",
        "02-dev-tools.ps1",
        "03-github-runners.ps1",
        "04-wsl-setup.sh",
        "Register-Runner.bat",
        "Stop-Runners.bat"
    )
    foreach ($script in $scripts) {
        Write-Host "  Downloading $script..." -ForegroundColor DarkGray
        Invoke-WebRequest -Uri "$baseUrl/$script" -OutFile "$setupDir\$script" -UseBasicParsing
    }
    Write-Host "Scripts downloaded to $setupDir" -ForegroundColor Green
}
Write-Host ""

# =============================================================================
# PHASE 0: File I/O Optimizations
# =============================================================================
if (Test-PhaseComplete 0) {
    Write-Host "=== Phase 0: File I/O Optimizations === (already done, skipping)" -ForegroundColor DarkGray
} else {
    Write-Host "=== Phase 0: File I/O Optimizations ===" -ForegroundColor Cyan
    & "$setupDir\00-file-io-optimizations.ps1"
    Save-PhaseComplete 0
}

# =============================================================================
# PHASE 1: Windows Features (may require reboot)
# =============================================================================
if (Test-PhaseComplete 1) {
    Write-Host "=== Phase 1: Windows Features === (already done, skipping)" -ForegroundColor DarkGray
} else {
    Write-Host ""
    Write-Host "=== Phase 1: Windows Features ===" -ForegroundColor Cyan
    & "$setupDir\01-windows-features.ps1"
    Save-PhaseComplete 1
}

# -------------------------------------------------------------------------
# REBOOT CHECKPOINT — if Phase 1 set the reboot flag, reboot now so that
# Hyper-V / WSL / Container networking is properly initialized before
# Phase 2 installs Docker and modifies the network stack.
# -------------------------------------------------------------------------
$rebootFlag = "$setupDir\.reboot-needed"
if ((Test-Path $rebootFlag) -and -not (Test-PhaseComplete 2)) {
    Write-Host ""
    Write-Host "*** Reboot required for Windows features to take effect ***" -ForegroundColor Red
    Write-Host "Setup will resume automatically after reboot." -ForegroundColor Yellow
    Write-Host ""

    # Register RunOnce to re-launch this script after reboot
    $runOnceKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce"
    $resumeCmd = "powershell.exe -ExecutionPolicy Bypass -File `"$setupDir\windows_setup.ps1`""
    Set-ItemProperty -Path $runOnceKey -Name "ComfyDevSetup" -Value $resumeCmd

    # Stop transcript before reboot so log is flushed
    try { Stop-Transcript } catch {}
    Write-Host "Rebooting in 10 seconds... (Ctrl+C to cancel)" -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    Restart-Computer -Force
    exit
}

# =============================================================================
# PHASE 2: Dev Tools (includes git clone of comfy-dev-cli)
# =============================================================================
if (Test-PhaseComplete 2) {
    Write-Host "=== Phase 2: Dev Tools === (already done, skipping)" -ForegroundColor DarkGray
} else {
    Write-Host ""
    Write-Host "=== Phase 2: Dev Tools ===" -ForegroundColor Cyan
    & "$setupDir\02-dev-tools.ps1"
    Save-PhaseComplete 2
}

# =============================================================================
# PHASE 3: GitHub Runners
# =============================================================================
if (Test-PhaseComplete 3) {
    Write-Host "=== Phase 3: GitHub Runners === (already done, skipping)" -ForegroundColor DarkGray
} else {
    Write-Host ""
    Write-Host "=== Phase 3: GitHub Runners ===" -ForegroundColor Cyan
    & "$setupDir\03-github-runners.ps1" -SetupDir $setupDir
    Save-PhaseComplete 3
}

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

# Clean up progress file — setup is fully done
Remove-Item $progressFile -ErrorAction SilentlyContinue
Remove-Item "$setupDir\.reboot-needed" -ErrorAction SilentlyContinue

} finally {
    # =============================================================================
    # STOP LOGGING — always runs, even on error or before reboot
    # =============================================================================
    try { Stop-Transcript } catch {}
}

Write-Host "Setup log saved to: $logFile" -ForegroundColor Cyan
