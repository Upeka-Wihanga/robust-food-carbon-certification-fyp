# End-to-end test results

- **Windows baseline:** 107 passed and 3 failed. One test assumed Python's pre-3.12 uncompensated float sum. Windows checkout translated the byte-verified synthetic CSV and failed two ingestion tests.
- **Windows corrected tests:** The active library, independent LP comparator, archived mathematical harness, data/model checks, geometry regressions, and Stage 26 policy tests passed after the fixes. See the [test receipt](test_results.txt) for the final counts.
- **Stage 18 integration:** The archived bundle completed and compared its metrics. Independent node-bootstrap regeneration and the repaired-QUID variant completed.
- **Stage 20/22 integration:** Windows rebuilt the supported archived Stage 20 point groups and Stage 22 surface, budget, and statistics; the comparison passed.
- **Stage 24 integration:** Windows rebuilt midpoint correction, six targeted scenarios, exact-subset audits, primary bootstrap, and the secondary ±1 pp saturation regime. The final comparison passed after the initial unmodified runner failed on Windows `fork`. The separate rounding-repaired run also matched all compared outputs.
- **Stage 26 headless workflow:** The empirical smoke rebuilt the cohort, applied simulated observations, tracked budget, updated certificates, and replayed 28 trajectories. The full first and second held-out passes, frontend build, API integration, and user acceptance workflow were not executed. The active tree has no FastAPI or React entry point.

[Execution commands](execution_commands.md) · [Dataset audit](04_DATASET_AUDIT.md)
