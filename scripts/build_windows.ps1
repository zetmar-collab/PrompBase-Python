# Buduje PrompBase.exe (PyInstaller) i paczke ZIP do dystrybucji.
# Wymaga: pip install pyinstaller
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Version = "2.6"
if (Test-Path (Join-Path $Root "promptbase.py")) {
    $match = Select-String -Path (Join-Path $Root "promptbase.py") -Pattern 'APP_VERSION = "([^"]+)"' | Select-Object -First 1
    if ($match) { $Version = $match.Matches.Groups[1].Value }
}

Write-Host "PrompBase build v$Version"
Write-Host "Instalacja PyInstaller (jesli brak)..."
python -m pip install --upgrade pyinstaller --quiet

$icon = Join-Path $Root "assets\promptbase.ico"
$pyArgs = @(
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", "PrompBase",
    "promptbase.py"
)
if (Test-Path $icon) {
    $pyArgs += @("--icon", $icon)
}

Write-Host "Budowanie EXE..."
python -m PyInstaller @pyArgs

$exe = Join-Path $Root "dist\PrompBase.exe"
if (-not (Test-Path $exe)) {
    Write-Host "Nie znaleziono dist\PrompBase.exe - sprawdz log PyInstaller."
    exit 1
}
Write-Host "EXE: $exe"

$packageName = "PrompBase-$Version-Windows"
$packageDir = Join-Path $Root "dist\$packageName"
if (Test-Path $packageDir) {
    Remove-Item -Recurse -Force $packageDir
}
New-Item -ItemType Directory -Path $packageDir | Out-Null

Copy-Item $exe (Join-Path $packageDir "PrompBase.exe")

$copyItems = @(
    @{ Src = "landing"; Dst = "landing" },
    @{ Src = "docs"; Dst = "docs" },
    @{ Src = "PRICING.md"; Dst = "PRICING.md" },
    @{ Src = "OPIS-NAFFY.md"; Dst = "OPIS-NAFFY.md" },
    @{ Src = "scripts\START-Po-pobraniu.txt"; Dst = "START.txt" },
    @{ Src = "Otworz-landing.bat"; Dst = "Otworz-landing.bat" },
    @{ Src = "models.json"; Dst = "models.json" }
)
foreach ($item in $copyItems) {
    $srcPath = Join-Path $Root $item.Src
    $dstPath = Join-Path $packageDir $item.Dst
    if (Test-Path $srcPath) {
        if ((Get-Item $srcPath).PSIsContainer) {
            Copy-Item -Recurse $srcPath $dstPath
        } else {
            Copy-Item $srcPath $dstPath
        }
        Write-Host "Dodano: $($item.Dst)"
    }
}

$zipPath = Join-Path $Root "dist\$packageName.zip"
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
Compress-Archive -Path (Join-Path $packageDir "*") -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host ""
Write-Host "Gotowe:"
Write-Host "  Folder: $packageDir"
Write-Host "  ZIP:    $zipPath"
Write-Host ""
Write-Host "Wrzuc na GitHub Releases: $packageName.zip oraz PrompBase.exe"
