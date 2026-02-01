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
