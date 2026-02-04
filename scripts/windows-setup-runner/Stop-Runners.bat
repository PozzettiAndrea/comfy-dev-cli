@echo off
echo Stopping GitHub Runners...

echo Stopping Windows runner...
taskkill /FI "WINDOWTITLE eq Windows GitHub Runner*" 2>nul

echo Stopping Linux runner...
wsl -d Ubuntu -e bash -c "pkill -f 'Runner.Listener' 2>/dev/null"

echo.
echo Runners stopped.
pause
