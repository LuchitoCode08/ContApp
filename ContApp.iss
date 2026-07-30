; ============================================================
; ContApp.iss - Inno Setup Script para ContApp
; ============================================================
;
; Que hace este instalador:
;   - Instala dist/ContApp/ en {autopf}\ContApp (o %LOCALAPPDATA%\ContApp)
;   - Crea acceso directo en el Menu Inicio y (opcional) Escritorio
;   - Registra desinstalador en "Agregar o quitar programas" de Windows
;   - Detecta una instalacion previa y permite upgrade sin perder data
;
; Build:
;   iscc ContApp.iss
;
; Salida:
;   dist/ContApp_Setup-1.0.0.exe   (instalador)
;   dist/ContApp_Setup-1.0.0.zip   (wrapper para subir a GitHub Releases)
;
; Notas de diseno:
;   - Privilegios: "admin" si instalamos en Program Files, "lowest" si en
;     %LOCALAPPDATA%. Elegimos lowest para no pedir UAC (mas friendly).
;   - No instalamos la carpeta jsons/: vive al lado del .exe y se mantiene
;     entre upgrades. El bundle la trae como fallback por si es la primera
;     vez.
;   - Si el usuario ya tiene ContApp, el instalador lo reemplaza in-place.

#define MyAppName "ContApp"
#define MyAppExeName "ContApp.exe"
#define MyAppDescription "Sistema de Automatización Contable"

; Tomamos la version desde app/version.py (unica fuente de verdad).
; Para que funcione, hay que pasar -DMyAppVersion="1.0.0" en la linea de
; comandos de ISCC, o leerla de un archivo. Acá la dejamos parametrizable.
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

[Setup]
; Note: AppId es un GUID unico. NO cambiar entre versiones, sino Windows
; pensara que es una app distinta y no hara upgrade in-place.
AppId={{A1B2C3D4-E5F6-4A7B-8C9D-0E1F2A3B4C5D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=LuchitoCode08
AppPublisherURL=https://github.com/LuchitoCode08/Demo
AppSupportURL=https://github.com/LuchitoCode08/Demo/issues
AppUpdatesURL=https://github.com/LuchitoCode08/Demo/releases
; Inno Setup 6.x NO reconoce la directiva ``AppDescription`` en
; ``[Setup]``. La descripcion se setea via ``AppComments`` (que aparece
; en el panel de "Agregar o quitar programas" de Windows) o via
; ``VersionInfoDescription`` (metadata del .exe). Usamos AppComments
; que es la que el usuario ve al desinstalar.
AppComments={#MyAppDescription}
AppCopyright=Copyright (C) 2026

; Salidas.
OutputDir=dist
OutputBaseFilename=ContApp_Setup-{#MyAppVersion}
; Icono (opcional, debe existir como .ico):
; SetupIconFile=ui\recursos\contapp.ico

; Compresion.
Compression=lzma2/ultra64
SolidCompression=yes

; Privilegios: lowest = instala en %LOCALAPPDATA% sin pedir UAC.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Directorio de instalacion por defecto. Requerido por Inno Setup
; aunque tengamos ``DisableDirPage=yes`` (la directiva es obligatoria,
; solo ocultamos la pagina para que el usuario no la vea).
; Con ``PrivilegesRequired=lowest`` lo llevamos a %LOCALAPPDATA%
; (no a Program Files) para no pedir UAC.
DefaultDirName={localappdata}\{#MyAppName}

; Version de Windows minima: Windows 10.
MinVersion=10.0

; Flags.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Para que el icono del .exe del instalador se vea en la taskbar:
; SetupLogging=yes
Uninstallable=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

; Privado (no se muestra en "Agregar o quitar programas" hasta instalar).
; DisableProgramGroupPage=yes
; No preguntar por directorio destino (lo decidimos nosotros).
DisableDirPage=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Carpeta completa del bundle (incluye ContApp.exe, _internal/, jsons/).
; Source: dist/ContApp/  ->  Dest: {app}\
; Nota: el bundle de PyInstaller --onedir tiene esta estructura exacta.
Source: "dist\ContApp\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Crear subcarpetas vacias para que la app escriba ahi.
; (data/ y log/ no las creamos: las crea app/config.py al primer uso.)

[Icons]
; Menu Inicio.
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
; Mismo escape que en [Run]: las constantes {#...} dentro de
; {cm:...} se referencian con doble llave {{#...}}.
Name: "{group}\{cm:UninstallProgram,{{#MyAppName}}}"; Filename: "{uninstallexe}"
; Escritorio (solo si el usuario marco el checkbox).
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Preguntar al final si quiere ejecutar la app.
; Importante: dentro de {cm:LaunchProgram,...} las constantes preprocesadas
; con {#...} se referencian como {{#...}} (doble llave para escapar).
; Sin esto el compilador aborta con "Unknown constant ContApp" en
; esta linea (porque {#MyAppName} no se expande dentro de un parametro
; de {cm:...}, hay que escaparlo con doble llave).
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{{#MyAppName}}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; NO borrar data/, log/, ni jsons/ al desinstalar: el usuario puede querer
; conservarlos para una reinstalacion limpia. Si quiere limpieza total,
; puede borrar %LOCALAPPDATA%\ContApp\ manualmente.

[Code]
// Hooks de Inno Setup para comportamiento custom.

// Detectar instalacion previa (distinto al AppId de Windows).
function IsUpgrade(): Boolean;
var
  UninstallKey: String;
begin
  UninstallKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' +
                  '{A1B2C3D4-E5F6-4A7B-8C9D-0E1F2A3B4C5D}_is1';
  Result := RegKeyExists(HKLM, UninstallKey) or
            RegKeyExists(HKCU, UninstallKey);
end;

// Mensaje custom al instalar: avisar si es upgrade.
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall and IsUpgrade() then
  begin
    MsgBox(
      'Se detectó una instalación previa de {#MyAppName}.' + #13#10 +
      'Sus datos (preferencias y JSONs editables) se conservarán.',
      mbInformation, MB_OK
    );
  end;
end;