# Sequential acquisition audit

The active pathway reconstructs Guan61/M2, generates shared factor worlds from seeds 26000–26099, selects one share rank per food on observable order geometry and factor midpoints, and constructs starting uncertainty from the published half-up value. The held-out share is a latent source value. A factor observation in the primary Stage 26 simulation is a seeded draw from its factor interval and is shared across matching keys. A policy receives the current observable state and budget. It selects an action before the execution layer reveals a value and updates the selected interval. After every update the oracle recomputes the certificate.

The source includes B0 share-only, B1 factor-only, B2 fixed staged, B3 geometric width, B4 one-step certification value, P two-step rollout, and H hindsight. The hindsight code is an outcome-aware reference. Fixed unit costs and stop rules are checked in the state and policy tests. Cache keys use observable state. LOCO construction excludes held-out recipe nodes from the fold comparator selection. Earlier pilots used the same cohort; the fold separation applies to Stage 26 comparison and tuning.

The Windows smoke used one empirical pair and one simulated world across all four starting regimes and all seven arms. It replayed 28 identical trajectories, including 10 acquisitions per pass. Four trajectories began with a share action and three began with a factor action. There were zero containment, direction, budget, repeated-action, or post-certification violations. The smoke also tests the Windows process initializer.

## Full-run status

The archived manifest matched all 10 recorded original code digests in the preserved source snapshot. Its sole first-pass file is a gzip stream ending before its end marker. It exposes 317,132 readable rows against 621,600 expected and has no completed first-pass safety/coverage manifest or second pass. The Windows code records a new receipt for subsequent reproducibility checks. The partial stream is preserved as evidence of interruption.

The policy's nine quadrature nodes currently use a uniform prior over the observable share interval. The supplied protocol describes training-fold share distributions for the rollout expectation. Resolve the permitted share prior before a prospective run. No alternate cost/noise study, measured-factor integration, or complete standalone observation-log replay was verified. H3 and prospective switching remain untested. [Statistical audit](07_STATISTICAL_VALIDITY.md)
