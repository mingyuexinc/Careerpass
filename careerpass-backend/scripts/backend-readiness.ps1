[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-GateResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    Write-Output ("{0}={1}" -f $Name, $Value)
}

function Invoke-NativeCheck {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    try {
        $output = & $Executable @Arguments 2>&1
        return [PSCustomObject]@{
            ExitCode = $LASTEXITCODE
            Output = @($output)
            Denied = $false
        }
    }
    catch [System.UnauthorizedAccessException] {
        return [PSCustomObject]@{
            ExitCode = 11
            Output = @()
            Denied = $true
        }
    }
    catch {
        if ($_.Exception.Message -match "denied|拒绝访问|permission") {
            return [PSCustomObject]@{
                ExitCode = 11
                Output = @()
                Denied = $true
            }
        }
        throw
    }
}

$backendRoot = Split-Path -Parent $PSScriptRoot
$troubleshootingPath = Join-Path $backendRoot "docs\development\backend-troubleshooting.md"
$composePath = Join-Path $backendRoot "docker-compose.integration.yml"

if (-not (Test-Path -LiteralPath $troubleshootingPath -PathType Leaf)) {
    Write-GateResult -Name "status" -Value "governance_file_missing"
    exit 20
}

$null = Get-Content -LiteralPath $troubleshootingPath -Raw -Encoding UTF8
Write-GateResult -Name "troubleshooting_loaded" -Value "true"

$dockerCandidates = @()
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if ($null -ne $dockerCommand -and -not [string]::IsNullOrWhiteSpace($dockerCommand.Source)) {
    $dockerCandidates += [PSCustomObject]@{
        Path = $dockerCommand.Source
        Source = "PATH"
    }
}

if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    $dockerCandidates += [PSCustomObject]@{
        Path = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin\docker.exe"
        Source = "LOCALAPPDATA"
    }
}

if (-not [string]::IsNullOrWhiteSpace($env:ProgramFiles)) {
    $dockerCandidates += [PSCustomObject]@{
        Path = Join-Path $env:ProgramFiles "Docker\Docker\resources\bin\docker.exe"
        Source = "PROGRAMFILES"
    }
}

$dockerExecutable = $null
$dockerSource = $null
foreach ($candidate in $dockerCandidates) {
    if (Test-Path -LiteralPath $candidate.Path -PathType Leaf) {
        $dockerExecutable = (Resolve-Path -LiteralPath $candidate.Path).Path
        $dockerSource = $candidate.Source
        break
    }
}

if ($null -eq $dockerExecutable) {
    Write-GateResult -Name "docker_cli_discovered" -Value "false"
    Write-GateResult -Name "status" -Value "cli_not_found"
    Write-GateResult -Name "conclusion_boundary" -Value "engine_status_unverified"
    exit 10
}

Write-GateResult -Name "docker_cli_discovered" -Value "true"
Write-GateResult -Name "docker_cli_source" -Value $dockerSource
Write-GateResult -Name "docker_cli_invocation" -Value "absolute_path"

$clientResult = Invoke-NativeCheck -Executable $dockerExecutable -Arguments @("--version")
if ($clientResult.Denied) {
    Write-GateResult -Name "status" -Value "execution_denied"
    Write-GateResult -Name "conclusion_boundary" -Value "engine_status_unverified"
    Write-GateResult -Name "next_action" -Value "rerun_with_escalated_permissions"
    exit 11
}
if ($clientResult.ExitCode -ne 0) {
    Write-GateResult -Name "status" -Value "cli_execution_failed"
    Write-GateResult -Name "conclusion_boundary" -Value "engine_status_unverified"
    exit 12
}
Write-GateResult -Name "docker_client" -Value "available"

$composeResult = Invoke-NativeCheck -Executable $dockerExecutable -Arguments @("compose", "version", "--short")
if ($composeResult.Denied) {
    Write-GateResult -Name "status" -Value "execution_denied"
    Write-GateResult -Name "conclusion_boundary" -Value "engine_status_unverified"
    Write-GateResult -Name "next_action" -Value "rerun_with_escalated_permissions"
    exit 11
}
if ($composeResult.ExitCode -ne 0) {
    Write-GateResult -Name "status" -Value "compose_unavailable"
    exit 13
}
Write-GateResult -Name "docker_compose" -Value "available"

$engineResult = Invoke-NativeCheck -Executable $dockerExecutable -Arguments @("version", "--format", "{{.Server.Version}}")
if ($engineResult.Denied) {
    Write-GateResult -Name "status" -Value "execution_denied"
    Write-GateResult -Name "conclusion_boundary" -Value "engine_status_unverified"
    Write-GateResult -Name "next_action" -Value "rerun_with_escalated_permissions"
    exit 11
}
if ($engineResult.ExitCode -ne 0) {
    Write-GateResult -Name "docker_engine" -Value "unreachable"
    Write-GateResult -Name "status" -Value "engine_unreachable"
    exit 12
}
Write-GateResult -Name "docker_engine" -Value "available"

$contextResult = Invoke-NativeCheck -Executable $dockerExecutable -Arguments @("context", "show")
if ($contextResult.ExitCode -ne 0) {
    Write-GateResult -Name "status" -Value "context_unavailable"
    exit 12
}
Write-GateResult -Name "docker_context" -Value (($contextResult.Output | Select-Object -First 1).ToString().Trim())

if (-not (Test-Path -LiteralPath $composePath -PathType Leaf)) {
    Write-GateResult -Name "status" -Value "compose_file_missing"
    exit 13
}

$configResult = Invoke-NativeCheck -Executable $dockerExecutable -Arguments @("compose", "-f", $composePath, "config", "--quiet")
if ($configResult.Denied) {
    Write-GateResult -Name "status" -Value "execution_denied"
    Write-GateResult -Name "next_action" -Value "rerun_with_escalated_permissions"
    exit 11
}
if ($configResult.ExitCode -ne 0) {
    Write-GateResult -Name "status" -Value "compose_config_invalid"
    exit 13
}

Write-GateResult -Name "compose_config" -Value "valid"
Write-GateResult -Name "status" -Value "ready"
exit 0
