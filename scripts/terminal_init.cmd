@echo off
:: Refresh user environment variables from registry (live, not stale)
:: Use 'call set' to expand REG_EXPAND_SZ values (e.g. %USERPROFILE% in TEMP)
for /f "tokens=1,2,* delims= " %%a in ('reg query "HKCU\Environment" 2^>nul ^| findstr /r "^    "') do (
    call set "%%a=%%c"
)
:: Ensure tools are on PATH
set "PATH=%USERPROFILE%\.local\bin;C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI;%PATH%"
:: Clear Claude Code env var to allow nested sessions
set "CLAUDECODE="
:: Fall back to server root if no cwd was set by JupyterLab
if "%CD%"=="%USERPROFILE%" D: && cd \
