# Proposal-to-implementation traceability

All 16 pages were reviewed. Source paths beginning with a Python package folder are relative to `src/food_carbon_cert/`. The proposal's applied research question concerns the share precision needed to preserve a strict robust sign and whether observation-aware acquisition improves coverage under a limited budget. The scope is modeled upstream ingredient production only. The matrix below uses the requested verification statuses. The full machine-readable matrix includes evidence, limitations, required work and commits. [Requirements status](requirements_status.csv)

| ID | Proposal | Requirement | Status | Evidence |
| --- | --- | --- | --- | --- |
| SCOPE | §3.2, §11.2, Appendix A · pp. 4, 12, 16 | Certification conditional on upstream production, shared factors and declared sets | PASS | Only production fields used for Guan comparison; environmental scope stated. |
| H1 | §5.3 · p. 5 | Non-trivial coverage under incomplete disclosure and shared factors | PARTIAL | Pilot evidence supports H1 in Guan61 M2; 81/222 for rank-weighted rounded selection. |
| H2 | §5.3 · p. 5 | Diminishing gains near exact selected-share precision | PARTIAL | Guan61 M2 selected-rank curve 26.6% at ±10 pp, 36.0% at ±1 pp, 37.4% exact. |
| H3 | §5.3 · p. 5 | Observation-aware mixed acquisition beats fixed strategies held out | BLOCKED | 28 trajectories replayed. Full archived pass is truncated and H3 is NOT YET TESTED. |
| O1 / D1 | §5.4, §6.1–6.4, §14 · pp. 5–7, 14 | Complete ordered certification, shared factor endpoints and disclosure support | PARTIAL | 100 active and 220 archive LP cases, zero direction disagreements; two strict-sign defects repaired. |
| O2 | §5.4, §9.3 · pp. 5, 10 | Quantify effect of share precision | PASS | Frozen precision tables reproduced for recovered pilot scenarios. |
| O3 | §5.4, §6.2 · pp. 5–6 | Evaluate source and sensitivity factor uncertainty | PASS | dataFIELD variability, Guan minor-factor scenarios and corrected midpoint evidence reproduced. |
| O4 | §5.4 · p. 6 | Selectable rank before hidden shares | PASS | Frozen selection uses factor midpoint and order-only feasible width, with deterministic tie-break. |
| O5 / D2 | §5.4, §6.5, §14 · pp. 6–7, 14 | Observation-aware sequential module | PARTIAL | Choose then reveal, update, recertify and budget tracking verified in exact-reveal mode. |
| O6 | §5.4, §6.6 · pp. 6–7 | Equal-budget baseline comparison with hindsight ceiling | PARTIAL | All arms execute at B=2 in smoke. Stage 24 compares planned pilot refinements. |
| O7 / D5 | §5.4, §6.7, §9.2, §14 · pp. 6–8, 10, 14 | Node-held-out contrasts, node bootstrap, stability | PARTIAL | Historical 5,000-replicate bootstrap reproduced; Stage 26 folds and inference driver exist. |
| O8 | §5.4, §10.3, §11.1 · pp. 6, 11 | Portable prototype, manifests and rerun receipts | PARTIAL | Pinned .venv and runnable Windows headless commands. |
| D3 | §10.1–10.2, §14 · pp. 10–11, 14 | Web and API prototype, abstention/acquisition workflow | NOT IMPLEMENTED | Headless state workflow exists; FastAPI and React/Next.js absent. |
| D4 | §7, §14 · pp. 8, 14 | Provenanced raw ingest, mapping and experiments | PARTIAL | 61/222 Guan cohort exact, original source hashes match; reviewed FCID/dataFIELD linkage. |
| D6 | §14.1 · p. 14 | Dissertation and archived research evidence | PARTIAL | Research archive and preflight evidence preserved. |
| D7 | §14.1, §15 · pp. 14–15 | Publication claim boundary, closest work and later validation plan | PARTIAL | Bounded research framing and prior independent reports available. |
| POC-A | §8 · p. 8 | Robust oracle | PASS | 320 reference cases across versions; zero direction mismatches after active repairs. |
| POC-B | §8 · p. 8 | Rounding/disclosure inverse | PASS | Verified low/high branch, half-up ties, invalid and clipped publications including 0% and 100%. |
| POC-C | §8 · p. 8 | Source-faithful external analysis | PASS | 320 rows, 308 parseable, 61 eligible, eight cuisines, 222 matching pair identities. |
| POC-D | §8 · p. 8 | Selectable ranks without hidden input | PASS | Deterministic selection verified with observable inputs for tested policies. |
| POC-E | §8 · pp. 8–9 | Node-aware dependence and influence | PASS | Matched node weights, 5,000 replicates and leave-one-out evidence reproduced. |
| POC-F | §8 · p. 9 | Cost-sensitive targeted pilot; small-subset exact checks | PASS | Regenerated 83,280 targeted rows plus 644 exact-subset rows. Archived midpoint corrections verified. |
| POC-G | §8 · p. 9 | Portable frozen pilot replay | PARTIAL | All recovered core components replayed; raw and derived freeze checks passed. |
| SUCCESS-1 | §14.2 · p. 14 | Correctness and all mathematical tests | PASS | Two new minimal false-certificate cases repaired; zero remaining failing cases observed. |
| SUCCESS-2 | §14.2 · p. 14 | Clean regeneration of final held-out metrics | BLOCKED | Archived pass1 gzip truncated; no pass2 or complete metrics. |
| SUCCESS-3 | §14.2 · p. 14 | Complete research user workflow | PARTIAL | Exact observation update and recertify verified. |
| SUCCESS-4 | §14.2 · p. 14 | Valid held-out research results | BLOCKED | Pooled switching denominator corrected; full held-out results unavailable. |
| SUCCESS-5 | §14.2 · p. 14 | Bounded claims and simulated data labels | PASS | Reporting confines conclusions to modeled upstream GHG and identifies simulated worlds and costs. |
| ABLATIONS | §9.3 · p. 10 | Prespecified factor/disclosure, policy, cost/noise and cohort sensitivity | PARTIAL | Rounded/bounded/exact regimes, fixed/box variability, Guan scenarios and cost ratios present. |

Use [execution commands](execution_commands.md) to rerun the mapped checks. The evidence package records source-composition weights, latent simulated factor worlds, policy decisions, and historical pilot refinements under their respective methods. The final API/UI, external commercial validity, and held-out experimental evidence remain separate deliverables.
