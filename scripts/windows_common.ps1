$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ProjectPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$HistoricalRoot = Join-Path $ProjectRoot 'historical_preflight'
$ProjectCache = Join-Path $ProjectRoot '.cache'
$ProjectTemp = (New-Item -ItemType Directory -Force (Join-Path $ProjectCache 'tmp')).FullName
$env:TEMP = $ProjectTemp
$env:TMP = $ProjectTemp
$env:PYTHONUTF8 = '1'
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONPATH = Join-Path $ProjectRoot 'src'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:PIP_CACHE_DIR = Join-Path $ProjectCache 'pip'
$env:PIP_REQUIRE_VIRTUALENV = 'true'

function Invoke-ProjectPython {
    param([Parameter(Mandatory)][string[]] $Arguments)
    if (-not (Test-Path -LiteralPath $ProjectPython -PathType Leaf)) {
        throw 'Project Python is missing. Run scripts/setup_windows.ps1 first.'
    }
    & $ProjectPython @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python exited with code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}
