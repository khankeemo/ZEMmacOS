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
Type: files; Name: "{app}\trial.flag"
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.tmp"
Type: dirifempty; Name: "{app}\public\images"
Type: dirifempty; Name: "{app}\public"

[Code]
var
  CustomPage: TWizardPage;
  FullNameEdit: TEdit;
  EmailEdit: TEdit;
  LicenseKeyEdit: TEdit;
  TrialCheckBox: TCheckBox;

procedure InitializeWizard();
var
  Page: TWizardPage;
  FullNameLabel: TLabel;
  EmailLabel: TLabel;
  LicenseKeyLabel: TLabel;
  VerticalSpacing: Integer;
  LabelWidth: Integer;
  EditWidth: Integer;
  EditLeft: Integer;
  CurrentY: Integer;
begin
  Page := CreateCustomPage(wpSelectDir, 'License Information', 'Please enter your information');
  CustomPage := Page;
  
  VerticalSpacing := 12;
  LabelWidth := ScaleX(90);
  EditWidth := ScaleX(250);
  EditLeft := LabelWidth + ScaleX(10);
  CurrentY := ScaleY(8);
  
  FullNameLabel := TLabel.Create(Page);
  FullNameLabel.Parent := Page.Surface;
  FullNameLabel.Caption := 'Full Name:';
  FullNameLabel.Left := ScaleX(8);
  FullNameLabel.Top := CurrentY;
  FullNameLabel.Width := LabelWidth;
  
  FullNameEdit := TEdit.Create(Page);
  FullNameEdit.Parent := Page.Surface;
  FullNameEdit.Left := EditLeft;
  FullNameEdit.Top := CurrentY;
  FullNameEdit.Width := EditWidth;
  FullNameEdit.Text := '';
  
  CurrentY := CurrentY + FullNameEdit.Height + VerticalSpacing;
  
  EmailLabel := TLabel.Create(Page);
  EmailLabel.Parent := Page.Surface;
  EmailLabel.Caption := 'Email Address:';
  EmailLabel.Left := ScaleX(8);
  EmailLabel.Top := CurrentY;
  EmailLabel.Width := LabelWidth;
  
  EmailEdit := TEdit.Create(Page);
  EmailEdit.Parent := Page.Surface;
  EmailEdit.Left := EditLeft;
  EmailEdit.Top := CurrentY;
  EmailEdit.Width := EditWidth;
  EmailEdit.Text := '';
  
  CurrentY := CurrentY + EmailEdit.Height + VerticalSpacing;
  
  LicenseKeyLabel := TLabel.Create(Page);
  LicenseKeyLabel.Parent := Page.Surface;
  LicenseKeyLabel.Caption := 'License Key (if you have one):';
  LicenseKeyLabel.Left := ScaleX(8);
  LicenseKeyLabel.Top := CurrentY;
  LicenseKeyLabel.Width := LabelWidth + ScaleX(50);
  
  LicenseKeyEdit := TEdit.Create(Page);
  LicenseKeyEdit.Parent := Page.Surface;
  LicenseKeyEdit.Left := EditLeft;
  LicenseKeyEdit.Top := CurrentY;
  LicenseKeyEdit.Width := EditWidth;
  LicenseKeyEdit.Text := '';
  
  CurrentY := CurrentY + LicenseKeyEdit.Height + VerticalSpacing + ScaleY(8);
  
  TrialCheckBox := TCheckBox.Create(Page);
  TrialCheckBox.Parent := Page.Surface;
  TrialCheckBox.Caption := 'Enable 7-day trial mode (no license key needed)';
  TrialCheckBox.Left := EditLeft;
  TrialCheckBox.Top := CurrentY;
  TrialCheckBox.Width := ScaleX(300);
  TrialCheckBox.Checked := False;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  TrialFlagPath: String;
  Content: String;
  DateTimeStr: String;
  Lines: TArrayOfString;
begin
  if CurStep = ssInstall then
  begin
    TrialFlagPath := ExpandConstant('{app}\trial.flag');
    
    if TrialCheckBox.Checked then
    begin
      DateTimeStr := GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':');
      Content := 'trial_installed=' + DateTimeStr + #13#10;
      Content := Content + 'expires_in_days=7' + #13#10;
      Content := Content + 'mode=evaluation' + #13#10;
      
      SetArrayLength(Lines, 1);
      Lines[0] := Content;
      SaveStringsToFile(TrialFlagPath, Lines, False);
    end;
    
    if FullNameEdit.Text <> '' then
    begin
      RegWriteStringValue(HKEY_CURRENT_USER, 'Software\WebSmithDigital\ZEMmacOS', 'UserName', FullNameEdit.Text);
    end;
    
    if EmailEdit.Text <> '' then
    begin
      RegWriteStringValue(HKEY_CURRENT_USER, 'Software\WebSmithDigital\ZEMmacOS', 'UserEmail', EmailEdit.Text);
    end;
    
    if LicenseKeyEdit.Text <> '' then
    begin
      RegWriteStringValue(HKEY_CURRENT_USER, 'Software\WebSmithDigital\ZEMmacOS', 'LicenseKeyProvided', LicenseKeyEdit.Text);
    end;
    
    if TrialCheckBox.Checked then
    begin
      RegWriteStringValue(HKEY_CURRENT_USER, 'Software\WebSmithDigital\ZEMmacOS', 'InstallMode', 'Trial');
    end
    else if LicenseKeyEdit.Text <> '' then
    begin
      RegWriteStringValue(HKEY_CURRENT_USER, 'Software\WebSmithDigital\ZEMmacOS', 'InstallMode', 'LicenseKeyEntered');
    end
    else
    begin
      RegWriteStringValue(HKEY_CURRENT_USER, 'Software\WebSmithDigital\ZEMmacOS', 'InstallMode', 'NoLicense');
    end;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  MessageText: String;
  Response: Integer;
begin
  Result := True;
  
  if CurPageID = CustomPage.ID then
  begin
    if (LicenseKeyEdit.Text = '') and (not TrialCheckBox.Checked) then
    begin
      MessageText := 'You have not entered a license key or enabled trial mode.' + #13#10#13#10;
      MessageText := MessageText + 'Would you like to enable the 7-day trial?';
      
      Response := MsgBox(MessageText, mbConfirmation, MB_YESNO);
      if Response = IDYES then
      begin
        TrialCheckBox.Checked := True;
        Result := True;
      end
      else
      begin
        Result := False;
      end;
    end;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = CustomPage.ID then
  begin
    Log('License information page displayed');
  end;
end;

procedure DeinitializeSetup();
begin
  Log('Setup completed for ZEMmacOS');
end;