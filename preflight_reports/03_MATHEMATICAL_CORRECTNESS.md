# Mathematical correctness

For each food the active oracle forms the ordered unit simplex intersected by one selected-rank slab. It uses feasible simplex vertices and all original-edge crossings of the slab boundaries. Duplicate stored rows are removed by exact equality. Multiple disconnected branches of a disclosure are evaluated as a union of component pairs. Simultaneously disclosed ranks require a general polytope intersection and corresponding independent tests.

For fixed vertex pairs, ingredients are aggregated by shared commodity before computing coefficients of A minus B. The sign of each coefficient determines the factor interval endpoint for the minimum and maximum. Across vertex pairs the minimum lower and maximum upper endpoint define the raw bounds. The sign threshold is the larger of the requested engineering tolerance and a floating-point margin scaled by factor magnitude and input width. Near-zero comparisons abstain. This is an engineering margin and its validation covers the tested scales and inputs.

## Independent checks

- The active SciPy HiGHS comparator separately enumerates factor-box corners and solves the two food composition LPs jointly. Across 100 seeded cases, there were zero direction mismatches. The largest lower- and upper-endpoint errors were about 1.78e−15 and 2.22e−15, respectively.
- The recovered Stage 16 comparator ran 220 cases with zero direction mismatches and maximum endpoint errors of 1.33e−15 and 1.78e−15. This is separate evidence for the archived implementation.
- Regressions exercise the historical four-corner failure, repeated factor identities, narrow slabs, infeasible bounds, reflexive comparison, and monotone certificate preservation. The two-ingredient new counterexample uses exact rational arithmetic for its endpoint expectations.

## Reproduced false certificates

1. For identical factors (10, 0), A had rank 1 in [0.6, 0.6 + 7e−13] and B had rank 1 at 0.6 + 3e−13. The former engine returned both bounds near −3e−12 and certified A lower. The true upper bound is near +4e−12. The repaired result abstains.
2. Six equal shares of one commodity versus one serving composed entirely of the same commodity has D = 0. With the factor fixed at 1e16, the former calculation returned D = −1.1102230246251565. Unit mass now cancels exactly for a sole common factor. For distinct large-valued keys, the shared sign margin also reaches both the disclosure adapter and Stage 26 policy scoring.
3. A clipped first-rank slab entirely below 0.5 for two ingredients now raises infeasibility even within the former geometric tolerance.

The factor is deliberately oversized in the second regression to expose floating-point sensitivity. The 2–16 ingredient profile used deterministic synthetic CPU cases, 2 geometry builds and zero LP calls per comparison. For the active oracle, observed means ranged from about 1.42 to 31.91 ms and Python-traced peaks ranged from 5,400 to 7,443,784 bytes. Active support evaluations ranged from 8 to 18,432 per comparison. Archived means ranged from about 0.84 to 94.86 ms, with Python-traced peaks of 3,789 to 3,769,885 bytes. These diagnostic runs used the same ingredient-count range with different factor and boundary settings. The active vectorized vertex-pair tensor can be memory intensive at large rank counts.

[Counterexample and repair](../tests/regression/test_numerical_false_certificates.py) · [Issue log](09_ISSUES_AND_FIXES.md)
