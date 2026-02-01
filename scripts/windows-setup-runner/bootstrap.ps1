# =============================================================================
# COMFY-DEV-CLI BOOTSTRAP
# One-liner: irm https://raw.githubusercontent.com/PozzettiAndrea/comfy-dev-cli/main/scripts/windows-setup-runner/bootstrap.ps1 | iex
#
# Downloads all setup scripts to a persistent directory, then launches
# windows_setup.ps1 as a proper script file. This ensures Start-Transcript
# captures all output reliably (unlike piped iex execution).
# =============================================================================

$ErrorActionPreference = "Stop"
$baseUrl = "https://raw.githubusercontent.com/PozzettiAndrea/comfy-dev-cli/main/scripts/windows-setup-runner"
$setupDir = "$env:USERPROFILE\.comfy-dev-setup"

# Create persistent setup directory (survives reboots, unlike $env:TEMP on some configs)
New-Item -ItemType Directory -Force -Path $setupDir | Out-Null

# Download all scripts
$scripts = @(
    "windows_setup.ps1",
    "00-file-io-optimizations.ps1",
    "01-windows-features.ps1",
    "02-dev-tools.ps1",
    "03-github-runners.ps1",
    "04-wsl-setup.sh",
    "Register-Runner.bat",
    "Stop-Runners.bat"
)

Write-Host "=== Comfy Dev CLI - Downloading Setup Scripts ===" -ForegroundColor Cyan
foreach ($script in $scripts) {
    Write-Host "  Downloading $script..." -ForegroundColor DarkGray
    curl.exe -fSL -o "$setupDir\$script" "$baseUrl/$script"
}
Write-Host "Scripts downloaded to $setupDir" -ForegroundColor Green
Write-Host ""

# Launch the main setup script as a file (not piped) for reliable transcript logging
powershell.exe -ExecutionPolicy Bypass -File "$setupDir\windows_setup.ps1"
