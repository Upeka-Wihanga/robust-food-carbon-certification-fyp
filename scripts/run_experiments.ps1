param(
    [Parameter(Mandatory)][ValidateSet('stage18', 'stage22', 'stage24')][string] $Stage,
    [string] $Stage18Run,
    [switch] $Repaired
)

. (Join-Path $PSScriptRoot 'windows_common.ps1')
$Tools = Join-Path $HistoricalRoot 'scripts'
$Runs = (New-Item -ItemType Directory -Force (Join-Path $HistoricalRoot 'results')).FullName
if ($Stage -eq 'stage22') {
    if (-not $Stage18Run) { throw 'Pass the output directory from Stage 18 with -Stage18Run.' }
    if ($Repaired) { throw 'Supply a repaired Stage 18 run instead of using -Repaired for Stage 22.' }
    $Stage18Run = (Resolve-Path -LiteralPath $Stage18Run).Path
    if (-not (Get-ChildItem -LiteralPath (Join-Path $Stage18Run 'generated') -Filter 'Stage18_2_*_Action_Results.csv')) {
        throw 'Stage 18 action results are missing.'
    }
    Invoke-ProjectPython @('-u', (Join-Path $Tools 'run_frontier.py'), $Stage18Run)
    return
}

$BundleName = if ($Stage -eq 'stage18') { 'Stage18_Portable_Reproduction' } else { 'Stage24_Portable_Reproduction' }
$Bundle = Join-Path $HistoricalRoot "evidence/frozen/$Stage/portable/$BundleName"
$Run = Join-Path $Runs "$Stage.$([Guid]::NewGuid().ToString('N'))"
$Prepare = if ($Stage -eq 'stage24') { 'prepare_windows_stage24.py' } else { 'prepare_run.py' }
Invoke-ProjectPython @((Join-Path $Tools $Prepare), $Bundle, $Run)
if ($Repaired) {
    $RepairArgs = @((Join-Path $Tools 'apply_worktree_repairs.py'), $Run)
    if ($Stage -eq 'stage24') { $RepairArgs += '--verified-archive-driver' }
    Invoke-ProjectPython $RepairArgs
}
Write-Output "Run directory: $Run"
Push-Location -LiteralPath $Run
try {
    Invoke-ProjectPython @('-u', 'reproduce.py') | Tee-Object 'reproduction.log'
    if ($Stage -eq 'stage18') {
        Invoke-ProjectPython @('-u', 'scripts/stage18_5_dependence_bootstrap.py') | Tee-Object 'bootstrap.log'
    } else {
        Invoke-ProjectPython @('-u', 'scripts/stage24_secondary_saturation_mp.py') | Tee-Object 'secondary.log'
        Invoke-ProjectPython @('-u', 'scripts/stage24_secondary_analyze.py') | Tee-Object 'secondary.log' -Append
    }
} finally {
    Pop-Location
}
