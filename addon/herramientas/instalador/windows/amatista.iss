; Instalador de Amatista para Windows (motor 6.2): un .exe firmado en lugar del .zip con el .bat.
;
; Lo compila Inno Setup 6 sobre la carpeta que deja
;     python addon/herramientas/instaladores.py preparar      (dist/instaladores/comun)
; así:
;     iscc /DVersion=6.2.0 /DComun=..\..\..\..\dist\instaladores\comun addon\herramientas\instalador\windows\amatista.iss
; El flujo .github/workflows/instaladores.yml lo hace solo y lo firma (SignPath o un certificado propio).
;
; Qué hace, sin pedir administrador:
; 1. Busca Blender (Archivos de programa, Steam, la carpeta del usuario o la ruta que elijas).
; 2. Copia la extensión oficial y los scripts a %LOCALAPPDATA%\Programs\Amatista.
; 3. Le pide a ese Blender que compruebe su versión (4.2 o más nuevo) e instale Amatista
;    (instalar_en_blender.py: la extensión, el enlace amatista:// y «Blender Amatista» en el menú Inicio).
; 4. Al final ofrece abrir «Blender Amatista».
; Desinstalar (Configuración › Aplicaciones) quita Amatista de ese Blender; tu avance no se toca.
;
; Para que Windows y los antivirus no lo marquen: va firmado con marca de tiempo, con los datos
; del editor en el .exe, sin empaquetadores (UPX) y sin descargar nada mientras instala.

#ifndef Version
  #define Version "0.0.0"
#endif
#ifndef Comun
  #define Comun "..\..\..\..\dist\instaladores\comun"
#endif
#ifndef Salida
  #define Salida "..\..\..\..\dist\instaladores"
#endif

[Setup]
AppId={{6F3D2A9C-4B7E-4F1A-9C2D-AMATISTA3D01}
AppName=Amatista para Blender
AppVersion={#Version}
AppVerName=Amatista para Blender {#Version}
AppPublisher=Maximiliano Cabello Mata
AppPublisherURL=https://amatista-3d.tech
AppSupportURL=https://amatista-3d.tech/#/ayuda
AppUpdatesURL=https://amatista-3d.tech/#/blender
AppCopyright=Copyright (C) 2026 Maximiliano Cabello Mata (GPL-3.0-or-later)
VersionInfoVersion={#Version}
VersionInfoCompany=Amatista
VersionInfoDescription=Instalador de Amatista para Blender
VersionInfoProductName=Amatista para Blender
VersionInfoProductVersion={#Version}
DefaultDirName={localappdata}\Programs\Amatista
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=no
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=
UsedUserAreasWarning=no
ArchitecturesAllowed=x64compatible arm64
ArchitecturesInstallIn64BitMode=x64compatible arm64
OutputDir={#Salida}
OutputBaseFilename=Amatista-{#Version}-Windows
SetupIconFile={#Comun}\amatista.ico
UninstallDisplayIcon={app}\amatista.ico
UninstallDisplayName=Amatista para Blender
LicenseFile={#Comun}\LICENSE.txt
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no
CloseApplications=no
#ifdef Firmar
SignTool=firma
SignedUninstaller=yes
#endif

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Messages]
es.WelcomeLabel2=Esto instala Amatista {#Version} en tu Blender: prácticas guiadas, la herramienta que toca iluminada y tu avance conectado con la plataforma.%n%nNecesitas Blender 4.2 o más nuevo. No hace falta ser administrador.
es.FinishedLabel=Listo. Abre «Blender Amatista» desde el menú Inicio o pulsa «Abrir en Blender» en la plataforma.

[Files]
Source: "{#Comun}\amatista-{#Version}.zip"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Comun}\instalar_en_blender.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Comun}\desinstalar_en_blender.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Comun}\amatista.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Comun}\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Run]
Filename: "{code:Lanzador}"; Parameters: "--app-template amatista"; Description: "Abrir Blender Amatista"; Flags: postinstall nowait skipifsilent; Check: InstaloBien

[UninstallDelete]
Type: files; Name: "{app}\blender.txt"

[Code]
var
  PaginaBlender: TInputFileWizardPage;
  RutaBlender: String;
  Resultado: Integer;

function VersionDeCarpeta(Nombre: String): Integer;
{ «Blender 4.2» → 402: para quedarse con el más nuevo. }
var
  Resto: String;
  Punto, Mayor, Menor: Integer;
begin
  Result := 0;
  Resto := Trim(Copy(Nombre, Pos(' ', Nombre) + 1, 20));
  Punto := Pos('.', Resto);
  if Punto = 0 then
    Exit;
  Mayor := StrToIntDef(Copy(Resto, 1, Punto - 1), 0);
  Menor := StrToIntDef(Copy(Resto, Punto + 1, 3), 0);
  Result := Mayor * 100 + Menor;
end;

function BuscarEnCarpeta(Base: String): String;
var
  Busqueda: TFindRec;
  Mejor, Version: Integer;
begin
  Result := '';
  Mejor := -1;
  if FindFirst(AddBackslash(Base) + 'Blender*', Busqueda) then
  begin
    try
      repeat
        if (Busqueda.Attributes and FILE_ATTRIBUTE_DIRECTORY <> 0) and
           FileExists(AddBackslash(Base) + Busqueda.Name + '\blender.exe') then
        begin
          Version := VersionDeCarpeta(Busqueda.Name);
          if Version > Mejor then
          begin
            Mejor := Version;
            Result := AddBackslash(Base) + Busqueda.Name + '\blender.exe';
          end;
        end;
      until not FindNext(Busqueda);
    finally
      FindClose(Busqueda);
    end;
  end;
end;

function BuscarBlender(): String;
begin
  Result := GetEnv('AMATISTA_BLENDER');
  if (Result <> '') and FileExists(Result) then
    Exit;
  Result := BuscarEnCarpeta(ExpandConstant('{commonpf64}\Blender Foundation'));
  if Result = '' then
    Result := BuscarEnCarpeta(ExpandConstant('{commonpf32}\Blender Foundation'));
  if Result = '' then
    Result := BuscarEnCarpeta(ExpandConstant('{localappdata}\Programs\Blender Foundation'));
  if (Result = '') and FileExists(ExpandConstant('{commonpf32}\Steam\steamapps\common\Blender\blender.exe')) then
    Result := ExpandConstant('{commonpf32}\Steam\steamapps\common\Blender\blender.exe');
end;

procedure InitializeWizard();
begin
  RutaBlender := BuscarBlender();
  PaginaBlender := CreateInputFilePage(wpLicense, 'Tu Blender',
    '¿Dónde está Blender? Amatista se instala dentro de él.',
    'Si no tienes Blender, descárgalo gratis en https://www.blender.org/download/ (4.2 o más nuevo), ' +
    'instálalo y vuelve a abrir este instalador.');
  PaginaBlender.Add('blender.exe:', 'Blender|blender.exe', '.exe');
  PaginaBlender.Values[0] := RutaBlender;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  { Si ya lo encontramos, no preguntamos. }
  Result := (PageID = PaginaBlender.ID) and (RutaBlender <> '') and FileExists(RutaBlender);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = PaginaBlender.ID then
  begin
    RutaBlender := Trim(PaginaBlender.Values[0]);
    if (RutaBlender = '') or not FileExists(RutaBlender) then
    begin
      MsgBox('Elige el archivo blender.exe (por ejemplo C:\Program Files\Blender Foundation\Blender 4.2\blender.exe).',
        mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function Lanzador(Param: String): String;
{ blender-launcher.exe abre Blender sin la ventana negra de la consola. }
begin
  Result := ExtractFilePath(RutaBlender) + 'blender-launcher.exe';
  if not FileExists(Result) then
    Result := RutaBlender;
end;

function InstaloBien(): Boolean;
begin
  Result := Resultado = 0;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Parametros: String;
begin
  if CurStep <> ssPostInstall then
    Exit;
  Resultado := -1;
  SaveStringToFile(ExpandConstant('{app}\blender.txt'), RutaBlender, False);
  WizardForm.StatusLabel.Caption := 'Blender está instalando Amatista…';
  Parametros := '--background --factory-startup --python-exit-code 9 --python "' +
    ExpandConstant('{app}\instalar_en_blender.py') + '" -- "' + ExpandConstant('{app}\amatista-{#Version}.zip') + '"';
  if not Exec(RutaBlender, Parametros, ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, Resultado) then
  begin
    MsgBox('No se pudo abrir Blender en ' + RutaBlender + '.', mbError, MB_OK);
    Exit;
  end;
  if Resultado = 3 then
    MsgBox('Tu Blender es anterior a 4.2 y no puede instalar Amatista. Descarga uno nuevo en https://www.blender.org/download/ y vuelve a abrir este instalador.',
      mbError, MB_OK)
  else if Resultado <> 0 then
    MsgBox('Blender no pudo instalar Amatista (código ' + IntToStr(Resultado) + '). Cierra Blender si está abierto y vuelve a intentarlo.',
      mbError, MB_OK);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Ruta: AnsiString;
  Codigo: Integer;
begin
  if CurUninstallStep <> usUninstall then
    Exit;
  if LoadStringFromFile(ExpandConstant('{app}\blender.txt'), Ruta) and FileExists(String(Ruta)) then
    Exec(String(Ruta), '--background --factory-startup --python "' + ExpandConstant('{app}\desinstalar_en_blender.py') + '"',
      ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, Codigo);
end;
