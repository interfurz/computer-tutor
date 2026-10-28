#define AppVersion "1.0.0"

[Setup]
AppId={{46869B09-E5EE-42F3-9FE5-3C7B9E4641B4}
AppName=Computer Tutor
AppVersion={#AppVersion}
AppPublisher=Computer Tutor
AppPublisherURL=https://github.com/interfurz/computer-tutor
DefaultDirName={localappdata}\Programs\ComputerTutor
DefaultGroupName=Computer Tutor
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
OutputDir=..\dist
OutputBaseFilename=ComputerTutor-Setup-{#AppVersion}-x64
SetupIconFile=tutor.ico
UninstallDisplayIcon={app}\ComputerTutor.exe
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; Flags: unchecked

[Files]
Source: "..\dist\ComputerTutor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Computer Tutor"; Filename: "{app}\ComputerTutor.exe"
Name: "{autodesktop}\Computer Tutor"; Filename: "{app}\ComputerTutor.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ComputerTutor.exe"; Description: "Computer Tutor starten"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\computer-tutor-mcp.exe"; Parameters: "--shutdown"; Flags: runhidden waituntilterminated skipifdoesntexist
