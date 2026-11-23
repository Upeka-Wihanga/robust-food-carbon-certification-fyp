param(
    [Parameter(Mandatory)][string] $Stage18Run,
    [Parameter(Mandatory)][string] $Stage22Run,
    [Parameter(Mandatory)][string] $Stage24Run
)

. (Join-Path $PSScriptRoot 'windows_common.ps1')
$Tools = Join-Path $HistoricalRoot 'scripts'
Invoke-ProjectPython @((Join-Path $Tools 'audit_pilot.py'), $Stage24Run)
Invoke-ProjectPython @((Join-Path $Tools 'verify_results.py'), $Stage18Run, $Stage22Run, $Stage24Run)
