;###############################################################################
; Inno Setup Script for ZEMmacOS v3.0.0
; Publisher: WebSmithDigital
;###############################################################################

#define MyAppName "ZEMmacOS"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "WebSmithDigital"
#define MyAppURL "https://www.websmithdigital.com"
#define MyAppExeName "ZEMmacOS.exe"

[Setup]
; Basic
AppId={{ZEMmacOS-Prod-v3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppCopyright=Copyright (C) 2026 WebSmithDigital
VersionInfoVersion=3.0.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=macOS Download Manager
VersionInfoCopyright=Copyright (C) 2026 WebSmithDigital
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=D:\Software Installer\ZEMmacOS
OutputBaseFilename=ZEMmacOS_Setup
SetupIconFile=..\public\images\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=yes
WizardSizePercent=100
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
CloseApplications=yes
RestartApplications=no

; Language
ShowLanguageDialog=no

; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Update support
UsePreviousAppDir=yes
UsePreviousGroup=yes
UpdateUninstallLogAppName=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "launchafter"; Description: "&Launch {#MyAppName} after installation"; GroupDescription: "Startup options:"; Flags: unchecked

[Files]
; Application files (built by PyInstaller)
Source: "..\dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "ZEMmacOS - macOS Download Manager"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; WorkingDir: "{app}"
Name: "{group}\Visit WebSmithDigital"; Filename: "{#MyAppURL}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: postinstall nowait skipifsilent; Tasks: launchafter

[UninstallDelete]
; Application runtime files
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\temp"
Type: files and dirs; Name: "{app}\__pycache__"

[InstallDelete]
; Clean up old files before install
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\*.log"

[Messages]
WelcomeLabel1=Welcome to the ZEMmacOS Setup Wizard
WelcomeLabel2=This will install ZEMmacOS v3.0.0 on your computer.%n%nZEMmacOS is a macOS Download Manager that allows you to download macOS installer files directly from Apple's servers.%n%nIt is recommended that you close all other applications before continuing.
WinVersionTooLowError=ZEMmacOS requires Windows 10 or later to run.
UninstallAppFullTitle=Uninstall ZEMmacOS
UninstallAppTitle=ZEMmacOS Uninstall
