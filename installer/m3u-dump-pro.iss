#define MyAppName "m3u-dump Pro"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "Weslei Tools"
#define MyAppExeName "m3u-dump-pro.exe"

[Setup]
AppId={{D5AA267B-E7A2-4C99-A8D6-380A9F3E4B19}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\m3u-dump-pro
DefaultGroupName=m3u-dump Pro
OutputDir=.
OutputBaseFilename=m3u-dump-pro-installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\m3u-dump Pro"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\m3u-dump Pro"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Executar m3u-dump Pro"; Flags: nowait postinstall skipifsilent
