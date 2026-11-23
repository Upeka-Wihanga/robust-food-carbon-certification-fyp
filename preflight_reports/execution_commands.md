# Windows execution commands

Run from the active workspace. Supply an existing native Windows CPython 3.12 to setup when the Python launcher is unavailable.

```powershell
Set-Location -LiteralPath 'D:\Final Year Project'
pwsh -NoProfile -File .\scripts\setup_windows.ps1
pwsh -NoProfile -File .\scripts\run_tests.ps1
pwsh -NoProfile -File .\scripts\run_preflight.ps1
```

For a fresh clone, obtain the frozen packet files recorded in the manifest and place them in `evidence/frozen/`, or pass their path to `run_preflight.ps1 -EvidenceDir`. Place the three raw files at the recorded `data/raw/` locations. The scripts use the project's interpreter and keep temporary files and caches local.

```powershell
pwsh -NoProfile -File .\scripts\run_experiments.ps1 -Stage stage18
pwsh -NoProfile -File .\scripts\run_experiments.ps1 -Stage stage22 -Stage18Run '<printed Stage 18 directory>'
pwsh -NoProfile -File .\scripts\run_experiments.ps1 -Stage stage24
pwsh -NoProfile -File .\scripts\verify_reproducibility.ps1 -Stage18Run '<Stage 18 directory>' -Stage22Run '<Stage 22 directory>' -Stage24Run '<Stage 24 directory>'
```

The preflight used `.venv\Scripts\python.exe` to run `historical_preflight/scripts/import_evidence.py`, `audit_datasets.py`, `run_archived_oracle.py`, `profile_oracle.py`, the archived `reproduce.py` entry points, the Stage 18 bootstrap script, the Stage 20/22 frontier runner, Stage 24 secondary scripts, `audit_pilot.py`, and `verify_results.py`. An unmodified Stage 24 run recorded the unsupported fork failure. Fresh verified working copies then ran the portable implementation.

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
& .\.venv\Scripts\python.exe scripts/stage26/freeze_manifest.py --check-only
& .\.venv\Scripts\python.exe scripts/stage26/run_frozen_evaluation.py --smoke
```

The full Stage 26 entry points are `freeze_manifest.py`, `run_frozen_evaluation.py --pass-id pass1` and `--pass-id pass2`, `verify_reproducibility.py`, and `bootstrap_and_finalize.py`. The audit did not execute the full study. Review the open prior, method, and verification items before using these research drivers for outcome evaluation. [Acquisition audit](06_SEQUENTIAL_ACQUISITION_AUDIT.md)
