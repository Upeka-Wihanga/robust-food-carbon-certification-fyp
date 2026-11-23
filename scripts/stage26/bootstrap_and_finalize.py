from __future__ import annotations

import csv
import gzip
import hashlib
import json
import shutil
from pathlib import Path
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "results/current/stage26"
PASS1 = FINAL / "pass1"
BOOTSTRAP_REPLICATES = 5000
BOOTSTRAP_SEED = 26500
REGIME_ORDER = (
    "ORDER_ONLY",
    "PLUS_MINUS_5PP",
    "PLUS_MINUS_2PP",
    "PLUS_MINUS_1PP",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pooled_factor_first_rate(rows):
    """Count first actions across the specified cuisine and precision regimes."""
    denominator = sum(int(row["acquisition_denominator"]) for row in rows)
    factor_first = sum(int(row["factor_first"]) for row in rows)
    return factor_first / denominator if denominator else None


def main() -> None:
    started = perf_counter()
    reproducibility = json.loads(
        (FINAL / "reproducibility.json").read_text(encoding="utf-8")
    )
    safety = json.loads((PASS1 / "safety.json").read_text(encoding="utf-8"))
    if not reproducibility["all_match"] or not safety["pass"]:
        summary = {
            "g26_0": {
                **safety,
                "deterministic_output_hashes_match": reproducibility["all_match"],
                "verdict": "FAIL",
            },
            "interpretation_stopped": True,
            "overall_stage26_classification": "FAIL / ROLLBACK",
        }
        (FINAL / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise SystemExit("G26-0 failed; performance interpretation stopped")

    metrics = json.loads((PASS1 / "metrics.json").read_text(encoding="utf-8"))
    with np.load(PASS1 / "primary_arrays.npz", allow_pickle=False) as archive:
        oasa = archive["oasa"].astype(np.float64)
        champion = archive["champion"].astype(np.float64)
        pair_cuisines = archive["pair_cuisines"].astype(str)
        pair_recipe_a = archive["pair_recipe_a"].astype(str)
        pair_recipe_b = archive["pair_recipe_b"].astype(str)
        cuisines = tuple(archive["cuisines"].astype(str))
    difference = oasa - champion

    cuisine_data = {}
    for cuisine in cuisines:
        pair_indexes = np.flatnonzero(pair_cuisines == cuisine)
        recipe_ids = sorted(
            set(pair_recipe_a[pair_indexes]) | set(pair_recipe_b[pair_indexes])
        )
        recipe_index = {recipe_id: index for index, recipe_id in enumerate(recipe_ids)}
        endpoints = np.array(
            [
                (
                    recipe_index[pair_recipe_a[pair_index]],
                    recipe_index[pair_recipe_b[pair_index]],
                )
                for pair_index in pair_indexes
            ],
            dtype=np.int64,
        )
        cuisine_data[cuisine] = (
            pair_indexes,
            len(recipe_ids),
            endpoints,
        )

    generator = np.random.default_rng(BOOTSTRAP_SEED)
    bootstrap_values = np.empty(BOOTSTRAP_REPLICATES, dtype=np.float64)
    for replicate in range(BOOTSTRAP_REPLICATES):
        weights_by_cuisine = {}
        for cuisine in cuisines:
            _, recipe_count, endpoints = cuisine_data[cuisine]
            while True:
                sampled = generator.integers(0, recipe_count, size=recipe_count)
                multiplicities = np.bincount(sampled, minlength=recipe_count).astype(
                    np.float64
                )
                if np.count_nonzero(multiplicities) >= 2:
                    break
            weights_by_cuisine[cuisine] = (
                multiplicities[endpoints[:, 0]] * multiplicities[endpoints[:, 1]]
            )
        sampled_worlds = generator.integers(0, 100, size=100)
        cuisine_effects = []
        for cuisine in cuisines:
            pair_indexes, _, _ = cuisine_data[cuisine]
            weights = weights_by_cuisine[cuisine]
            denominator = float(np.sum(weights))
            weighted = (
                np.tensordot(weights, difference[pair_indexes, :, :], axes=(0, 0))
                / denominator
            )
            cuisine_effects.append(float(np.mean(weighted[:, sampled_worlds])))
        bootstrap_values[replicate] = float(np.mean(cuisine_effects))

    bootstrap_path = FINAL / "bootstrap_primary.csv.gz"
    with gzip.open(bootstrap_path, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("replicate", "delta"))
        writer.writeheader()
        for index, value in enumerate(bootstrap_values):
            writer.writerow({"replicate": index, "delta": repr(float(value))})

    lower, upper = np.percentile(bootstrap_values, (2.5, 97.5))
    median = float(np.median(bootstrap_values))
    probability_positive = float(np.mean(bootstrap_values > 0.0))
    point_delta = float(metrics["primary_delta"])
    if point_delta >= 0.05 and lower > 0.0:
        g26_1 = "STRONG PASS"
    elif lower > 0.0 and point_delta < 0.05:
        g26_1 = "STATISTICAL PASS / PRACTICAL WARNING"
    elif point_delta > 0.0 and lower <= 0.0 <= upper:
        g26_1 = "UNRESOLVED"
    else:
        g26_1 = "FAIL"

    with (PASS1 / "first_action_rates.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        action_rows = list(csv.DictReader(handle))
    oasa_rows = [row for row in action_rows if row["policy_id"] == "P"]
    by_cuisine_regime = {
        (row["held_out_cuisine"], row["regime"]): row for row in oasa_rows
    }
    switching_cuisines = {}
    for cuisine in cuisines:
        factor_rates = {}
        for regime in REGIME_ORDER:
            raw = by_cuisine_regime[(cuisine, regime)]["factor_first_rate"]
            factor_rates[regime] = float(raw) if raw else None
        coarse = pooled_factor_first_rate([
            by_cuisine_regime[(cuisine, regime)] for regime in REGIME_ORDER[:2]
        ])
        tight = factor_rates["PLUS_MINUS_1PP"]
        correct = tight is not None and coarse is not None and tight > coarse
        switching_cuisines[cuisine] = {
            "order_only_factor_rate": factor_rates["ORDER_ONLY"],
            "plus_minus_5pp_factor_rate": factor_rates["PLUS_MINUS_5PP"],
            "plus_minus_2pp_factor_rate": factor_rates["PLUS_MINUS_2PP"],
            "plus_minus_1pp_factor_rate": factor_rates["PLUS_MINUS_1PP"],
            "coarse_factor_rate": coarse,
            "tight_factor_rate": tight,
            "correct_direction": correct,
        }
    overall_coarse = pooled_factor_first_rate([
        row for row in oasa_rows if row["regime"] in REGIME_ORDER[:2]
    ])
    overall_tight = pooled_factor_first_rate([
        row for row in oasa_rows if row["regime"] == "PLUS_MINUS_1PP"
    ])
    switching_difference = (
        None
        if overall_coarse is None or overall_tight is None
        else overall_tight - overall_coarse
    )
    correct_cuisines = sum(
        value["correct_direction"] for value in switching_cuisines.values()
    )
    g26_2_pass = (
        overall_coarse is not None
        and overall_tight is not None
        and overall_coarse < 0.50
        and overall_tight > 0.50
        and switching_difference is not None
        and switching_difference >= 0.20
        and correct_cuisines >= 6
    )
    g26_2 = "PASS" if g26_2_pass else "FAIL"

    total_oasa = sum(
        int(row["acquisition_denominator"])
        + int(row["initially_certified"])
        + int(row["no_action"])
        for row in oasa_rows
    )
    initial_count = sum(int(row["initially_certified"]) for row in oasa_rows)
    no_action_count = sum(int(row["no_action"]) for row in oasa_rows)

    g26_1_pass = g26_1 in {
        "STRONG PASS",
        "STATISTICAL PASS / PRACTICAL WARNING",
    }
    if g26_1 == "STRONG PASS" and g26_2_pass:
        overall_classification = "STRONG PASS"
    elif g26_1_pass or g26_2_pass:
        overall_classification = "PARTIAL PASS"
    else:
        overall_classification = "FAIL / ROLLBACK"

    pass1_runtime = json.loads((PASS1 / "runtime.json").read_text(encoding="utf-8"))
    pass2_runtime = json.loads(
        (FINAL / "pass2/runtime.json").read_text(encoding="utf-8")
    )
    per_cuisine_delta = {
        cuisine: (
            metrics["cuisine_coverage"]["P"][cuisine]
            - metrics["cuisine_coverage"]["CHAMPION"][cuisine]
        )
        for cuisine in cuisines
    }
    summary = {
        "g26_0": {
            **safety,
            "deterministic_output_hashes_match": True,
            "verdict": "PASS",
        },
        "fold_champions": metrics["champions"],
        "primary": {
            "oasa_coverage": metrics["overall_coverage"]["P"],
            "champion_coverage": metrics["overall_coverage"]["CHAMPION"],
            "delta": point_delta,
            "delta_percentage_points": 100 * point_delta,
        },
        "bootstrap": {
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "ci_95": [float(lower), float(upper)],
            "median_delta": median,
            "probability_delta_gt_zero": probability_positive,
        },
        "g26_1_verdict": g26_1,
        "regime_coverage": metrics["regime_coverage"],
        "per_cuisine_delta": per_cuisine_delta,
        "g26_2": {
            "overall_coarse_factor_rate": overall_coarse,
            "overall_coarse_share_rate": (
                None if overall_coarse is None else 1 - overall_coarse
            ),
            "overall_plus_minus_1pp_factor_rate": overall_tight,
            "overall_plus_minus_1pp_share_rate": (
                None if overall_tight is None else 1 - overall_tight
            ),
            "factor_rate_difference": switching_difference,
            "correct_direction_cuisines": correct_cuisines,
            "cuisine_values": switching_cuisines,
            "verdict": g26_2,
        },
        "hindsight": {
            "coverage": metrics["overall_coverage"]["H"],
            "oasa_regret": metrics["hindsight_regret"],
        },
        "baseline_coverage": {
            policy_id: metrics["overall_coverage"][policy_id]
            for policy_id in ("B0", "B1", "B2", "B3", "B4")
        },
        "oasa_initially_certified": {
            "count": initial_count,
            "rate": initial_count / total_oasa,
        },
        "oasa_no_action": {
            "count": no_action_count,
            "rate": no_action_count / total_oasa,
        },
        "tie_counts": metrics["tie_counts"],
        "mean_cost": metrics["mean_cost"],
        "budget_to_first_certificate": metrics["budget_to_first_certificate"],
        "total_evaluated_trajectories": metrics["total_trajectories"],
        "runtime": {
            "pass1": pass1_runtime,
            "pass2": pass2_runtime,
            "bootstrap_seconds": perf_counter() - started,
        },
        "folds_where_oasa_loses": [
            cuisine for cuisine, delta in per_cuisine_delta.items() if delta < 0
        ],
        "overall_stage26_classification": overall_classification,
    }
    (FINAL / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    for name in (
        "fold_champions.csv",
        "heldout_records.csv.gz",
        "coverage_by_fold_regime.csv",
        "first_action_rates.csv",
        "primary_arrays.npz",
    ):
        shutil.copyfile(PASS1 / name, FINAL / name)

    checksum_paths = (
        FINAL / "run_manifest.json",
        FINAL / "fold_champions.csv",
        FINAL / "heldout_records.csv.gz",
        FINAL / "coverage_by_fold_regime.csv",
        FINAL / "first_action_rates.csv",
        FINAL / "bootstrap_primary.csv.gz",
        FINAL / "summary.json",
        FINAL / "reproducibility.json",
        FINAL / "primary_arrays.npz",
    )
    with (FINAL / "checksums.txt").open("w", encoding="utf-8") as handle:
        for path in checksum_paths:
            handle.write(f"{file_sha256(path)}  {path.name}\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
