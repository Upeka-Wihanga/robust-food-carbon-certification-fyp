"""Compare freshly regenerated outputs against frozen result packets."""
import argparse
from collections import defaultdict
import csv
import json
from math import isclose
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "evidence/frozen"


def data(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def equal(a, b):
    if a == b:
        return True
    try:
        return isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12)
    except ValueError:
        return False


def compare_csv(frozen, fresh):
    if frozen.read_bytes() == fresh.read_bytes():
        return "byte-identical"
    old, new = data(frozen), data(fresh)
    if len(old) != len(new):
        raise ValueError(f"{frozen.name}: row counts differ")
    for a, b in zip(old, new):
        if a.keys() != b.keys() or not all(equal(a[k], b[k]) for k in a):
            raise ValueError(f"{frozen.name}: changed data: {a} vs {b}")
    return "numerically equivalent at 1e-12"


def compare_factorial(stage20):
    archived = FROZEN / "stage20/reviewer_packet/06_Stage20_Factorial_Summary.csv"
    buckets = defaultdict(list)
    for key in ("Guan61", "FCID100"):
        for row in data(stage20 / f"Stage20_{key}_Policy_Pair_Results.csv"):
            buckets[(row["dataset"], row["scenario"], row["policy"])].append(row)
    archive_keys = set()
    for expected in data(archived):
        key = tuple(expected[k] for k in ("dataset", "scenario", "policy"))
        archive_keys.add(key)
        observed = buckets[key]
        if not observed or len(observed) != int(expected["pairs"]):
            raise ValueError(f"Missing Stage 20 result {key}")
        for suffix in ("00", "10", "01", "11"):
            mean = sum(r[f"C{suffix}_success"] == "True" for r in observed) / len(observed)
            if not equal(expected[f"Y{suffix}"], str(mean)):
                raise ValueError(f"Stage 20 point metric mismatch: {key}, Y{suffix}")
    if buckets.keys() != archive_keys:
        raise ValueError("The regenerated and archived Stage 20 groups differ")
    return len(archive_keys)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("stage18", "stage22", "stage24"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    checks = {}
    for stage, bundle, generated, outputs in (
        ("stage18", "Stage18_Portable_Reproduction", "generated", (
            "Stage18_4_Guan61_Policy_Summary.csv", "Stage18_5_Node_Bootstrap_Replicates.csv")),
        ("stage24", "Stage24_Portable_Reproduction", "generated", (
            "Stage24_Exact_Subset_Audit_Summary.csv",
            "Stage24_Targeted_Acquisition_Bootstrap_Summary.csv",
            "Stage24_Secondary_Saturation_Bootstrap_Summary.csv")),
        ("stage22", "", "stage22_recovery", tuple(
            p.name for p in sorted((FROZEN / "stage22/portable").glob("*.csv")))),
    ):
        archived = FROZEN / stage / "portable" / bundle
        if bundle:
            archived /= "generated"
        for filename in outputs:
            checks[filename] = compare_csv(
                archived / filename, getattr(args, stage) / generated / filename)
    print(json.dumps({"csv_matches": checks, "stage20_four_cell_group_matches":
                      compare_factorial(args.stage22 / "stage20_recovery")}, indent=2))


if __name__ == "__main__":
    main()
