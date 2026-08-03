param(
    [string]$Python = ".venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"

function Invoke-Check {
    param(
        [string]$Name,
        [string[]]$Arguments
    )

    Write-Host "==> $Name"
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python executable not found: $Python"
}

Invoke-Check "Ruff" @("-m", "ruff", "check", "src", "tests")
Invoke-Check "Tests and coverage" @("-m", "pytest")
Invoke-Check "Dependency consistency" @("-m", "pip", "check")
Invoke-Check "Dependency vulnerability audit" @(
    "-m", "pip_audit", "--cache-dir", ".pip-audit-cache"
)
Invoke-Check "Package build" @(
    "-m", "pip", "wheel", "--no-deps", "--wheel-dir", "dist", "."
)

Write-Host "All verification checks passed."
