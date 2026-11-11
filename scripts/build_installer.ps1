# Buduje instalator PrompBase-<wersja>-Setup.exe (Inno Setup).
# Wymaga: wcześniejszego uruchomienia scripts\build_windows.ps1
#         oraz zainstalowanego Inno Setup (ISCC.exe).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# Wersja z promptbase.py (spójna z build_windows.ps1).
$Version = "2.10.0"
$versionFile = Join-Path $Root "pbcore\core.py"
if (Test-Path $versionFile) {
    $match = Select-String -Path $versionFile -Pattern 'APP_VERSION = "([^"]+)"' | Select-Object -First 1
    if ($match) { $Version = $match.Matches.Groups[1].Value }
}

# Sprawdź, czy istnieje spakowany katalog z EXE.
$packageDir = Join-Path $Root "dist\PrompBase-$Version-Windows"
if (-not (Test-Path (Join-Path $packageDir "PrompBase.exe"))) {
    Write-Host "Brak $packageDir\PrompBase.exe."
    Write-Host "Uruchom najpierw: scripts\build_windows.ps1"
    exit 1
}

# Znajdź ISCC.exe (Inno Setup 6/7, w Program Files lub per-user).
$isccCandidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 7\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 7\ISCC.exe",
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 7\ISCC.exe")
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { $iscc = $cmd.Source }
}
if (-not $iscc) {
    Write-Host "Nie znaleziono ISCC.exe. Zainstaluj Inno Setup:"
    Write-Host "  winget install --id JRSoftware.InnoSetup -e"
    exit 1
}

Write-Host "Inno Setup: $iscc"
Write-Host "Budowanie instalatora PrompBase v$Version..."

$iss = Join-Path $Root "installer\PrompBase.iss"
& $iscc "/DAppVersion=$Version" $iss
if ($LASTEXITCODE -ne 0) {
    Write-Host "ISCC zwrocil blad ($LASTEXITCODE)."
    exit $LASTEXITCODE
}

$setup = Join-Path $Root "dist\PrompBase-$Version-Setup.exe"
if (Test-Path $setup) {
    Write-Host ""
    Write-Host "Gotowe:"
    Write-Host "  Instalator: $setup"
} else {
    Write-Host "Nie znaleziono $setup - sprawdz log ISCC."
    exit 1
}
