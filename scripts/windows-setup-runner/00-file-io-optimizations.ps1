# =============================================================================
# 00-FILE-IO-OPTIMIZATIONS.PS1
# Optimizes Windows for fast file I/O before dev tools installation
# =============================================================================

$ErrorActionPreference = "Stop"

# ============================================================================
# POWER PLAN - High Performance
# ============================================================================
$currentPlan = powercfg /getactivescheme
if ($currentPlan -notmatch "High performance") {
    Write-Host "Setting power plan to High Performance..." -ForegroundColor Yellow
    powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
    Write-Host "Power plan set" -ForegroundColor Green
} else {
    Write-Host "Power plan already High Performance" -ForegroundColor DarkGray
}

# ============================================================================
# WINDOWS DEFENDER - Check and warn
# ============================================================================
$defender = Get-MpComputerStatus -ErrorAction SilentlyContinue
if ($defender -and $defender.RealTimeProtectionEnabled) {
    Write-Host "WARNING: Windows Defender Real-Time Protection is ENABLED" -ForegroundColor Red
    Write-Host "  This slows file operations. Disable via Windows Security settings." -ForegroundColor Yellow
} else {
    Write-Host "Windows Defender Real-Time Protection disabled" -ForegroundColor DarkGray
}

# ============================================================================
# NTFS - Disable 8.3 short names (speeds up file creation)
# ============================================================================
$current8dot3 = fsutil behavior query disable8dot3
if ($current8dot3 -match "disable8dot3 = 0") {
    Write-Host "Disabling 8.3 short name creation..." -ForegroundColor Yellow
    fsutil behavior set disable8dot3 1
    Write-Host "8.3 names disabled" -ForegroundColor Green
} else {
    Write-Host "8.3 short names already disabled" -ForegroundColor DarkGray
}

# ============================================================================
# NTFS - Disable last access time updates (speeds up reads)
# ============================================================================
$currentLastAccess = fsutil behavior query disablelastaccess
if ($currentLastAccess -match "DisableLastAccess = 0") {
    Write-Host "Disabling last access time updates..." -ForegroundColor Yellow
    fsutil behavior set disablelastaccess 1
    Write-Host "Last access time disabled" -ForegroundColor Green
} else {
    Write-Host "Last access time already disabled" -ForegroundColor DarkGray
}

# ============================================================================
# NTFS - Increase memory usage for file system cache
# ============================================================================
$currentMemory = fsutil behavior query memoryusage
if ($currentMemory -notmatch "MemoryUsage = 2") {
    Write-Host "Setting NTFS memory usage to maximum..." -ForegroundColor Yellow
    fsutil behavior set memoryusage 2
    Write-Host "NTFS memory usage set" -ForegroundColor Green
} else {
    Write-Host "NTFS memory usage already at maximum" -ForegroundColor DarkGray
}

Write-Host "File I/O optimizations complete" -ForegroundColor Green
