[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command py.exe -ErrorAction SilentlyContinue)) {
    throw "No se encontró Python. Instala Python 3.12 de 64 bits desde python.org."
}

$DenoCommand = Get-Command deno.exe -ErrorAction SilentlyContinue
if (-not $DenoCommand) {
    throw "No se encontró Deno. Instálalo con: winget install DenoLand.Deno"
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & py.exe -3.12 -m venv .venv
}

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install --requirement requirements-build.txt

$env:DENO_EXE = $DenoCommand.Source
$env:PYTHONPATH = Join-Path $PSScriptRoot "src"
& $Python -m unittest discover -s tests -v
& $Python -m PyInstaller --noconfirm --clean StudioMokaFrameExporter.spec

$Executable = Join-Path $PSScriptRoot "dist\Exportador de fotogramas de YouTube - Studio Moka.exe"
if (-not (Test-Path $Executable)) {
    throw "La compilación terminó sin crear el ejecutable esperado."
}

Write-Host ""
Write-Host "Compilación terminada:" -ForegroundColor Green
Write-Host $Executable
Get-FileHash -Algorithm SHA256 $Executable
Write-Warning "El ejecutable todavía no está firmado. Ejecuta sign.ps1 con un certificado RSA confiable."
