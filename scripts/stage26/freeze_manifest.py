"""Record an auditable Windows run receipt against the archived protocol."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
from pathlib import Path

from food_carbon_cert.data import load_guan, load_source_manifest, sha256_file
from food_carbon_cert.stage26 import (
    build_m2_factor_model,
    build_within_cuisine_pairs,
    normalize_guan_factor_table,
    reconstruct_guan_cohort,
)

ROOT = Path(__file__).resolve().parents[2]
ARCHIVED_MANIFEST = Path(__file__).with_name("frozen_run_manifest.json")
OUTPUT = ROOT / "results/current/stage26/run_manifest.json"


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_identities(cohort, pairs, archived) -> None:
    recipes = [
        {"recipe_id": item.recipe_id, "source_row": item.source_row, "cuisine": item.cuisine}
        for item in sorted(cohort.eligible_recipes, key=lambda recipe: recipe.recipe_id)
    ]
    edges = [
        {
            "pair_id": item.pair_id,
            "cuisine": item.cuisine,
            "recipe_a_id": item.recipe_a_id,
            "recipe_b_id": item.recipe_b_id,
        }
        for item in sorted(pairs, key=lambda pair: pair.pair_id)
    ]
    if {
        "cohort_sha256": canonical_hash(recipes),
        "pair_manifest_sha256": canonical_hash(edges),
    } != archived["identity_hashes"]:
        raise ValueError("Rebuilt Guan61 recipe or pair identities differ from the archive")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    archived = json.loads(ARCHIVED_MANIFEST.read_text(encoding="utf-8"))
    sources = load_source_manifest(ROOT / "data/manifests/source_files.json")
    expected = sources.by_category("guan_external_recipe_workbook")
    raw_path = ROOT / "data/raw" / expected.expected_filename
    workbook = load_guan(raw_path, expected=expected)
    factors = normalize_guan_factor_table(workbook)
    cohort = reconstruct_guan_cohort(workbook, factors=factors)
    pairs = build_within_cuisine_pairs(cohort.eligible_recipes)
    verify_identities(cohort, pairs, archived)
    m2 = build_m2_factor_model(cohort.eligible_recipes, factors)
    counts = {
        "source_rows": cohort.source_row_count,
        "parseable_recipes": cohort.parseable_count,
        "eligible_recipes": cohort.eligible_count,
        "cuisines": cohort.cuisine_counts,
        "within_cuisine_pairs": len(pairs),
        "m2_factor_keys": len(m2.intervals),
        "m2_p25": str(m2.p25),
        "m2_p75": str(m2.p75),
    }
    if counts != archived["verified_counts"]:
        raise ValueError("Rebuilt Guan61/M2 counts differ from the archive")
    if args.check_only:
        print(json.dumps(counts, indent=2))
        return

    version = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    sources = sorted((ROOT / "src/food_carbon_cert").rglob("*.py"))
    drivers = sorted(Path(__file__).parent.glob("*.py"))
    receipt = {
        "archived_manifest_sha256": sha256_file(ARCHIVED_MANIFEST),
        "commit": version,
        "configuration": archived["configuration"],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": {
                name: importlib.metadata.version(name)
                for name in ("numpy", "scipy", "pandas", "openpyxl")
            },
        },
        "file_sha256": {
            path.relative_to(ROOT).as_posix(): sha256_file(path)
            for path in (*sources, *drivers)
        },
        "source_sha256": sha256_file(raw_path),
        "identity_hashes": archived["identity_hashes"],
        "verified_counts": counts,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(receipt, output, indent=2, sort_keys=True)
        output.write("\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
