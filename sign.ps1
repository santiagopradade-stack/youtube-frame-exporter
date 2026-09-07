[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Fa-f0-9]{40}$')]
    [string]$CertificateThumbprint,

    [string]$Executable = "$PSScriptRoot\dist\Exportador de fotogramas de YouTube - Studio Moka.exe",

    [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Executable)) {
    throw "No existe el ejecutable: $Executable"
}

$SignToolCommand = Get-Command signtool.exe -ErrorAction SilentlyContinue
if ($SignToolCommand) {
    $SignToolExe = $SignToolCommand.Source
} else {
    $WindowsKits = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    $SignToolPath = Get-ChildItem $WindowsKits -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if (-not $SignToolPath) {
        throw "No se encontró signtool.exe. Instala Windows SDK desde Visual Studio Installer."
    }
    $SignToolExe = $SignToolPath.FullName
}

& $SignToolExe sign /sha1 $CertificateThumbprint /fd SHA256 /tr $TimestampUrl /td SHA256 /v $Executable
if ($LASTEXITCODE -ne 0) {
    throw "La firma falló con el código $LASTEXITCODE."
}

& $SignToolExe verify /pa /all /v $Executable
if ($LASTEXITCODE -ne 0) {
    throw "La verificación de la firma falló con el código $LASTEXITCODE."
}

Write-Host "Firma y verificación terminadas correctamente." -ForegroundColor Green
