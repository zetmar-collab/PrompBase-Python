; Instalator PrompBase (Inno Setup)
; Buduj przez: scripts\build_installer.ps1 (najpierw build_windows.ps1)
; Wersja przekazywana z zewnątrz: ISCC /DAppVersion=2.8 installer\PrompBase.iss

#ifndef AppVersion
  #define AppVersion "2.10.1"
#endif

#define AppName "PrompBase"
#define AppPublisher "Marek Zettel"
#define AppURL "https://github.com/zetmar-collab/PrompBase-Python"
#define AppExe "PrompBase.exe"
; Katalog ze spakowaną aplikacją (wynik build_windows.ps1)
#define SourceDir "..\dist\PrompBase-" + AppVersion + "-Windows"

[Setup]
AppId={{D5E387CB-4CBD-4114-B47C-F0B53E58ADC5}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Instalacja bez uprawnień administratora (per-user), gdy to możliwe.
PrivilegesRequiredOverridesAllowed=dialog commandline
OutputDir=..\dist
OutputBaseFilename=PrompBase-{#AppVersion}-Setup
SetupIconFile=..\assets\promptbase.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\models.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\landing\*"; DestDir: "{app}\landing"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.tmp"
Source: "{#SourceDir}\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\PRICING.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceDir}\OPIS-NAFFY.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceDir}\START.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceDir}\Otworz-landing.bat"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Strona produktu (landing)"; Filename: "{app}\landing\index.html"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
