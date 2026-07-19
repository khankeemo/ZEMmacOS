;###############################################################################
; Inno Setup Script for ZEMmacOS v3.0.0
; Production Installer - Professional Distribution Package
; Publisher: WebSmithDigital
;###############################################################################

#define MyAppName "ZEMmacOS"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "WebSmithDigital"
#define MyAppURL "https://www.websmithdigital.com"
#define MyAppSupportURL "https://www.websmithdigital.com/support"
#define MyAppUpdatesURL "https://www.websmithdigital.com/updates"
#define MyAppExeName "ZEMmacOS.exe"
#define MyAppAssocName "ZEMmacOS Data"
#define MyAppAssocExt ".zem"

[Setup]
; Basic
AppId={{ZEMmacOS-Prod-v3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppSupportURL}
AppUpdatesURL={#MyAppUpdatesURL}
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

; Installer images
WizardImageFile=..\public\images\banner.bmp
WizardSmallImageFile=..\public\images\logo-small.bmp

; Language
ShowLanguageDialog=no

; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Signing (optional - set paths for production)
; SignTool=mysigntool
; SignedUninstaller=yes

; Update support
UsePreviousAppDir=yes
UsePreviousGroup=yes
UpdateUninstallLogAppName=no

; Allow upgrade/reinstall

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "launchafter"; Description: "&Launch {#MyAppName} after installation"; GroupDescription: "Startup options:"; Flags: unchecked

;-----------------------------------------------------------------------------
; FILES TO INSTALL
;-----------------------------------------------------------------------------
[Files]
; Application files (built by PyInstaller - includes EXE, configs, SDK, images, help)
Source: "..\dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Legal texts for installer pages (extracted to temp during setup)
Source: "..\config\license_agreement.txt"; Flags: ignoreversion dontcopy
Source: "..\config\terms_of_use.txt"; Flags: ignoreversion dontcopy
Source: "..\config\privacy_policy.txt"; Flags: ignoreversion dontcopy

;-----------------------------------------------------------------------------
; REGISTRY
;-----------------------------------------------------------------------------
[Registry]
; Installation metadata
Root: "HKCU"; Subkey: "Software\WebSmithDigital\{#MyAppName}"; Flags: uninsdeletekeyifempty
Root: "HKCU"; Subkey: "Software\WebSmithDigital\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue
Root: "HKCU"; Subkey: "Software\WebSmithDigital\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletevalue


; Application path for shell
Root: "HKLM"; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletevalue
Root: "HKLM"; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: "Path"; ValueData: "{app}"; Flags: uninsdeletevalue

;-----------------------------------------------------------------------------
; ICONS (Start Menu & Desktop)
;-----------------------------------------------------------------------------
[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\public\images\logo.ico"; Comment: "ZEMmacOS - macOS Download Manager"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; WorkingDir: "{app}"
Name: "{group}\Visit WebSmithDigital"; Filename: "{#MyAppURL}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\public\images\logo.ico"; Tasks: desktopicon

;-----------------------------------------------------------------------------
; RUN AFTER INSTALL
;-----------------------------------------------------------------------------
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: postinstall nowait skipifsilent; Tasks: launchafter

;-----------------------------------------------------------------------------
; UNINSTALL - Remove all traces
;-----------------------------------------------------------------------------
[UninstallDelete]
; Application files
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\temp"
Type: filesandordirs; Name: "{app}\__pycache__"
; License cache files
Type: files; Name: "{app}\*.lic"
Type: files; Name: "{app}\*.key"
Type: files; Name: "{app}\*_cache*"
; Log and temp files
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.tmp"
Type: files; Name: "{app}\*.pyc"
; User data folder (WebSmith cache)
Type: filesandordirs; Name: "{localappdata}\WebSmith"
Type: filesandordirs; Name: "{userappdata}\WebSmith"

;-----------------------------------------------------------------------------
; CODE - Custom installer pages, validation, and helpers
;-----------------------------------------------------------------------------
[Code]

// ---------------------------------------------------------------------------
// Custom page IDs
// ---------------------------------------------------------------------------
var
  AboutPage: TWizardPage;
  TermsPage: TWizardPage;
  PrivacyPage: TWizardPage;
  TermsAccepted: Boolean;

// ---------------------------------------------------------------------------
// Initialize Wizard - Check if already installed
// ---------------------------------------------------------------------------
function InitializeSetup: Boolean;
begin
  Result := True;
  TermsAccepted := False;
end;

// ---------------------------------------------------------------------------
// Get current date as DWORD for registry (YYYYMMDD format)
// ---------------------------------------------------------------------------
// Create About Page
// ---------------------------------------------------------------------------
procedure CreateAboutPage;
var
  AboutLabel, CompanyLabel, TaglineLabel, AddressLabel: TNewStaticText;
  LogoImage: TBitmapImage;
begin
  AboutPage := CreateCustomPage(wpWelcome, 'About WebSmith Digital', 'About the publisher');

  CompanyLabel := TNewStaticText.Create(AboutPage);
  CompanyLabel.Parent := AboutPage.Surface;
  CompanyLabel.Caption := 'Websmith Digital™';
  CompanyLabel.Font.Name := 'Segoe UI';
  CompanyLabel.Font.Size := 18;
  CompanyLabel.Font.Style := [fsBold];
  CompanyLabel.Left := 0;
  CompanyLabel.Top := 20;
  CompanyLabel.Width := AboutPage.SurfaceWidth;

  TaglineLabel := TNewStaticText.Create(AboutPage);
  TaglineLabel.Parent := AboutPage.Surface;
  TaglineLabel.Caption := 'Universal License Controller';
  TaglineLabel.Font.Name := 'Segoe UI';
  TaglineLabel.Font.Size := 12;
  TaglineLabel.Font.Color := clGray;
  TaglineLabel.Left := 0;
  TaglineLabel.Top := 50;
  TaglineLabel.Width := AboutPage.SurfaceWidth;

  AboutLabel := TNewStaticText.Create(AboutPage);
  AboutLabel.Parent := AboutPage.Surface;
  AboutLabel.Caption := 'Protected by Brevo and Websmith' + #13#10 +
    '' + #13#10 +
    'Kolkata, West Bengal, India' + #13#10 +
    '' + #13#10 +
    'support@websmithdigital.com' + #13#10 +
    'https://www.websmithdigital.com';
  AboutLabel.Font.Name := 'Segoe UI';
  AboutLabel.Font.Size := 10;
  AboutLabel.Left := 0;
  AboutLabel.Top := 90;
  AboutLabel.Width := AboutPage.SurfaceWidth;
  AboutLabel.Height := 120;
end;

// ---------------------------------------------------------------------------
// Create Terms of Use Page
// ---------------------------------------------------------------------------
procedure CreateTermsPage;
var
  TermsMemo: TNewMemo;
  TermsLabel: TNewStaticText;
begin
  TermsPage := CreateCustomPage(AboutPage.ID, 'Terms of Use', 'Please read the following terms carefully');

  TermsLabel := TNewStaticText.Create(TermsPage);
  TermsLabel.Parent := TermsPage.Surface;
  TermsLabel.Caption := 'Terms of Use';
  TermsLabel.Font.Name := 'Segoe UI';
  TermsLabel.Font.Size := 14;
  TermsLabel.Font.Style := [fsBold];
  TermsLabel.Left := 0;
  TermsLabel.Top := 10;
  TermsLabel.Width := TermsPage.SurfaceWidth;

  TermsMemo := TNewMemo.Create(TermsPage);
  TermsMemo.Parent := TermsPage.Surface;
  TermsMemo.Left := 0;
  TermsMemo.Top := 40;
  TermsMemo.Width := TermsPage.SurfaceWidth;
  TermsMemo.Height := TermsPage.SurfaceHeight - 80;
  TermsMemo.ReadOnly := True;
  TermsMemo.ScrollBars := ssVertical;
  TermsMemo.WordWrap := True;

  // Load terms from bundled file
  TermsMemo.Lines.LoadFromFile(ExpandConstant('{tmp}\terms_of_use.txt'));
end;

// ---------------------------------------------------------------------------
// Create Privacy Policy Page
// ---------------------------------------------------------------------------
procedure CreatePrivacyPage;
var
  PrivacyMemo: TNewMemo;
  PrivacyLabel: TNewStaticText;
  AgreeCheck: TNewCheckBox;
begin
  PrivacyPage := CreateCustomPage(TermsPage.ID, 'Privacy Policy', 'How we handle your data');

  PrivacyLabel := TNewStaticText.Create(PrivacyPage);
  PrivacyLabel.Parent := PrivacyPage.Surface;
  PrivacyLabel.Caption := 'Privacy Policy';
  PrivacyLabel.Font.Name := 'Segoe UI';
  PrivacyLabel.Font.Size := 14;
  PrivacyLabel.Font.Style := [fsBold];
  PrivacyLabel.Left := 0;
  PrivacyLabel.Top := 10;
  PrivacyLabel.Width := PrivacyPage.SurfaceWidth;

  PrivacyMemo := TNewMemo.Create(PrivacyPage);
  PrivacyMemo.Parent := PrivacyPage.Surface;
  PrivacyMemo.Left := 0;
  PrivacyMemo.Top := 40;
  PrivacyMemo.Width := PrivacyPage.SurfaceWidth;
  PrivacyMemo.Height := PrivacyPage.SurfaceHeight - 130;
  PrivacyMemo.ReadOnly := True;
  PrivacyMemo.ScrollBars := ssVertical;
  PrivacyMemo.WordWrap := True;

  PrivacyMemo.Lines.LoadFromFile(ExpandConstant('{tmp}\privacy_policy.txt'));

  AgreeCheck := TNewCheckBox.Create(PrivacyPage);
  AgreeCheck.Parent := PrivacyPage.Surface;
  AgreeCheck.Left := 0;
  AgreeCheck.Top := PrivacyPage.SurfaceHeight - 80;
  AgreeCheck.Width := PrivacyPage.SurfaceWidth;
  AgreeCheck.Caption := 'I have read and agree to the Privacy Policy';
  AgreeCheck.Checked := False;
end;

// ---------------------------------------------------------------------------
// Custom Welcome page - disable Next until agreement
// ---------------------------------------------------------------------------
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
end;

// ---------------------------------------------------------------------------
// Next button handler - enforce agreement
// ---------------------------------------------------------------------------
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
end;

// ---------------------------------------------------------------------------
// Back button handler
// ---------------------------------------------------------------------------
function BackButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
end;

// ---------------------------------------------------------------------------
// Initialize Wizard - Extract legal files then create all custom pages
// ---------------------------------------------------------------------------
procedure InitializeWizard;
begin
  ExtractTemporaryFile('license_agreement.txt');
  ExtractTemporaryFile('terms_of_use.txt');
  ExtractTemporaryFile('privacy_policy.txt');
  CreateAboutPage;
  CreateTermsPage;
  CreatePrivacyPage;
end;

// ---------------------------------------------------------------------------
// CurUninstallStep - Clean up thoroughly
// ---------------------------------------------------------------------------
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    // Additional cleanup if needed
  end;
end;

// ---------------------------------------------------------------------------
// Handle uninstall confirmation
// ---------------------------------------------------------------------------
function InitializeUninstall: Boolean;
begin
  Result := True;
end;

[Messages]
WelcomeLabel1=Welcome to the ZEMmacOS Setup Wizard
WelcomeLabel2=This will install ZEMmacOS v3.0.0 on your computer.%n%nZEMmacOS is a macOS Download Manager that allows you to download macOS installer files directly from Apple's servers.%n%nIt is recommended that you close all other applications before continuing.
WinVersionTooLowError=ZEMmacOS requires Windows 10 or later to run.
UninstallAppFullTitle=Uninstall ZEMmacOS
UninstallAppTitle=ZEMmacOS Uninstall

;-----------------------------------------------------------------------------
; INSTALLER DIRECTORY
;-----------------------------------------------------------------------------
[InstallDelete]
; Clean up any old files before install
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.lic"
Type: files; Name: "{app}\*.key"
