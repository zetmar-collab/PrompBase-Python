# Paczka ZIP: PrompBase Premium Prompty (250 promptow + instrukcja)
# Uruchom: powershell -ExecutionPolicy Bypass -File scripts\build_premium_zip.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Version = "2.6"
$match = Select-String -Path (Join-Path $Root "promptbase.py") -Pattern 'APP_VERSION = "([^"]+)"' | Select-Object -First 1
if ($match) { $Version = $match.Matches.Groups[1].Value }

Write-Host "Budowa paczki premium promptow v$Version"

Write-Host "Generowanie JSON z zrodel..."
python (Join-Path $Root "scripts\build_premium_pack.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$packageName = "PrompBase-Premium-Prompty-v$Version"
$packageDir = Join-Path $Root "dist\$packageName"
if (Test-Path $packageDir) {
    Remove-Item -Recurse -Force $packageDir
}
New-Item -ItemType Directory -Path $packageDir | Out-Null

$promptyDir = Join-Path $Root "Prompty"
$files = @(
    @{ Src = "INSTRUKCJA-IMPORT.txt"; Dst = "INSTRUKCJA-IMPORT.txt" },
    @{ Src = "premium-prompbase-v2.6.json"; Dst = "premium-prompbase-v2.6.json" },
    @{ Src = "premium-promptLibrary-pwa.json"; Dst = "premium-promptLibrary-pwa.json" }
)

foreach ($f in $files) {
    $src = Join-Path $promptyDir $f.Src
    if (-not (Test-Path $src)) {
        Write-Host "Brak pliku: $($f.Src)" -ForegroundColor Red
        exit 1
    }
    Copy-Item $src (Join-Path $packageDir $f.Dst)
    Write-Host "  + $($f.Dst)"
}

$zipPath = Join-Path $Root "dist\$packageName.zip"
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
Compress-Archive -Path (Join-Path $packageDir "*") -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host ""
Write-Host "Gotowe:"
Write-Host "  Folder: $packageDir"
Write-Host "  ZIP:    $zipPath"
