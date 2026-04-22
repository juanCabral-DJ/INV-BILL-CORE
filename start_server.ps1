$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$pythonPath = Join-Path $projectRoot "venv\Scripts\python.exe"
if (-not (Test-Path $pythonPath)) {
    throw "No se encontro Python en venv\Scripts\python.exe"
}

$existing = netstat -ano | Select-String ":8000\s+.*LISTENING\s+(\d+)$"
if ($existing) {
    $processId = [int]$existing.Matches[0].Groups[1].Value
    Stop-Process -Id $processId -Force
    Start-Sleep -Seconds 2
}

$outLog = Join-Path $projectRoot "server.out.log"
$errLog = Join-Path $projectRoot "server.err.log"

Start-Process `
    -FilePath $pythonPath `
    -ArgumentList "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog

Start-Sleep -Seconds 3

try {
    $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/"
    Write-Output "Servidor iniciado. Status: $($response.StatusCode)"
} catch {
    Write-Output "El proceso fue lanzado, pero la verificacion HTTP fallo: $($_.Exception.Message)"
}
