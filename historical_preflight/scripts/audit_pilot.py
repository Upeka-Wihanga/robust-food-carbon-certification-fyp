"""Verify budget accounting and nested certificates in the regenerated Stage 24 pilot."""
import argparse
import csv
from fractions import Fraction
import json
from pathlib import Path

TOL = 1e-10


def direction(lower, upper):
    if upper < -TOL:
        return "A"
    if lower > TOL:
        return "B"
    return "ABSTAIN"


def audit(path):
    seen = set()
    certificates = {"share": 0, "factor": 0}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            key = tuple(row[key] for key in ("dataset", "scenario", "pair_id", "policy",
                                              "budget", "factor_cost_ratio"))
            if key in seen:
                raise ValueError(f"Repeated pilot row: {key}")
            seen.add(key)
            budget = Fraction(row["budget"])
            ratio = Fraction(row["factor_cost_ratio"])
            n = int(row["K"])
            full = min(budget // ratio, n)
            partial = int(full < n and budget > full * ratio)
            assert full == int(row["factors_fully_resolved"]), key
            assert partial == int(row["factor_partial_count"]), key
            assert max(0, 1 - budget / 2) == Fraction(row["share_lambda"]), key
            lo, hi = float(row["baseline_L"]), float(row["baseline_U"])
            initial = direction(lo, hi)
            assert row["baseline_success"] == str(initial != "ABSTAIN"), key
            for arm in certificates:
                lower, upper = float(row[f"{arm}_L"]), float(row[f"{arm}_U"])
                final = direction(lower, upper)
                assert lo - TOL <= lower <= upper <= hi + TOL, key
                assert row[f"{arm}_direction"] == final, key
                assert row[f"{arm}_success"] == str(final != "ABSTAIN"), key
                assert initial == "ABSTAIN" or initial == final, key
                certificates[arm] += final != "ABSTAIN"
    if len(seen) != 83280:
        raise ValueError(f"Expected 83,280 distinct pilot rows, got {len(seen)}")
    return {"rows_checked": len(seen), "certificate_rows": certificates,
            "rows_violating_budget_containment_or_direction": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage24_run", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.stage24_run /
                          "generated/Stage24_Targeted_Acquisition_Pair_Results.csv"), indent=2))


if __name__ == "__main__":
    main()
