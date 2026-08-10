#Requires -Version 5.1
<#
.SYNOPSIS
    Build completo de ContApp: tests, PyInstaller, zip portable e instalador Inno Setup.

.DESCRIPTION
    Ejecuta el pipeline de build local:
      1. Tests con pytest.
      2. Limpia carpetas build/ y dist/.
      3. Build con PyInstaller (ContApp.spec).
      4. Crea ZIP portable con build_portable_zip.py.
      5. (Opcional) Build del instalador con Inno Setup.

.PARAMETER Version
    Version para nombrar el instalador y el zip portable.
    Si no se pasa, se lee de app/version.py.

.PARAMETER SkipTests
    Omite la ejecucion de tests.

.PARAMETER SkipInstaller
    Omite el build del instalador .exe (Inno Setup).

.EXAMPLE
    .\scripts\build\build_release.ps1 -Version 1.0.1

.EXAMPLE
    .\scripts\build\build_release.ps1 -Version 1.0.1 -SkipInstaller
#>
[CmdletBinding()]
param(
    [string]$Version = "",
    [switch]$SkipTests,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Push-Location $repoRoot

try {
    # ------------------------------------------------------------------
    # 0. Detectar version
    # ------------------------------------------------------------------
    if (-not $Version) {
        $versionLine = Select-String -Path "app\version.py" -Pattern '__version__\s*=\s*"([^"]+)"' |
            Select-Object -First 1
        if (-not $versionLine) {
            throw "No se pudo leer __version__ de app/version.py"
        }
        $Version = $versionLine.Matches.Groups[1].Value
    }
    Write-Host "Version: $Version" -ForegroundColor Cyan

    # ------------------------------------------------------------------
    # 1. Tests
    # ------------------------------------------------------------------
    if (-not $SkipTests) {
        Write-Host "`n[1/5] Ejecutando tests..." -ForegroundColor Cyan
        .\.venv\Scripts\python.exe -m pytest tests/ -v --tb=short
        if ($LASTEXITCODE -ne 0) {
            throw "Tests fallaron con codigo $LASTEXITCODE"
        }
    } else {
        Write-Host "`n[1/5] Tests omitidos." -ForegroundColor Yellow
    }

    # ------------------------------------------------------------------
    # 2. Limpiar builds previos
    # ------------------------------------------------------------------
    Write-Host "`n[2/5] Limpiando build/ y dist/..." -ForegroundColor Cyan
    if (Test-Path build) { Remove-Item -Recurse -Force build }
    if (Test-Path dist)  { Remove-Item -Recurse -Force dist }

    # ------------------------------------------------------------------
    # 3. PyInstaller
    # ------------------------------------------------------------------
    Write-Host "`n[3/5] Build con PyInstaller..." -ForegroundColor Cyan
    .\.venv\Scripts\pyinstaller.exe --noconfirm --clean ContApp.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller fallo con codigo $LASTEXITCODE"
    }

    $exe = "dist\ContApp\ContApp.exe"
    if (-not (Test-Path $exe)) {
        throw "No se encontro el ejecutable: $exe"
    }

    # ------------------------------------------------------------------
    # 4. ZIP portable
    # ------------------------------------------------------------------
    Write-Host "`n[4/5] Creando ZIP portable..." -ForegroundColor Cyan
    .\.venv\Scripts\python.exe scripts\build\build_portable_zip.py $Version
    if ($LASTEXITCODE -ne 0) {
        throw "build_portable_zip.py fallo con codigo $LASTEXITCODE"
    }

    # ------------------------------------------------------------------
    # 5. Instalador Inno Setup (opcional)
    # ------------------------------------------------------------------
    if (-not $SkipInstaller) {
        Write-Host "`n[5/5] Build del instalador con Inno Setup..." -ForegroundColor Cyan
        $candidatos = @(
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
            "${env:ProgramFiles}\Inno Setup 7\ISCC.exe",
            "${env:LOCALAPPDATA}\Programs\Inno Setup 7\ISCC.exe"
        )
        $iscc = $candidatos | Where-Object { Test-Path $_ } | Select-Object -First 1
        if (-not $iscc) {
            throw "No se encontro ISCC.exe. Instala Inno Setup 6/7 o usa -SkipInstaller."
        }
        Write-Host "Usando ISCC: $iscc" -ForegroundColor DarkGray
        & $iscc /DMyAppVersion=$Version ContApp.iss
        if ($LASTEXITCODE -ne 0) {
            throw "Inno Setup fallo con codigo $LASTEXITCODE"
        }
    } else {
        Write-Host "`n[5/5] Instalador omitido." -ForegroundColor Yellow
    }

    # ------------------------------------------------------------------
    # Resumen
    # ------------------------------------------------------------------
    Write-Host "`n=== Build completado ===" -ForegroundColor Green
    Get-ChildItem dist | Format-Table Name, Length, LastWriteTime
}
catch {
    Write-Host "`nERROR: $_" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
