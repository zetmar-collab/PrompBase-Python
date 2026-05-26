$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "PrompBase Python.lnk"
$TargetPath = Join-Path $AppDir "Start-PrompBase-Windows.bat"
$IconPath = Join-Path $AppDir "assets\promptbase.ico"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $AppDir
$Shortcut.Description = "PrompBase Python"
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
}
$Shortcut.Save()

Write-Host "Utworzono skrot: $ShortcutPath"
