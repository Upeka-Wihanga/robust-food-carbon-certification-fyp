from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "results/current/stage26"
PASS1 = FINAL / "pass1"
PASS2 = FINAL / "pass2"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalized_file_hash(path: Path) -> str:
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as handle:
            return sha256_bytes(handle.read())
    return sha256_bytes(path.read_bytes())


def npz_hash(path: Path) -> str:
    with np.load(path, allow_pickle=False) as archive:
        digest = hashlib.sha256()
        for name in sorted(archive.files):
            array = archive[name]
            digest.update(name.encode("utf-8"))
            digest.update(str(array.dtype).encode("utf-8"))
            digest.update(str(array.shape).encode("utf-8"))
            digest.update(array.tobytes())
        return digest.hexdigest()


def main() -> None:
    files = (
        "heldout_records.csv.gz",
        "fold_champions.csv",
        "coverage_by_fold_regime.csv",
        "first_action_rates.csv",
        "safety.json",
        "metrics.json",
    )
    comparisons = {}
    for name in files:
        first = normalized_file_hash(PASS1 / name)
        second = normalized_file_hash(PASS2 / name)
        comparisons[name] = {
            "pass1_sha256": first,
            "pass2_sha256": second,
            "match": first == second,
        }
    first_npz = npz_hash(PASS1 / "primary_arrays.npz")
    second_npz = npz_hash(PASS2 / "primary_arrays.npz")
    comparisons["primary_arrays.npz"] = {
        "pass1_sha256": first_npz,
        "pass2_sha256": second_npz,
        "match": first_npz == second_npz,
    }
    payload = {
        "runtime_and_timestamps_excluded": True,
        "comparisons": comparisons,
        "all_match": all(item["match"] for item in comparisons.values()),
    }
    output = FINAL / "reproducibility.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not payload["all_match"]:
        raise SystemExit("substantive final-run outputs are not deterministic")


if __name__ == "__main__":
    main()
