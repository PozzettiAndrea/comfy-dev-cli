# =============================================================================
# 03-GITHUB-RUNNERS.PS1
# Downloads GitHub runners, creates cleanup script and desktop shortcuts
# =============================================================================

param(
    [string]$SetupDir = "$env:USERPROFILE\.comfy-dev-setup"
)

$ErrorActionPreference = "Stop"

# ============================================================================
# RUNNER DIRECTORIES
# Create folders for Windows and Linux runners
# ============================================================================
$runnerBaseDir = "$env:USERPROFILE\github-runners"
$windowsRunnerDir = "$runnerBaseDir\windows"

Write-Host "Creating runner directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $windowsRunnerDir | Out-Null
Write-Host "Runner directories created at $runnerBaseDir" -ForegroundColor Green

# ============================================================================
# WINDOWS RUNNER
# Download GitHub Actions runner for Windows
# ============================================================================
$windowsRunnerExe = "$windowsRunnerDir\run.cmd"
if (Test-Path $windowsRunnerExe) {
    Write-Host "Windows GitHub Runner already downloaded" -ForegroundColor DarkGray
} else {
    Write-Host "Downloading Windows GitHub Runner..." -ForegroundColor Yellow
    $runnerVersion = "2.321.0"
    $runnerUrl = "https://github.com/actions/runner/releases/download/v$runnerVersion/actions-runner-win-x64-$runnerVersion.zip"
    $runnerZip = "$env:TEMP\actions-runner-win.zip"
    $maxRetries = 3
    for ($i = 1; $i -le $maxRetries; $i++) {
        try {
            # curl.exe is much faster than Invoke-WebRequest for large downloads
            $curlExit = (Start-Process -FilePath "curl.exe" -ArgumentList "-fSL", "-o", $runnerZip, $runnerUrl -NoNewWindow -Wait -PassThru).ExitCode
            if ($curlExit -ne 0) { throw "curl.exe exited with code $curlExit" }
            break
        } catch {
            if ($i -eq $maxRetries) {
                Write-Host "ERROR: Failed to download GitHub Runner after $maxRetries attempts." -ForegroundColor Red
                Write-Host "  Check your network connection and try again." -ForegroundColor Yellow
                throw
            }
            Write-Host "  Download attempt $i failed, retrying in 5 seconds..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        }
    }
    Expand-Archive $runnerZip $windowsRunnerDir -Force
    Remove-Item $runnerZip
    Write-Host "Windows GitHub Runner downloaded" -ForegroundColor Green
}

# ============================================================================
# WINDOWS RUNNER CLEANUP SCRIPT
# Runs between jobs to reset environment
# ============================================================================
$cleanupScript = @'
@echo off
echo === GitHub Runner Cleanup ===

echo Killing stray processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM python3.exe 2>nul
taskkill /F /IM node.exe 2>nul
taskkill /F /IM npm.exe 2>nul
taskkill /F /IM conda.exe 2>nul

echo Clearing temp directory...
del /q /s %TEMP%\* 2>nul
rd /s /q %TEMP%\pip-* 2>nul
rd /s /q %TEMP%\npm-* 2>nul

echo Clearing conda caches...
if exist %USERPROFILE%\miniconda3\condabin\conda.bat (
    call %USERPROFILE%\miniconda3\condabin\conda.bat clean --all -y 2>nul
)

echo Removing leftover containers...
for /f "tokens=*" %%i in ('docker ps -aq 2^>nul') do docker rm -f %%i 2>nul
docker system prune -f 2>nul

echo Resetting GPU state...
nvidia-smi --gpu-reset 2>nul

echo Cleanup complete.
'@
$cleanupScript | Out-File -FilePath "$windowsRunnerDir\cleanup.cmd" -Encoding ASCII
Write-Host "Windows runner cleanup script created" -ForegroundColor Green

# ============================================================================
# COPY WSL SETUP SCRIPT
# Move to runner directory so it's accessible from Ubuntu
# ============================================================================
Copy-Item "$SetupDir\04-wsl-setup.sh" "$runnerBaseDir\04-wsl-setup.sh" -Force
Write-Host "WSL setup script copied to $runnerBaseDir" -ForegroundColor Green

# ============================================================================
# WSL KEEPALIVE
# Prevent WSL2 from auto-shutting down when no interactive sessions are open
# ============================================================================
$keepaliveTask = Get-ScheduledTask -TaskName "WSL-Keepalive" -ErrorAction SilentlyContinue
if ($keepaliveTask) {
    Write-Host "WSL-Keepalive scheduled task already exists" -ForegroundColor DarkGray
} else {
    Write-Host "Creating WSL-Keepalive scheduled task..." -ForegroundColor Yellow
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "-d Ubuntu -- sleep infinity"
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0 -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName "WSL-Keepalive" -Trigger $trigger -Action $action -Principal $principal -Settings $settings -Force | Out-Null
    Write-Host "WSL-Keepalive task created (runs at startup)" -ForegroundColor Green
}

# Start keepalive now if not already running
$wslSleep = Get-Process -Name wsl -ErrorAction SilentlyContinue
if (-not $wslSleep) {
    Write-Host "Starting WSL keepalive process..." -ForegroundColor Yellow
    Start-Process -WindowStyle Hidden wsl -ArgumentList "-d","Ubuntu","--","sleep","infinity"
    Write-Host "WSL keepalive started" -ForegroundColor Green
}

# ============================================================================
# REGISTER-RUNNER BATCH SCRIPT
# Desktop shortcut to register both runners for any repo
# ============================================================================
$registerScript = @'
@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   GitHub Runner Registration
echo ============================================
echo.

set /p REPO="Enter repo (owner/repo): "

if "%REPO%"=="" (
    echo Error: No repo provided
    pause
    exit /b 1
)

echo.
echo Checking GitHub CLI authentication...
gh auth status >nul 2>&1
if errorlevel 1 (
    echo You need to login first.
    gh auth login
)

echo.
echo Getting registration token for %REPO%...
for /f "tokens=*" %%i in ('gh api repos/%REPO%/actions/runners/registration-token -X POST --jq .token') do set TOKEN=%%i

if "%TOKEN%"=="" (
    echo Error: Could not get registration token. Check repo name and permissions.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Registering Windows Runner
echo ============================================
cd /d %USERPROFILE%\github-runners\windows

:: Remove existing config if present
if exist .runner (
    echo Removing existing Windows runner configuration...
    call config.cmd remove --token %TOKEN% 2>nul
)

call config.cmd --url https://github.com/%REPO% --token %TOKEN% --name windows-gpu --labels self-hosted,Windows,X64,gpu --runnergroup Default --work _work --replace

echo.
echo ============================================
echo   Registering Linux Runner (WSL2)
echo ============================================
wsl -d Ubuntu -e bash -c "cd ~/github-runners/linux && ./config.sh remove --token %TOKEN% 2>/dev/null; ./config.sh --url https://github.com/%REPO% --token %TOKEN% --name linux-gpu-docker --labels self-hosted,Linux,X64,gpu,docker --runnergroup Default --work _work --replace"

echo.
echo ============================================
echo   Starting Runners
echo ============================================

:: Derive service name: replace / with - in repo name
set "SVC_REPO=%REPO:/=-%"
set "WIN_SVC=actions.runner.%SVC_REPO%.windows-gpu"

echo Installing Windows runner as a Windows service...
cd /d %USERPROFILE%\github-runners\windows
sc.exe stop "%WIN_SVC%" >nul 2>&1
sc.exe delete "%WIN_SVC%" >nul 2>&1
sc.exe create "%WIN_SVC%" binPath= "\"%USERPROFILE%\github-runners\windows\bin\RunnerService.exe\"" start= delayed-auto obj= "NT AUTHORITY\NETWORK SERVICE" DisplayName= "GitHub Actions Runner (%SVC_REPO%.windows-gpu)"
sc.exe start "%WIN_SVC%"
echo Windows runner service installed and started.

echo.
echo Installing Linux runner as systemd service...
wsl -d Ubuntu -e bash -c "cd ~/github-runners/linux && sudo ./svc.sh uninstall 2>/dev/null; sudo ./svc.sh install %USERNAME% && sudo ./svc.sh start"

echo.
echo ============================================
echo   Both runners are now running as services!
echo ============================================
echo.
echo Windows runner: windows-gpu (Windows service: %WIN_SVC%)
echo Linux runner:   linux-gpu-docker (systemd service in WSL2)
echo.
echo Both runners will auto-start on reboot.
echo.
echo Press any key to exit...
pause >nul
'@

$desktopPath = [Environment]::GetFolderPath("Desktop")
$registerScript | Out-File -FilePath "$desktopPath\Register-Runner.bat" -Encoding ASCII
Write-Host "Register-Runner.bat created on Desktop" -ForegroundColor Green

# ============================================================================
# STOP-RUNNERS BATCH SCRIPT
# Desktop shortcut to stop both runners gracefully
# ============================================================================
$stopScript = @'
@echo off
echo Stopping GitHub Runners...

echo Stopping Windows runner service...
for /f "tokens=*" %%s in ('powershell -Command "(Get-Service -Name 'actions.runner.*' -ErrorAction SilentlyContinue).Name"') do (
    echo   Stopping %%s...
    sc.exe stop "%%s" >nul 2>&1
)

echo Stopping Linux runner service...
wsl -d Ubuntu -e bash -c "cd ~/github-runners/linux && sudo ./svc.sh stop 2>/dev/null"

echo.
echo Runners stopped.
pause
'@
$stopScript | Out-File -FilePath "$desktopPath\Stop-Runners.bat" -Encoding ASCII
Write-Host "Stop-Runners.bat created on Desktop" -ForegroundColor Green

Write-Host "GitHub runners setup complete" -ForegroundColor Green
