# ==============================================================================
# LANDSLIDENEI - Windows Standalone Installer Builder (Phase 8N)
# ==============================================================================
# Packages dist/LANDSLIDENEI into installer/LANDSLIDENEI_Setup_x64.exe
# using 7-Zip LZMA2 ultra-compressed self-extracting archive with shortcut hooks.
# ==============================================================================

param(
    [string]$DistDir = "$PSScriptRoot\..\dist\LANDSLIDENEI",
    [string]$OutputDir = "$PSScriptRoot\..\installer",
    [string]$InstallerName = "LANDSLIDENEI_Setup_x64.exe"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " LANDSLIDENEI - WINDOWS INSTALLER PACKAGER" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Verify Prerequisites
$SevenZipExe = "C:\Program Files\7-Zip\7z.exe"
$SevenZipSfx = "C:\Program Files\7-Zip\7z.sfx"

if (-not (Test-Path $SevenZipExe)) {
    throw "7-Zip executable not found at: $SevenZipExe"
}
if (-not (Test-Path $SevenZipSfx)) {
    throw "7-Zip SFX module not found at: $SevenZipSfx"
}

$ExePath = Join-Path $DistDir "LANDSLIDENEI.exe"
if (-not (Test-Path $ExePath)) {
    throw "Target application executable not found at: $ExePath. Run scripts/build_desktop_app.py first."
}

# 2. Ensure Output Directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}
$InstallerPath = Join-Path $OutputDir $InstallerName

# 3. Create Shortcut Generator Helpers inside dist directory
$VbsShortcutPath = Join-Path $DistDir "Create_Desktop_Shortcut.vbs"
$VbsContent = @"
' LANDSLIDENEI Windows Shortcut Creator
Set oWS = CreateObject("WScript.Shell")
sCurrentDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Desktop Shortcut
sDesktop = oWS.SpecialFolders("Desktop")
sDesktopLink = sDesktop & "\LANDSLIDENEI.lnk"
Set oLink = oWS.CreateShortcut(sDesktopLink)
oLink.TargetPath = sCurrentDir & "\LANDSLIDENEI.exe"
oLink.WorkingDirectory = sCurrentDir
oLink.Description = "LANDSLIDENEI - Regional Landslide Risk Intelligence Platform"
oLink.IconLocation = sCurrentDir & "\assets\icon.ico,0"
oLink.Save

' Start Menu Shortcut
sPrograms = oWS.SpecialFolders("Programs")
sMenuLink = sPrograms & "\LANDSLIDENEI.lnk"
Set oMenuLink = oWS.CreateShortcut(sMenuLink)
oMenuLink.TargetPath = sCurrentDir & "\LANDSLIDENEI.exe"
oMenuLink.WorkingDirectory = sCurrentDir
oMenuLink.Description = "LANDSLIDENEI - Regional Landslide Risk Intelligence Platform"
oMenuLink.IconLocation = sCurrentDir & "\assets\icon.ico,0"
oMenuLink.Save

WScript.Echo "LANDSLIDENEI shortcuts created successfully on Desktop and Start Menu!"
"@
Set-Content -Path $VbsShortcutPath -Value $VbsContent -Encoding ASCII

$BatShortcutPath = Join-Path $DistDir "Create_Shortcuts.bat"
$BatContent = @"
@echo off
title LANDSLIDENEI Shortcut Generator
cd /d "%~dp0"
cscript //nologo Create_Desktop_Shortcut.vbs
echo.
echo Press any key to finish...
pause >nul
"@
Set-Content -Path $BatShortcutPath -Value $BatContent -Encoding ASCII

Write-Host "`n[1/3] Added shortcut creation helpers to distribution directory..." -ForegroundColor Yellow

# 4. Build 7-Zip SFX Archive
if (Test-Path $InstallerPath) {
    Write-Host "  Removing existing installer: $InstallerPath" -ForegroundColor DarkGray
    Remove-Item -Path $InstallerPath -Force
}

Write-Host "`n[2/3] Compressing package into standalone SFX installer ($InstallerName)..." -ForegroundColor Yellow
$SfxArg = "-sfx$SevenZipSfx"
$SourceWildcard = "$DistDir\*"

& $SevenZipExe a $SfxArg -mx9 -mmt=on -y $InstallerPath $SourceWildcard | Out-Host

if (-not (Test-Path $InstallerPath)) {
    throw "Installer generation failed! Output file does not exist: $InstallerPath"
}

# 5. Integrity Verification & Metrics
Write-Host "`n[3/3] Verifying installer integrity..." -ForegroundColor Yellow
& $SevenZipExe t $InstallerPath | Out-Host

$HashObj = Get-FileHash -Path $InstallerPath -Algorithm SHA256
$SizeMb = (Get-Item $InstallerPath).Length / 1MB

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host " INSTALLER GENERATION SUCCESSFUL!" -ForegroundColor Green
Write-Host " Installer File : $InstallerPath" -ForegroundColor Green
Write-Host " File Size      : $([Math]::Round($SizeMb, 2)) MB" -ForegroundColor Green
Write-Host " SHA-256 Hash   : $($HashObj.Hash)" -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Green
