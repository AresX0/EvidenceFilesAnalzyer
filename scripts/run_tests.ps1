# Run tests using the project venv
$venv = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-Not (Test-Path $venv)) {
    Write-Error "vENV python not found at $venv. Activate or create the venv as documented in COPILOT_INSTRUCTIONS.MD"
    exit 1
}
& $venv -m pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output "All tests passed"