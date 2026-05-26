# Buduje PrompBase.exe (PyInstaller). Wymaga: pip install pyinstaller
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Instalacja PyInstaller (jesli brak)..."
python -m pip install --upgrade pyinstaller

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
if (Test-Path $exe) {
    Write-Host "Gotowe: $exe"
} else {
    Write-Host "Nie znaleziono dist\PrompBase.exe - sprawdz log PyInstaller."
    exit 1
}
