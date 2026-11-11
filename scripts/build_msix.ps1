# Buduje pakiet PrompBase-<wersja>.msix do publikacji w Microsoft Store.
# Wymaga: wcześniejszego uruchomienia scripts\build_windows.ps1
#         oraz Windows SDK (makeappx.exe) — zwykle zainstalowany z Visual Studio
#         lub samodzielnie: https://aka.ms/windowssdk
#
# Parametry:
#   -Sign   Podpisuje pakiet lokalnym certyfikatem testowym (do sideloadingu
#           na tej maszynie). NIE jest wymagane do wysyłki na Microsoft Store —
#           Partner Center podpisuje pakiet ponownie przy publikacji.
param(
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# Wersja z pbcore/core.py (spójna z build_windows.ps1).
$Version = "2.10.1"
$versionFile = Join-Path $Root "pbcore\core.py"
if (Test-Path $versionFile) {
    $match = Select-String -Path $versionFile -Pattern 'APP_VERSION = "([^"]+)"' | Select-Object -First 1
    if ($match) { $Version = $match.Matches.Groups[1].Value }
}
# MSIX wymaga wersji 4-częściowej (Major.Minor.Build.Revision).
$parts = $Version.Split(".")
while ($parts.Count -lt 3) { $parts += "0" }
$msixVersion = "$($parts[0]).$($parts[1]).$($parts[2]).0"

Write-Host "PrompBase MSIX build v$Version (pakiet: $msixVersion)"

# 1) Wymagaj gotowego builda EXE.
$packageDir = Join-Path $Root "dist\PrompBase-$Version-Windows"
$exeSource = Join-Path $packageDir "PrompBase.exe"
if (-not (Test-Path $exeSource)) {
    Write-Host "Brak $exeSource."
    Write-Host "Uruchom najpierw: scripts\build_windows.ps1"
    exit 1
}

# 2) Znajdź makeappx.exe (Windows SDK) — najnowsza dostępna wersja SDK, x64.
$sdkRoot = "C:\Program Files (x86)\Windows Kits\10\bin"
$makeappx = Get-ChildItem -Path $sdkRoot -Recurse -Filter "makeappx.exe" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match "\\x64\\" } |
    Sort-Object FullName -Descending |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $makeappx) {
    Write-Host "Nie znaleziono makeappx.exe. Zainstaluj Windows SDK:"
    Write-Host "  https://aka.ms/windowssdk (lub komponent 'Windows SDK' w Visual Studio Installer)"
    exit 1
}
Write-Host "makeappx: $makeappx"

# 3) Wygeneruj zasoby graficzne MSIX, jeśli brak.
$assetsDir = Join-Path $Root "msix\Assets"
if (-not (Test-Path (Join-Path $assetsDir "Square150x150Logo.png"))) {
    Write-Host "Generowanie ikon MSIX..."
    python (Join-Path $Root "scripts\generate_msix_assets.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

# 4) Przygotuj folder staging: EXE + Assets + manifest z podstawioną wersją.
$staging = Join-Path $Root "dist\msix-staging"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Path $staging | Out-Null

Copy-Item $exeSource (Join-Path $staging "PrompBase.exe")
Copy-Item $assetsDir (Join-Path $staging "Assets") -Recurse

$manifestSrc = Join-Path $Root "msix\AppxManifest.xml"
# Jawne -Encoding UTF8: Windows PowerShell 5.1 bez tego auto-wykrywa kodowanie
# po systemowej stronie kodowej i psuje polskie znaki (mojibake) mimo BOM.
$manifestContent = Get-Content $manifestSrc -Raw -Encoding UTF8
$manifestContent = $manifestContent.Replace("__VERSION__", $msixVersion)
Set-Content -Path (Join-Path $staging "AppxManifest.xml") -Value $manifestContent -Encoding UTF8 -NoNewline

# 5) Zbuduj .msix.
$outDir = Join-Path $Root "dist"
$msixPath = Join-Path $outDir "PrompBase-$Version.msix"
if (Test-Path $msixPath) { Remove-Item -Force $msixPath }

& $makeappx pack /d $staging /p $msixPath /o
if ($LASTEXITCODE -ne 0) {
    Write-Host "makeappx zwrocil blad ($LASTEXITCODE)."
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Gotowe: $msixPath (NIEPODPISANY — dokladnie taki plik wysylasz do Partner Center)"
Write-Host "Wyslij ten plik w Partner Center (Microsoft Store) — Store podpisze go ponownie przy publikacji."

# 6) Opcjonalnie: osobna, PODPISANA kopia do sideloadingu/testow lokalnych.
#    Plik $msixPath (do Store) NIGDY nie jest podpisywany — Store wymaga
#    dostac niepodpisany pakiet, wlasny podpis Partner Center dodaje sam.
if ($Sign) {
    $testMsixPath = Join-Path $outDir "PrompBase-$Version-Test.msix"
    Copy-Item -Path $msixPath -Destination $testMsixPath -Force
    $msixPath = $testMsixPath
    $signtool = Get-ChildItem -Path $sdkRoot -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "\\x64\\" } |
        Sort-Object FullName -Descending |
        Select-Object -First 1 -ExpandProperty FullName
    if (-not $signtool) {
        Write-Host "Nie znaleziono signtool.exe — pomijam podpisywanie."
        exit 0
    }

    $certSubject = "CN=15A53D32-C868-48EE-B700-5DBB5449CA1B"

    # Użyj istniejącego certyfikatu z magazynu CurrentUser\My (ten sam CN co
    # Publisher w manifeście), jeśli już tam jest — bez tworzenia duplikatu.
    $existing = Get-ChildItem Cert:\CurrentUser\My |
        Where-Object { $_.Subject -eq $certSubject -and $_.HasPrivateKey } |
        Sort-Object NotAfter -Descending |
        Select-Object -First 1

    if ($existing) {
        Write-Host ""
        Write-Host "Uzywam istniejacego certyfikatu testowego: $($existing.Thumbprint)"
        $thumbprint = $existing.Thumbprint
    } else {
        Write-Host ""
        Write-Host "Tworzenie lokalnego certyfikatu testowego (tylko do sideloadingu, NIE do Store)..."
        $cert = New-SelfSignedCertificate -Type Custom -Subject $certSubject `
            -KeyUsage DigitalSignature -FriendlyName "PrompBase test cert" `
            -CertStoreLocation "Cert:\CurrentUser\My" `
            -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
        $thumbprint = $cert.Thumbprint

        $pfxPath = Join-Path $Root "dist\PrompBase-test.pfx"
        $pfxPassword = "prompbase-test"
        $securePwd = ConvertTo-SecureString -String $pfxPassword -Force -AsPlainText
        Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $securePwd | Out-Null
        Write-Host "Certyfikat wyeksportowany takze do: $pfxPath (haslo: $pfxPassword)"
    }

    & $signtool sign /fd SHA256 /sha1 $thumbprint /s My $msixPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "signtool zwrocil blad ($LASTEXITCODE)."
        exit $LASTEXITCODE
    }

    Write-Host ""
    Write-Host "Podpisano pakiet testowy: $msixPath"

    $trusted = Get-ChildItem Cert:\LocalMachine\TrustedPeople -ErrorAction SilentlyContinue |
        Where-Object { $_.Thumbprint -eq $thumbprint }
    if ($trusted) {
        Write-Host "Certyfikat jest juz zaufany (LocalMachine\TrustedPeople) — mozna instalowac od razu:"
        Write-Host "  Add-AppxPackage -Path '$msixPath'"
    } else {
        Write-Host "Aby zainstalowac lokalnie (sideload), zaufaj certyfikatowi i uruchom:"
        Write-Host "  Export-Certificate -Cert Cert:\CurrentUser\My\$thumbprint -FilePath dist\PrompBase-test.cer"
        Write-Host "  Import-Certificate -FilePath dist\PrompBase-test.cer -CertStoreLocation Cert:\LocalMachine\TrustedPeople"
        Write-Host "  Add-AppxPackage -Path '$msixPath'"
    }
}
