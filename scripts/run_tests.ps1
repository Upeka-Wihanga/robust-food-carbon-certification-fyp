. (Join-Path $PSScriptRoot 'windows_common.ps1')
Push-Location -LiteralPath $ProjectRoot
try {
    Invoke-ProjectPython @('-m', 'pytest', '-ra', '-s', 'tests')
    Invoke-ProjectPython @('-m', 'pytest', '-ra', 'historical_preflight/tests', '-o', 'pythonpath=historical_preflight')
} finally {
    Pop-Location
}
