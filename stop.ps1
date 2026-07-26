[CmdletBinding()]
param(
    [switch]$StopQdrant
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = $PSScriptRoot
$environmentFile = Join-Path $projectRoot ".env"
$pidFile = Join-Path $projectRoot "storage\api.pid"
$expectedEntrypoint = Join-Path $projectRoot ".venv\Scripts\rag-agent-api.exe"

$apiPort = 8000
if (Test-Path -LiteralPath $environmentFile) {
    $apiPortLine = Get-Content -LiteralPath $environmentFile |
        Where-Object {
            $trimmed = $_.Trim()
            $trimmed -and -not $trimmed.StartsWith("#") -and $trimmed.StartsWith("API_PORT=")
        } |
        Select-Object -Last 1
    if ($apiPortLine) {
        $apiPortText = $apiPortLine.Trim().Substring("API_PORT=".Length).Trim().Trim('"').Trim("'")
        if (
            -not [int]::TryParse($apiPortText, [ref]$apiPort) -or
            $apiPort -lt 1 -or
            $apiPort -gt 65535
        ) {
            throw "API_PORT in .env must be an integer from 1 to 65535."
        }
    }
}

$listener = Get-NetTCPConnection `
    -LocalPort $apiPort `
    -State Listen `
    -ErrorAction SilentlyContinue |
    Select-Object -First 1

if ($listener) {
    $processId = [int]$listener.OwningProcess
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId"
    if (-not $process -or $process.CommandLine -notlike "*$expectedEntrypoint*") {
        throw "Port $apiPort belongs to an unexpected process ($processId). It was not stopped."
    }

    Stop-Process -Id $processId -Force
    Write-Host "Stopped the Adaptive RAG API process ($processId)." -ForegroundColor Green
}
else {
    Write-Host "The Adaptive RAG API is not running." -ForegroundColor Yellow
}

if (Test-Path -LiteralPath $pidFile) {
    Remove-Item -LiteralPath $pidFile -Force
}

if ($StopQdrant) {
    Set-Location -LiteralPath $projectRoot
    $dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCommand) {
        throw "Docker was not found, so Qdrant could not be stopped."
    }
    & $dockerCommand.Source compose stop qdrant
    if ($LASTEXITCODE -ne 0) {
        throw "Qdrant could not be stopped."
    }
    Write-Host "Stopped Qdrant without deleting its data volume." -ForegroundColor Green
}
