@echo off
setlocal enabledelayedexpansion

:: Create log directory and set log file path
set "LOGDIR=%USERPROFILE%\Desktop\runner_logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
for /f %%i in ('powershell -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TIMESTAMP=%%i"
set "LOGFILE=%LOGDIR%\register_%TIMESTAMP%.log"

echo Logging to: %LOGFILE%
echo.

:: Log header
echo ============================================ > "%LOGFILE%"
echo   GitHub Runner Registration - %date% %time% >> "%LOGFILE%"
echo ============================================ >> "%LOGFILE%"

echo ============================================
echo   GitHub Runner Registration
echo ============================================
echo.

set /p REPO="Enter repo (owner/repo): "
echo Repo: %REPO% >> "%LOGFILE%"

if "%REPO%"=="" (
    echo Error: No repo provided
    echo Error: No repo provided >> "%LOGFILE%"
    pause
    exit /b 1
)

echo.
echo Checking GitHub CLI authentication...
echo Checking GitHub CLI authentication... >> "%LOGFILE%"
gh auth status >nul 2>&1
if errorlevel 1 (
    echo You need to login first.
    gh auth login
)

echo.
echo Getting registration token for %REPO%...
echo Getting registration token... >> "%LOGFILE%"
for /f "tokens=*" %%i in ('gh api repos/%REPO%/actions/runners/registration-token -X POST --jq .token') do set TOKEN=%%i

if "%TOKEN%"=="" (
    echo Error: Could not get registration token. Check repo name and permissions.
    echo Error: Could not get registration token >> "%LOGFILE%"
    pause
    exit /b 1
)
echo Token obtained successfully >> "%LOGFILE%"

echo.
echo ============================================
echo   Registering Windows Runner
echo ============================================
echo. >> "%LOGFILE%"
echo === Registering Windows Runner === >> "%LOGFILE%"

:: Use C:\github-runners to avoid user profile permission issues
set "RUNNER_DIR=C:\github-runners\windows"
if not exist "%RUNNER_DIR%" (
    echo Creating runner directory and downloading...
    mkdir "%RUNNER_DIR%"
    curl.exe -fSL -o "%RUNNER_DIR%\runner.zip" "https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-win-x64-2.321.0.zip"
    powershell -Command "Expand-Archive -Path '%RUNNER_DIR%\runner.zip' -DestinationPath '%RUNNER_DIR%' -Force; Remove-Item '%RUNNER_DIR%\runner.zip'"
)
cd /d %RUNNER_DIR%

:: Remove existing config if present
if exist .runner (
    echo Removing existing Windows runner configuration...
    echo Removing existing config... >> "%LOGFILE%"
    call config.cmd remove --token %TOKEN% >> "%LOGFILE%" 2>&1
)

echo Configuring Windows runner as service...
echo Configuring Windows runner... >> "%LOGFILE%"
(echo Y & echo.) | call config.cmd --url https://github.com/%REPO% --token %TOKEN% --name windows-gpu --labels self-hosted,Windows,X64,gpu --runnergroup Default --work _work --replace >> "%LOGFILE%" 2>&1

echo.
echo ============================================
echo   Registering Linux Runner (WSL2)
echo ============================================
echo. >> "%LOGFILE%"
echo === Registering Linux Runner === >> "%LOGFILE%"

:: Check if Linux runner is set up, if not download it
echo Checking/downloading Linux runner...
wsl -d Ubuntu -e bash -c "test -f ~/github-runners/linux/config.sh || (echo 'Downloading Linux runner...' && mkdir -p ~/github-runners/linux && cd ~/github-runners/linux && curl -sL https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-linux-x64-2.321.0.tar.gz | tar xz)" >> "%LOGFILE%" 2>&1

:: Configure the Linux runner
echo Configuring Linux runner...
wsl -d Ubuntu -e bash -c "cd ~/github-runners/linux && ./config.sh remove --token %TOKEN% 2>/dev/null; printf 'Y\n\n' | ./config.sh --url https://github.com/%REPO% --token %TOKEN% --name linux-gpu-docker --labels self-hosted,Linux,X64,gpu,docker --runnergroup Default --work _work --replace" >> "%LOGFILE%" 2>&1

echo.
echo ============================================
echo   Starting Services
echo ============================================
echo. >> "%LOGFILE%"
echo === Starting Services === >> "%LOGFILE%"

:: Grant NETWORK SERVICE full access to runner directory
echo Granting NETWORK SERVICE permissions...
icacls "C:\github-runners" /grant "NETWORK SERVICE:(OI)(CI)F" /T >> "%LOGFILE%" 2>&1

echo Starting Windows runner service...
echo Starting Windows service... >> "%LOGFILE%"
powershell -Command "Get-Service -Name 'actions.runner.*' | Stop-Service -Force -ErrorAction SilentlyContinue" >> "%LOGFILE%" 2>&1
timeout /t 2 >nul
powershell -Command "Get-Service -Name 'actions.runner.*' | Start-Service" >> "%LOGFILE%" 2>&1

echo.
echo Installing Linux runner as systemd service...
echo Installing Linux runner as systemd service... >> "%LOGFILE%"
wsl -d Ubuntu -e bash -c "cd ~/github-runners/linux && sudo ./svc.sh uninstall 2>/dev/null; sudo ./svc.sh install %USERNAME% && sudo ./svc.sh start" >> "%LOGFILE%" 2>&1

echo.
echo ============================================
echo   Verifying Services
echo ============================================
echo. >> "%LOGFILE%"
echo === Service Status === >> "%LOGFILE%"

echo.
echo Windows runner service status:
powershell -Command "Get-Service -Name 'actions.runner.*' | Format-Table -Property Name, Status -AutoSize" | powershell -Command "$input | Tee-Object -FilePath '%LOGFILE%' -Append"

echo.
echo Linux runner service status:
wsl -d Ubuntu -e bash -c "sudo systemctl status actions.runner.*.service 2>/dev/null | head -5 || echo 'Service status unknown'" | powershell -Command "$input | Tee-Object -FilePath '%LOGFILE%' -Append"

echo.
echo ============================================
echo   Both runners installed as services!
echo ============================================
echo.
echo Windows runner: windows-gpu (Windows service, auto-starts on reboot)
echo Linux runner:   linux-gpu-docker (systemd service in WSL2, auto-starts)
echo.
echo Log saved to: %LOGFILE%
echo.
echo === Complete === >> "%LOGFILE%"

pause