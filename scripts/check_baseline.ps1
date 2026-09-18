param(
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $PythonPath) {
    $PythonPath = Join-Path $repoRoot "venv/Scripts/python.exe"
}
$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path

# App imports initialize the database. Override configuration before discovery.
$testEnvironment = @{
    DATABASE_URL = "sqlite:///:memory:"
    OPENAI_API_KEY = "baseline-not-a-real-key"
    OPENAI_BASE_URL = "http://127.0.0.1:9/v1"
    OPENAI_MODEL = "baseline-model"
    OPENAI_TIMEOUT = "1"
    TASK_WORKSPACE_ROOT = (Join-Path $repoRoot "runtime/a0-baseline/workspaces")
}
$previousEnvironment = @{}
foreach ($key in $testEnvironment.Keys) {
    $previousEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
}

Push-Location $repoRoot
try {
    foreach ($key in $testEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($key, $testEnvironment[$key], "Process")
    }

    & $PythonPath -c 'import platform,sys; print(sys.version); print(platform.platform())'
    if ($LASTEXITCODE -ne 0) { throw "Python environment check failed." }

    & $PythonPath -m pip list --format=freeze
    if ($LASTEXITCODE -ne 0) { throw "Dependency inventory failed." }

    & $PythonPath -m pip check
    if ($LASTEXITCODE -ne 0) { throw "Installed dependencies are inconsistent." }

    & $PythonPath -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Unit test baseline failed." }

    & node --version
    if ($LASTEXITCODE -ne 0) { throw "Node.js environment check failed." }

    & node --check vscode-extension/extension.js
    if ($LASTEXITCODE -ne 0) { throw "Extension syntax check failed." }

    Write-Output "Baseline checks passed. No real deployment or VS Code UI test was performed."
}
finally {
    foreach ($key in $previousEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($key, $previousEnvironment[$key], "Process")
    }
    Pop-Location
}
