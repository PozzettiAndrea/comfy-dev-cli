@echo off
setlocal enabledelayedexpansion

:: =============================================================================
:: COMFY-DEV-CLI WINDOWS DEV SETUP
:: Equivalent of linux_setup.sh -- installs Claude, uv, cds CLI, gh, git id
:: =============================================================================

:: ================= ensure uv/tools on PATH =======
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

:: ================= Claude ====================
where claude >nul 2>&1
if errorlevel 1 (
  echo Installing Claude Code...
  npm install -g @anthropic-ai/claude-code
  if errorlevel 1 (
    echo WARNING: Claude install failed. Make sure Node.js/npm is installed.
  ) else (
    echo Claude Code installed
  )
) else (
  echo Claude Code already installed
)

:: ================= uv ========================
where uv >nul 2>&1
if errorlevel 1 (
  echo Installing uv...
  powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
  echo uv installed
) else (
  echo uv already installed
)

:: ================= paths =====================
set "SCRIPT_DIR=%~dp0"
:: Remove trailing backslash
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..") do set "PROJECT_ROOT=%%~fI"

:: ================= cds CLI (global) ==========
echo Installing cds CLI...
uv tool install --force --editable "%PROJECT_ROOT%\cli"
if errorlevel 1 (
  echo WARNING: cds CLI install failed
) else (
  :: Set CDS_ROOT as persistent user env var
  setx CDS_ROOT "%PROJECT_ROOT%" >nul 2>&1
  set "CDS_ROOT=%PROJECT_ROOT%"
  echo cds installed globally
)

:: ================= GitHub CLI =================
where gh >nul 2>&1
if errorlevel 1 (
  echo Installing GitHub CLI...
  winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements
  if errorlevel 1 (
    echo WARNING: gh install failed. Install manually from https://cli.github.com
  ) else (
    :: Refresh PATH
    for /f "tokens=*" %%i in ('powershell -Command "[Environment]::GetEnvironmentVariable('Path','Machine')"') do set "PATH=%%i;%PATH%"
    echo GitHub CLI installed
  )
) else (
  echo GitHub CLI already installed
)

:: ================= git identity ===============
set "IDENTITY_FILE=%PROJECT_ROOT%\private\identity.yml"
if exist "%IDENTITY_FILE%" (
  for /f "tokens=2 delims=: " %%a in ('findstr "email:" "%IDENTITY_FILE%"') do set "GIT_EMAIL=%%a"
  for /f "tokens=2 delims=: " %%a in ('findstr "github_owner:" "%IDENTITY_FILE%"') do set "GIT_NAME=%%a"
  git config --global user.email "!GIT_EMAIL!"
  git config --global user.name "!GIT_NAME!"
  echo Git identity set from private/identity.yml
) else (
  echo Note: Set git identity with: git config --global user.email/user.name
)

:: ================= gh auth ====================
gh auth status --hostname github.com >nul 2>&1
if errorlevel 1 (
  echo GitHub CLI not authenticated. Launching login...
  gh auth login --hostname github.com --git-protocol https
  if errorlevel 1 (
    echo WARNING: GitHub authentication failed. Run 'gh auth login' manually.
  ) else (
    echo GitHub authenticated
  )
) else (
  echo GitHub CLI already authenticated
)

:: ================= git credential helper ========
:: Use gh CLI as credential helper so git uses gh's stored credentials
git config --global credential.helper "!gh auth git-credential"
echo Git credential helper set to gh CLI

:: ================= done =======================
echo.
echo Setup complete
echo - cds available everywhere
echo - safe to re-run anytime
