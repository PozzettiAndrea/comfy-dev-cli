# =============================================================================
# COMFY-DEV-CLI WINDOWS SETUP
# Launched by bootstrap.ps1 -- do not run via irm | iex directly.
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
        curl.exe -fSL -o "$setupDir\$script" "$baseUrl/$script"
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
# REBOOT CHECKPOINT -- if Phase 1 set the reboot flag, reboot now so that
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
# PHASE 4: WSL Ubuntu Setup
# Initialize Ubuntu non-interactively and run the WSL setup script
# =============================================================================
if (Test-PhaseComplete 4) {
    Write-Host "=== Phase 4: WSL Ubuntu Setup === (already done, skipping)" -ForegroundColor DarkGray
} else {
    Write-Host ""
    Write-Host "=== Phase 4: WSL Ubuntu Setup ===" -ForegroundColor Cyan

    # Initialize Ubuntu with a default user (bypasses the interactive first-launch prompt)
    Write-Host "Initializing Ubuntu default user..." -ForegroundColor Yellow
    wsl -d Ubuntu -u root -- bash -c "
        if ! id runner &>/dev/null; then
            useradd -m -s /bin/bash runner
            echo 'runner:runner' | chpasswd
            usermod -aG sudo runner
        fi
        echo 'runner ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/runner
        chmod 440 /etc/sudoers.d/runner
        # Set runner as the default login user
        printf '[user]\ndefault=runner\n' > /etc/wsl.conf
    "
    # Restart Ubuntu so wsl.conf takes effect
    wsl --terminate Ubuntu
    Start-Sleep -Seconds 2
    Write-Host "Ubuntu user 'runner' created" -ForegroundColor Green

    # Run the WSL setup script (Docker, NVIDIA toolkit, Linux runner)
    Write-Host "Running WSL setup script..." -ForegroundColor Yellow
    $wslSetupScript = "/mnt/c/Users/$env:USERNAME/github-runners/04-wsl-setup.sh"
    wsl -d Ubuntu -- bash $wslSetupScript
    Write-Host "WSL Ubuntu setup complete" -ForegroundColor Green
    Save-PhaseComplete 4
}

# =============================================================================
# PHASE 5: GitHub Auth & Runner Registration
# Authenticate with GitHub and register both runners
# =============================================================================
if (Test-PhaseComplete 5) {
    Write-Host "=== Phase 5: Runner Registration === (already done, skipping)" -ForegroundColor DarkGray
} else {
    Write-Host ""
    Write-Host "=== Phase 5: Runner Registration ===" -ForegroundColor Cyan

    # Ensure gh is on PATH
    $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")

    # Authenticate if needed
    $ghAuth = gh auth status 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "GitHub CLI not authenticated. Launching login..." -ForegroundColor Yellow
        gh auth login
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: GitHub authentication failed. Run 'gh auth login' manually, then re-run setup." -ForegroundColor Red
            throw "GitHub authentication failed"
        }
    } else {
        Write-Host "GitHub CLI already authenticated" -ForegroundColor DarkGray
    }

    # Prompt for repo
    Write-Host ""
    $repo = Read-Host "Enter repo to register runners for (owner/repo)"
    if ([string]::IsNullOrWhiteSpace($repo)) {
        Write-Host "No repo provided -- skipping runner registration." -ForegroundColor Yellow
        Write-Host "You can register later by running Register-Runner.bat on the Desktop." -ForegroundColor Yellow
    } else {
        Write-Host "Getting registration token for $repo..." -ForegroundColor Yellow
        $token = gh api "repos/$repo/actions/runners/registration-token" -X POST --jq '.token' 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Could not get registration token. Check repo name and permissions." -ForegroundColor Red
            throw "Failed to get registration token"
        }

        # --- Windows runner ---
        Write-Host ""
        Write-Host "Registering Windows runner..." -ForegroundColor Yellow
        $winRunnerDir = "C:\github-runners\windows"
        if (-not (Test-Path $winRunnerDir)) {
            New-Item -ItemType Directory -Force -Path $winRunnerDir | Out-Null
            $runnerVersion = "2.321.0"
            $runnerZip = "$env:TEMP\actions-runner-win.zip"
            curl.exe -fSL -o $runnerZip "https://github.com/actions/runner/releases/download/v$runnerVersion/actions-runner-win-x64-$runnerVersion.zip"
            Expand-Archive $runnerZip $winRunnerDir -Force
            Remove-Item $runnerZip
        }

        Push-Location $winRunnerDir
        try {
            # Remove existing config if present
            if (Test-Path ".runner") {
                Write-Host "  Removing existing configuration..." -ForegroundColor DarkGray
                & .\config.cmd remove --token $token 2>$null
            }
            # Configure (pipe Y + blank line for replace/group prompts)
            Write-Output "Y`n" | & .\config.cmd --url "https://github.com/$repo" --token $token --name windows-gpu --labels self-hosted,Windows,X64,gpu --runnergroup Default --work _work --replace
            Write-Host "Windows runner configured" -ForegroundColor Green

            # Install as Windows service
            $svcRepo = $repo -replace "/", "-"
            $svcName = "actions.runner.$svcRepo.windows-gpu"
            sc.exe stop $svcName 2>$null
            sc.exe delete $svcName 2>$null
            & .\bin\RunnerService.exe install 2>$null
            # Grant NETWORK SERVICE access
            icacls "C:\github-runners" /grant "NETWORK SERVICE:(OI)(CI)F" /T /Q 2>$null
            sc.exe start $svcName 2>$null
            Write-Host "Windows runner service started" -ForegroundColor Green
        } finally {
            Pop-Location
        }

        # --- Linux runner ---
        Write-Host ""
        Write-Host "Registering Linux runner..." -ForegroundColor Yellow
        wsl -d Ubuntu -- bash -c "cd ~/github-runners/linux `&`& ./config.sh remove --token $token 2>/dev/null; printf 'Y\n\n' | ./config.sh --url https://github.com/$repo --token $token --name linux-gpu-docker --labels self-hosted,Linux,X64,gpu,docker --runnergroup Default --work _work --replace"
        Write-Host "Linux runner configured" -ForegroundColor Green

        # Install Linux runner as systemd service
        wsl -d Ubuntu -- bash -c "cd ~/github-runners/linux `&`& sudo ./svc.sh uninstall 2>/dev/null; sudo ./svc.sh install runner `&`& sudo ./svc.sh start"
        Write-Host "Linux runner service started" -ForegroundColor Green
    }

    Save-PhaseComplete 5
}

# =============================================================================
# DONE
# =============================================================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Clean up progress file -- setup is fully done
Remove-Item $progressFile -ErrorAction SilentlyContinue
Remove-Item "$setupDir\.reboot-needed" -ErrorAction SilentlyContinue

} finally {
    # =============================================================================
    # STOP LOGGING -- always runs, even on error or before reboot
    # =============================================================================
    try { Stop-Transcript } catch {}
}

Write-Host "Setup log saved to: $logFile" -ForegroundColor Cyan
