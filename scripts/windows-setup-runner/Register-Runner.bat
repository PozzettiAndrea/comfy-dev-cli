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
for /f "tokens=*" %%i in ('gh api repos/%REPO%/actions/runners/registration-token --jq .token') do set TOKEN=%%i

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

echo Starting Windows runner...
start "Windows GitHub Runner" cmd /c "%USERPROFILE%\github-runners\windows\run.cmd"

echo Starting Linux runner (WSL2)...
start "Linux GitHub Runner" wsl -d Ubuntu -e bash -c "cd ~/github-runners/linux && ./run.sh"

echo.
echo ============================================
echo   Both runners are now running!
echo ============================================
echo.
echo Windows runner: windows-gpu (labels: self-hosted, Windows, X64, gpu)
echo Linux runner:   linux-gpu-docker (labels: self-hosted, Linux, X64, gpu, docker)
echo.
echo Press any key to exit (runners will keep running)...
pause >nul
