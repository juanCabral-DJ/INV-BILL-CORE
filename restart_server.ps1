$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

& (Join-Path $projectRoot "stop_server.ps1")
& (Join-Path $projectRoot "start_server.ps1")
