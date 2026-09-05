$ErrorActionPreference = "Stop"
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$denoExe = Join-Path $projectDir "deno.exe"

if (Test-Path $denoExe) {
    Write-Host "Using existing deno.exe"
    exit 0
}

$zipPath = Join-Path $env:TEMP "youtube-frame-exporter-deno.zip"
$extractDir = Join-Path $env:TEMP "youtube-frame-exporter-deno"
$url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"

Write-Host "Downloading the Deno runtime required by YouTube..."
Invoke-WebRequest -Uri $url -OutFile $zipPath
if (Test-Path $extractDir) {
    Remove-Item $extractDir -Recurse -Force
}
Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
Copy-Item (Join-Path $extractDir "deno.exe") $denoExe -Force
Remove-Item $zipPath -Force
Remove-Item $extractDir -Recurse -Force
Write-Host "Deno downloaded."
