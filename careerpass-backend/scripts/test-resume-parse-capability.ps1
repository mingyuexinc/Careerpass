[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"
$artifactRoot = Join-Path $backendRoot "tests\acceptance\s04_resume_parse\delivery-acceptance-results"

function Fail-Check {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host ("FAIL: {0}" -f $Message) -ForegroundColor Red
    exit 20
}

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    Fail-Check "backend virtual environment Python is unavailable: .venv\Scripts\python.exe"
}

New-Item -ItemType Directory -Force -Path $artifactRoot | Out-Null
$env:APP_ENV = "test"
$env:S04_CAPABILITY_ARTIFACT_ROOT = $artifactRoot

Write-Host "Running S-04 resume parse Capability Acceptance for the fixed PDF..."
Push-Location $backendRoot
try {
    & $python -m pytest tests/acceptance/s04_resume_parse/harness/test_s04_resume_parse_capability.py -m capability_acceptance --no-cov -p no:cacheprovider
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
    Write-Host "PASS: S-04 resume parse Capability Acceptance" -ForegroundColor Green
}
else {
    Write-Host "FAIL: inspect report.md and actual.json in the Acceptance Artifact" -ForegroundColor Red
}
exit $exitCode
