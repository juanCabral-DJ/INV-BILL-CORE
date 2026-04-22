$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$existing = netstat -ano | Select-String ":8000\s+.*LISTENING\s+(\d+)$"
if (-not $existing) {
    Write-Output "No hay ningun proceso escuchando en el puerto 8000."
    exit 0
}

$processId = [int]$existing.Matches[0].Groups[1].Value
Stop-Process -Id $processId -Force
Start-Sleep -Seconds 2

$stillListening = netstat -ano | Select-String ":8000\s+.*LISTENING\s+(\d+)$"
if ($stillListening) {
    throw "El proceso del puerto 8000 sigue activo."
}

Write-Output "Servidor detenido."
