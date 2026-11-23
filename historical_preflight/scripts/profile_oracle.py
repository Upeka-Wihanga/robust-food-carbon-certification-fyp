"""Measure the frozen interval oracle on deterministic synthetic CPU cases."""
from pathlib import Path
import json
import sys
from time import perf_counter
import tracemalloc

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evidence/frozen/stage18/portable/"
                       "Stage18_Portable_Reproduction/scripts"))
import corrected_oracle as oracle


def profile(n, repeats=30):
    ca = list(range(n))
    cb = list(range(n // 2, n + n // 2))
    _, index, factors = oracle.pair_union(
        ca, [1 + c / n for c in ca], cb, [1 + c / n for c in cb]
    )
    rank = n // 2
    lower, upper = 0.2 / rank, 0.8 / rank

    def evaluate():
        a = oracle.interval_vertices(n, rank, lower, upper)
        b = oracle.interval_vertices(n, rank, lower, upper)
        aa = oracle.aggregate_vertices(a, ca, index)
        bb = oracle.aggregate_vertices(b, cb, index)
        bounds = oracle.robust_bounds_from_arrays(aa, bb, factors)
        return len(a), len(b), bounds

    evaluate()
    started = perf_counter()
    for _ in range(repeats):
        na, nb, bounds = evaluate()
    seconds = perf_counter() - started
    tracemalloc.start()
    try:
        evaluate()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return {
        "ingredients_per_food": n, "shared_codes": n // 2,
        "geometry_builds_per_comparison": 2, "vertices_per_food": [na, nb],
        "closed_form_box_supports_per_comparison": 2 * na * nb,
        "optimizer_calls_per_comparison": 0, "bounds": bounds, "repeats": repeats,
        "mean_wall_ms_per_comparison": seconds * 1000 / repeats,
        "traced_peak_allocation_bytes": peak,
    }


if __name__ == "__main__":
    print(json.dumps([profile(n) for n in (2, 4, 8, 12, 16)], indent=2))
