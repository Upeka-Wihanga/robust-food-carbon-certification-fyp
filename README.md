# Robust Food-Carbon Certification under Incomplete Ingredient Disclosure

Information Sufficiency and Observation-Aware Sequential Acquisition · FYP 2026/27

The engine compares modeled upstream ingredient-production GHG per unit of ingredient mass. It certifies a direction only when it can establish a strict sign across the declared ordered compositions and shared commodity-factor intervals. Otherwise it abstains. Processing, cooking, packaging, transport, retail, waste and supplier-specific emissions are outside this model.

## What runs today

- The active Python library covers complete ordered geometry with one disclosed rank per food, disconnected rounding preimages, shared factors, and strict-sign classification.
- The recovered historical runners reproduce the Stage 18, 20, 22, and 24 pilot evidence from the supplied raw and frozen derived inputs.
- Stage 26 code includes Guan61/M2 construction, rounded starting states, observation-driven share and factor updates, all seven policy/ceiling arms, and a deterministic empirical smoke test. Completion of the full held-out study, multi-rank disclosures, and the API/web workflow are tracked in the [readiness report](preflight_reports/10_FINAL_READINESS_REPORT.md).

## Windows setup

Use an existing native Windows CPython 3.12, PowerShell 7, and Git. The workspace used for this audit is `D:\Final Year Project`. For a fresh copy, use a writable local folder. Supply `-BasePython 'C:\path\to\python.exe'` if the launcher or Python alias does not point to a working 3.12 interpreter. This workstation used the Python already bundled with Codex. Installation and pip's cache stay inside the project.

```powershell
Set-Location -LiteralPath 'D:\Final Year Project'
pwsh -NoProfile -File .\scripts\setup_windows.ps1
pwsh -NoProfile -File .\scripts\run_tests.ps1
```

Put the three raw files under `data/raw/` using the exact filenames in [the SHA-256 source manifest](data/manifests/source_files.json). Place the original handoff ZIP, seven review packet ZIPs, proposal and two Stage 26 documents in `evidence/frozen/`, or supply their directory with `-EvidenceDir`. The file list and exact hashes are recorded in [the reproducibility manifest](preflight_reports/reproducibility_manifest.json).

```powershell
pwsh -NoProfile -File .\scripts\run_preflight.ps1
pwsh -NoProfile -File .\scripts\run_experiments.ps1 -Stage stage18
pwsh -NoProfile -File .\scripts\run_experiments.ps1 -Stage stage22 -Stage18Run '<printed Stage 18 directory>'
pwsh -NoProfile -File .\scripts\run_experiments.ps1 -Stage stage24
pwsh -NoProfile -File .\scripts\verify_reproducibility.ps1 -Stage18Run '<Stage 18 directory>' -Stage22Run '<Stage 22 directory>' -Stage24Run '<Stage 24 directory>'
```

Stage 22's runner also builds the recovered Stage 20 analysis. Each historical run prints a fresh directory under `historical_preflight/results/`. The archived-QUID repair is available as `-Repaired` for Stage 18/24 and applies only to a newly staged copy. See [execution commands](preflight_reports/execution_commands.md) and [test results](preflight_reports/08_END_TO_END_TEST_RESULTS.md).

## Repository layout

- `src/food_carbon_cert/` holds the active data, geometry, certification, disclosure, and Stage 26 code.
- `tests/` holds independent-reference comparisons, unit tests and regressions.
- `historical_preflight/` holds the recovered experiment harness and local results. `scripts/stage26/` holds the recovered sequential study drivers and the frozen reference manifest.
- `research_archive/` holds historical documentation and manifests. `evidence/` holds local source snapshots. Raw datasets, portable evidence packets and generated results are kept local.
- `preflight_reports/` holds the Windows evidence receipts, proposal traceability, and final readiness assessment.

Use small commits that identify a verified behavior change and its evidence. Preserve archived results and record any prospective protocol revision before evaluating performance. Source-derived variability boxes, modeled factor observations, and pilot cost ratios are conditional research scenarios. Stronger generalization requires suitable observations and evaluation.
