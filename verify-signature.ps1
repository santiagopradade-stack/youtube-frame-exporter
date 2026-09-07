[CmdletBinding()]
param(
    [string]$Executable = "$PSScriptRoot\dist\Exportador de fotogramas de YouTube - Studio Moka.exe"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $Executable)) {
    throw "No existe el ejecutable: $Executable"
}

$Signature = Get-AuthenticodeSignature -FilePath $Executable
$Signature | Format-List Status, StatusMessage, SignerCertificate, TimeStamperCertificate
if ($Signature.Status -ne "Valid") {
    throw "La firma Authenticode no es válida: $($Signature.Status)"
}

