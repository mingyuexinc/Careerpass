[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $backendRoot "docker-compose.integration.yml"
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"
$apiBase = if ($env:S03_ACCEPTANCE_API_BASE_URL) { $env:S03_ACCEPTANCE_API_BASE_URL } else { "http://localhost:8080" }
$objectRoot = Join-Path $backendRoot ".careerpass-objects"
$artifactRoot = Join-Path $backendRoot "tests\acceptance\s03_jd_parse\delivery-acceptance-results"

function Fail-Check {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host ("FAIL: {0}" -f $Message) -ForegroundColor Red
    exit 20
}

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    Fail-Check "backend virtual environment Python is unavailable: .venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $composeFile -PathType Leaf)) {
    Fail-Check "integration Compose file is unavailable"
}

$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($null -eq $docker) {
    Fail-Check "Docker CLI is unavailable; PostgreSQL, Redis, Dispatcher and Worker cannot be verified"
}

try {
    $running = @(& $docker.Source compose -f $composeFile ps --services --filter status=running 2>&1)
    if ($LASTEXITCODE -ne 0) {
        Fail-Check "integration Compose services cannot be inspected"
    }
    $required = @("postgres", "redis", "backend", "worker", "dispatcher")
    foreach ($service in $required) {
        if ($running -notcontains $service) {
            Fail-Check "integration service is not running: $service"
        }
    }
}
catch {
    Fail-Check "integration Compose check failed"
}

foreach ($path in @("/health/live", "/health/ready")) {
    try {
        $response = Invoke-WebRequest -Uri ($apiBase + $path) -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -ne 200) {
            Fail-Check ("S-03 API health check failed: {0} ({1})" -f $path, $response.StatusCode)
        }
    }
    catch {
        Fail-Check ("S-03 API is unavailable: {0}" -f $path)
    }
}

New-Item -ItemType Directory -Force -Path $objectRoot, $artifactRoot | Out-Null
$env:APP_ENV = "test"
$env:DATABASE_URL = "postgresql+asyncpg://careerpass:careerpass_test_only@localhost:54329/careerpass"
$env:REDIS_URL = "redis://localhost:63790/0"
$env:TEST_DATABASE_URL = $env:DATABASE_URL
$env:TEST_REDIS_URL = $env:REDIS_URL
$env:TEST_OBJECT_STORAGE_ROOT = $objectRoot
$env:S03_ACCEPTANCE_API_BASE_URL = $apiBase
$env:S03_ACCEPTANCE_CONTAINER_JD_ROOT = "/opt/careerpass/s03-jd"
$env:S03_ACCEPTANCE_ARTIFACT_ROOT = $artifactRoot
$env:JWT_SECRET_KEY = "integration-jwt-secret-key-with-at-least-32-characters"

Write-Host "Running S-03 JD parse acceptance for fixed fixtures 001 and 002..."
Push-Location $backendRoot
try {
    & $python -m pytest tests/acceptance/s03_jd_parse/harness/test_s03_jd_parse_acceptance.py -m acceptance
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

$artifact = Get-ChildItem -LiteralPath $artifactRoot -Directory -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($null -ne $artifact) {
    Write-Host ("Acceptance Artifact: {0}" -f $artifact.FullName)
}
if ($exitCode -eq 0) {
    Write-Host "PASS: S-03 JD parse internal capability acceptance" -ForegroundColor Green
}
else {
    Write-Host "FAIL: inspect report.md and actual.json in the Acceptance Artifact" -ForegroundColor Red
}
exit $exitCode
