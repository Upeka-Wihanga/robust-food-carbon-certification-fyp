param([string] $BasePython)

. (Join-Path $PSScriptRoot 'windows_common.ps1')
if (-not (Test-Path -LiteralPath $ProjectPython -PathType Leaf)) {
    if ($BasePython) {
        & $BasePython -m venv --without-pip (Join-Path $ProjectRoot '.venv')
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -m venv --without-pip (Join-Path $ProjectRoot '.venv')
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv --without-pip (Join-Path $ProjectRoot '.venv')
    } else {
        throw 'An existing Windows Python 3.12 installation is required. Pass its executable with -BasePython.'
    }
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the project virtual environment.' }
}
Invoke-ProjectPython @('-c', 'import sys; assert sys.version_info[:2] == (3, 12) and sys.prefix != sys.base_prefix; print(sys.executable)')
& $ProjectPython -m pip --version
if ($LASTEXITCODE -ne 0) { Invoke-ProjectPython @('-m', 'ensurepip', '--upgrade') }
Invoke-ProjectPython @('-m', 'pip', 'install', '--disable-pip-version-check', '-r', (Join-Path $ProjectRoot 'requirements-windows.lock'))
Invoke-ProjectPython @('-m', 'pip', 'check')
