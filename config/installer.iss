;###############################################################################
; Inno Setup Script for ZEMmacOS
; Version: Phase 1 - Simple Stable Installer
;###############################################################################

[Setup]
AppId={{8E2D8E2D-8E2D-8E2D-8E2D-8E2D8E2D8E2D}
AppName=ZEMmacOS
AppVersion=1.0.0
AppPublisher=WebSmithDigital
AppPublisherURL=https://www.webSmithDigital.com
AppSupportURL=https://www.webSmithDigital.com/support
AppUpdatesURL=https://www.webSmithDigital.com/updates
DefaultDirName={autopf}\ZEMmacOS
DefaultGroupName=ZEMmacOS
AllowNoIcons=yes
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer_output
OutputBaseFilename=ZEMmacOS_Setup
SetupIconFile=public\images\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=yes
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\ZEMmacOS.exe
UninstallDisplayName=ZEMmacOS
CloseApplications=yes
RestartApplications=no
WizardImageFile=public\images\banner.bmp
WizardSmallImageFile=public\images\logo-small.bmp
ShowLanguageDialog=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\ZEMmacOS.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "Readme.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "help\*"; DestDir: "{app}\help"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "public\images\*"; DestDir: "{app}\public\images"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Registry]
Root: "HKCU"; Subkey: "Software\WebSmithDigital\ZEMmacOS"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue
Root: "HKCU"; Subkey: "Software\WebSmithDigital\ZEMmacOS"; ValueType: string; ValueName: "Version"; ValueData: "1.0.0"; Flags: uninsdeletevalue

[Icons]
Name: "{group}\ZEMmacOS"; Filename: "{app}\ZEMmacOS.exe"; WorkingDir: "{app}"; IconFilename: "{app}\public\images\logo.ico"
Name: "{group}\Uninstall ZEMmacOS"; Filename: "{uninstallexe}"; WorkingDir: "{app}"
Name: "{autodesktop}\ZEMmacOS"; Filename: "{app}\ZEMmacOS.exe"; WorkingDir: "{app}"; IconFilename: "{app}\public\images\logo.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\ZEMmacOS.exe"; Description: "{cm:LaunchProgram,ZEMmacOS}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\temp"
Type: files; Name: "{app}\*.lic"
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.tmp"
Type: dirifempty; Name: "{app}\public\images"
Type: dirifempty; Name: "{app}\public"
