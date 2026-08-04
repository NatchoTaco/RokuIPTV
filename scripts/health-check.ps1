param(
    [string]$ApiBaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"

$healthUrl = "$ApiBaseUrl/api/v1/health"
$readinessUrl = "$ApiBaseUrl/api/v1/readiness"

$health = Invoke-RestMethod -Uri $healthUrl -Method Get
Write-Output "Health: $($health.status)"

try {
    $readiness = Invoke-RestMethod -Uri $readinessUrl -Method Get
    Write-Output "Readiness: $($readiness.status)"
}
catch {
    Write-Error "Readiness check failed. Run database migrations and confirm Redis is reachable."
    exit 1
}

foreach ($checkName in $health.checks.PSObject.Properties.Name) {
    $check = $health.checks.$checkName
    Write-Output "$checkName: $($check.status) - $($check.detail)"
}
