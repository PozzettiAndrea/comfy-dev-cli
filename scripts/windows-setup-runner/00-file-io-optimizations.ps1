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
# SERVICES - Disable background I/O-heavy services (not useful in VMs)
# ============================================================================
$servicesToDisable = @(
    @{ Name = "WSearch";   Desc = "Windows Search Indexer" },
    @{ Name = "SysMain";   Desc = "Superfetch/Prefetch" },
    @{ Name = "DiagTrack"; Desc = "Telemetry" }
)
foreach ($svc in $servicesToDisable) {
    $s = Get-Service -Name $svc.Name -ErrorAction SilentlyContinue
    if ($s -and ($s.StartType -ne "Disabled")) {
        Write-Host "Disabling $($svc.Desc) ($($svc.Name))..." -ForegroundColor Yellow
        Stop-Service -Name $svc.Name -Force -ErrorAction SilentlyContinue
        Set-Service -Name $svc.Name -StartupType Disabled
        Write-Host "$($svc.Name) disabled" -ForegroundColor Green
    } else {
        Write-Host "$($svc.Name) already disabled" -ForegroundColor DarkGray
    }
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

# ============================================================================
# NTFS - Increase MFT zone (400MB reservation for many small files)
# ============================================================================
$currentMftZone = fsutil behavior query mftzone
if ($currentMftZone -notmatch "MftZone = 2") {
    Write-Host "Setting MFT zone to 2 (400MB)..." -ForegroundColor Yellow
    fsutil behavior set mftzone 2
    Write-Host "MFT zone set" -ForegroundColor Green
} else {
    Write-Host "MFT zone already at 2" -ForegroundColor DarkGray
}

# ============================================================================
# SCHEDULED DEFRAG - Disable (pointless for VM disks)
# ============================================================================
$defragTask = Get-ScheduledTask -TaskName "ScheduledDefrag" -TaskPath "\Microsoft\Windows\Defrag\" -ErrorAction SilentlyContinue
if ($defragTask -and $defragTask.State -ne "Disabled") {
    Write-Host "Disabling scheduled defrag..." -ForegroundColor Yellow
    Disable-ScheduledTask -TaskName "ScheduledDefrag" -TaskPath "\Microsoft\Windows\Defrag\" | Out-Null
    Write-Host "Scheduled defrag disabled" -ForegroundColor Green
} else {
    Write-Host "Scheduled defrag already disabled" -ForegroundColor DarkGray
}

# ============================================================================
# MEMORY MANAGEMENT - Optimize for file server workloads
# ============================================================================
$memMgmtPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
$largeCache = (Get-ItemProperty -Path $memMgmtPath -Name "LargeSystemCache" -ErrorAction SilentlyContinue).LargeSystemCache
$noPaging = (Get-ItemProperty -Path $memMgmtPath -Name "DisablePagingExecutive" -ErrorAction SilentlyContinue).DisablePagingExecutive

if ($largeCache -ne 1) {
    Write-Host "Enabling LargeSystemCache..." -ForegroundColor Yellow
    Set-ItemProperty -Path $memMgmtPath -Name "LargeSystemCache" -Value 1
    Write-Host "LargeSystemCache enabled" -ForegroundColor Green
} else {
    Write-Host "LargeSystemCache already enabled" -ForegroundColor DarkGray
}

if ($noPaging -ne 1) {
    Write-Host "Enabling DisablePagingExecutive (keep kernel in RAM)..." -ForegroundColor Yellow
    Set-ItemProperty -Path $memMgmtPath -Name "DisablePagingExecutive" -Value 1
    Write-Host "DisablePagingExecutive enabled" -ForegroundColor Green
} else {
    Write-Host "DisablePagingExecutive already enabled" -ForegroundColor DarkGray
}

# ============================================================================
# LONG PATHS - Enable paths longer than 260 characters
# ============================================================================
$fsPath = "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem"
$longPaths = (Get-ItemProperty -Path $fsPath -Name "LongPathsEnabled" -ErrorAction SilentlyContinue).LongPathsEnabled
if ($longPaths -ne 1) {
    Write-Host "Enabling long path support..." -ForegroundColor Yellow
    Set-ItemProperty -Path $fsPath -Name "LongPathsEnabled" -Value 1
    Write-Host "Long paths enabled" -ForegroundColor Green
} else {
    Write-Host "Long paths already enabled" -ForegroundColor DarkGray
}

Write-Host "File I/O optimizations complete" -ForegroundColor Green
