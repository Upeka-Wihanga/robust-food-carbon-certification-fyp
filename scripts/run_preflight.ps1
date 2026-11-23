param([string] $EvidenceDir)

. (Join-Path $PSScriptRoot 'windows_common.ps1')
if (-not $EvidenceDir) { $EvidenceDir = Join-Path $ProjectRoot 'evidence\frozen' }
$EvidenceDir = (Resolve-Path -LiteralPath $EvidenceDir).Path
Push-Location -LiteralPath $ProjectRoot
try {
    & (Join-Path $PSScriptRoot 'run_tests.ps1')
    Invoke-ProjectPython @('historical_preflight/scripts/import_evidence.py', $EvidenceDir)
    Invoke-ProjectPython @('historical_preflight/scripts/audit_datasets.py')
    Invoke-ProjectPython @('historical_preflight/scripts/run_archived_oracle.py')
    Invoke-ProjectPython @('scripts/stage26/freeze_manifest.py', '--check-only')
    Invoke-ProjectPython @('scripts/stage26/run_frozen_evaluation.py', '--smoke')
} finally {
    Pop-Location
}
