[CmdletBinding()]
param(
    [switch]$NoBrowser,
    [switch]$SkipDocker
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = $PSScriptRoot
$venvDirectory = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvDirectory "Scripts\python.exe"
$apiEntrypoint = Join-Path $venvDirectory "Scripts\rag-agent-api.exe"
$environmentFile = Join-Path $projectRoot ".env"
$environmentExample = Join-Path $projectRoot ".env.example"
$storageDirectory = Join-Path $projectRoot "storage"
$stdoutLog = Join-Path $storageDirectory "api.stdout.log"
$stderrLog = Join-Path $storageDirectory "api.stderr.log"
$pidFile = Join-Path $storageDirectory "api.pid"
$qdrantHealthUrl = "http://127.0.0.1:6333/healthz"

function Test-HttpEndpoint {
    param(
        [Parameter(Mandatory)]
        [string]$Url
    )

    $curlCommand = Get-Command curl.exe -ErrorAction SilentlyContinue
    if (-not $curlCommand) {
        throw "curl.exe is required for local health checks."
    }
    & $curlCommand.Source `
        --noproxy "*" `
        --silent `
        --fail `
        --max-time 10 `
        --output NUL `
        $Url 2> $null
    return $LASTEXITCODE -eq 0
}

function Wait-HttpEndpoint {
    param(
        [Parameter(Mandatory)]
        [string]$Url,
        [Parameter(Mandatory)]
        [int]$TimeoutSeconds
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-HttpEndpoint -Url $Url) {
            return $true
        }
        Start-Sleep -Milliseconds 750
    }
    return $false
}

function Get-JsonEndpoint {
    param(
        [Parameter(Mandatory)]
        [string]$Url
    )

    $curlCommand = Get-Command curl.exe -ErrorAction SilentlyContinue
    if (-not $curlCommand) {
        throw "curl.exe is required for local health checks."
    }
    $responseLines = & $curlCommand.Source `
        --noproxy "*" `
        --silent `
        --show-error `
        --max-time 15 `
        $Url 2> $null
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    try {
        return (($responseLines -join "`n") | ConvertFrom-Json)
    }
    catch {
        return $null
    }
}

function Add-LocalhostToNoProxy {
    foreach ($variableName in @("NO_PROXY", "no_proxy")) {
        $currentValue = [Environment]::GetEnvironmentVariable($variableName, "Process")
        $entries = @(
            $currentValue -split "," |
                ForEach-Object { $_.Trim() } |
                Where-Object { $_ }
        )
        foreach ($hostName in @("localhost", "127.0.0.1")) {
            if ($entries -notcontains $hostName) {
                $entries += $hostName
            }
        }
        [Environment]::SetEnvironmentVariable(
            $variableName,
            ($entries -join ","),
            "Process"
        )
    }
}

function Get-DotEnvValue {
    param(
        [Parameter(Mandatory)]
        [string]$Name
    )

    $prefix = "$Name="
    $line = Get-Content -LiteralPath $environmentFile |
        Where-Object {
            $trimmed = $_.Trim()
            $trimmed -and -not $trimmed.StartsWith("#") -and $trimmed.StartsWith($prefix)
        } |
        Select-Object -Last 1
    if (-not $line) {
        return ""
    }
    return $line.Trim().Substring($prefix.Length).Trim().Trim('"').Trim("'")
}

Set-Location -LiteralPath $projectRoot

if (-not (Test-Path -LiteralPath $environmentFile)) {
    Copy-Item -LiteralPath $environmentExample -Destination $environmentFile
    throw "Created .env. Fill in the model key, base URL, model name, and API_ACCESS_KEY, then run .\start.ps1 again."
}

$requiredSettings = @(
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "CHAT_MODEL",
    "API_ACCESS_KEY"
)
$missingSettings = @(
    $requiredSettings |
        Where-Object { -not (Get-DotEnvValue -Name $_) }
)
if ($missingSettings.Count -gt 0) {
    throw "Complete these .env settings first: $($missingSettings -join ', '). Their values are never printed or uploaded."
}

$apiPortText = Get-DotEnvValue -Name "API_PORT"
if (-not $apiPortText) {
    $apiPortText = "8000"
}
$apiPort = 0
if (
    -not [int]::TryParse($apiPortText, [ref]$apiPort) -or
    $apiPort -lt 1 -or
    $apiPort -gt 65535
) {
    throw "API_PORT in .env must be an integer from 1 to 65535."
}
$appUrl = "http://127.0.0.1:$apiPort"
$liveUrl = "$appUrl/health/live"
$readyUrl = "$appUrl/health/ready"
$capabilitiesUrl = "$appUrl/api/v1/capabilities"

Add-LocalhostToNoProxy

if (-not (Test-Path -LiteralPath $venvPython)) {
    $systemPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $systemPython) {
        throw "Python was not found. Install Python 3.10-3.14 and add the python command to PATH."
    }

    & $systemPython.Source -c "import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 15) else 1)"
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.10-3.14 is required to create the virtual environment."
    }

    Write-Host "[1/4] First run: creating the virtual environment..." -ForegroundColor Cyan
    & $systemPython.Source -m venv $venvDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "The virtual environment could not be created."
    }
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "pip could not be upgraded in the virtual environment."
    }
    & $venvPython -m pip install -e ".[dev,mcp]"
    if ($LASTEXITCODE -ne 0) {
        throw "Project dependencies could not be installed."
    }
}

if (-not (Test-Path -LiteralPath $apiEntrypoint)) {
    Write-Host "[1/4] Installing the project entry point..." -ForegroundColor Cyan
    & $venvPython -m pip install -e ".[dev,mcp]"
    if ($LASTEXITCODE -ne 0) {
        throw "The project entry point could not be installed."
    }
}

if (-not $SkipDocker) {
    $dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCommand) {
        throw "Docker was not found. Install Docker Desktop, or use -SkipDocker with an existing Qdrant instance."
    }

    & $dockerCommand.Source info *> $null
    if ($LASTEXITCODE -ne 0) {
        $dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        if (-not (Test-Path -LiteralPath $dockerDesktop)) {
            throw "Docker Desktop is not ready and was not found in its default location. Start it manually and retry."
        }
        Write-Host "[2/4] Starting Docker Desktop..." -ForegroundColor Cyan
        Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
        $dockerDeadline = [DateTime]::UtcNow.AddSeconds(120)
        do {
            Start-Sleep -Seconds 2
            & $dockerCommand.Source info *> $null
            $dockerReady = $LASTEXITCODE -eq 0
        } while (-not $dockerReady -and [DateTime]::UtcNow -lt $dockerDeadline)
        if (-not $dockerReady) {
            throw "Docker Desktop did not become ready within 120 seconds."
        }
    }

    & $dockerCommand.Source compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "The Docker Compose plugin is not installed."
    }

    Write-Host "[2/4] Starting Qdrant..." -ForegroundColor Cyan
    & $dockerCommand.Source compose up -d qdrant
    if ($LASTEXITCODE -ne 0) {
        throw "The Qdrant container failed to start."
    }
    if (-not (Wait-HttpEndpoint -Url $qdrantHealthUrl -TimeoutSeconds 45)) {
        throw "Qdrant did not become ready within 45 seconds. Run: docker compose logs qdrant"
    }
}

$existingListener = Get-NetTCPConnection `
    -LocalPort $apiPort `
    -State Listen `
    -ErrorAction SilentlyContinue |
    Select-Object -First 1

if ($existingListener) {
    $liveResponse = Get-JsonEndpoint -Url $liveUrl
    $capabilitiesResponse = Get-JsonEndpoint -Url $capabilitiesUrl
    $isRagAgent = $false
    try {
        $isRagAgent = (
            $liveResponse.status -eq "ok" -and
            $liveResponse.version -and
            $capabilitiesResponse.sources.managed_uploads_only -eq $true
        )
    }
    catch {
        $isRagAgent = $false
    }
    if (-not $isRagAgent) {
        throw "Port $apiPort is occupied by process $($existingListener.OwningProcess), which is not this RAG Agent. Stop it or change API_PORT."
    }
    Write-Host "[3/4] The RAG API is already running; reusing it." -ForegroundColor Green
}
else {
    New-Item -ItemType Directory -Path $storageDirectory -Force | Out-Null

    Write-Host "[3/4] Starting the RAG API in the background..." -ForegroundColor Cyan
    Start-Process `
        -FilePath $apiEntrypoint `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog | Out-Null
}

Write-Host "[4/4] Waiting for the API and checking its stores..." -ForegroundColor Cyan
if (-not (Wait-HttpEndpoint -Url $liveUrl -TimeoutSeconds 120)) {
    if (Test-Path -LiteralPath $stderrLog) {
        Write-Host "`nRecent API log output:" -ForegroundColor Yellow
        Get-Content -LiteralPath $stderrLog -Tail 30
    }
    throw "The API did not start within 120 seconds. Full log: $stderrLog"
}

$startupState = "ready"
if (-not (Test-HttpEndpoint -Url $readyUrl)) {
    $healthResponse = Get-JsonEndpoint -Url $readyUrl
    $sqliteReady = $false
    $qdrantDetail = ""
    try {
        $sqliteReady = $healthResponse.dependencies.sqlite.ready -eq $true
        $qdrantDetail = [string]$healthResponse.dependencies.qdrant.detail
    }
    catch {
        $sqliteReady = $false
    }

    if ($sqliteReady -and $qdrantDetail -match "(?i)collection .+ is missing") {
        $startupState = "running and waiting for its first document"
        Write-Host "The knowledge collection is empty. Upload or ingest a document in the Web UI." -ForegroundColor Yellow
    }
    else {
        if (Test-Path -LiteralPath $stderrLog) {
            Write-Host "`nRecent API log output:" -ForegroundColor Yellow
            Get-Content -LiteralPath $stderrLog -Tail 30
        }
        throw "The API started, but a required store is unavailable. Full log: $stderrLog"
    }
}

$apiListener = Get-NetTCPConnection `
    -LocalPort $apiPort `
    -State Listen `
    -ErrorAction Stop |
    Select-Object -First 1
Set-Content -LiteralPath $pidFile -Value ([string]$apiListener.OwningProcess) -Encoding Ascii

Write-Host ""
Write-Host "Adaptive RAG is ${startupState}:" -ForegroundColor Green
Write-Host "  Web UI  $appUrl"
Write-Host "  API docs $appUrl/docs"
Write-Host "  Log      $stderrLog"

if (-not $NoBrowser) {
    Start-Process $appUrl
}
