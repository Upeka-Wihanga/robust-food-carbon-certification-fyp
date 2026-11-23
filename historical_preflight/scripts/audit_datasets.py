"""Independently rebuild Guan61 and inventory the frozen raw sources."""
import ast
from collections import Counter, defaultdict
import csv
from decimal import Decimal
import hashlib
from itertools import combinations
import json
from pathlib import Path

from openpyxl import load_workbook
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "evidence/frozen"
HANDOFF = FROZEN / "handoff/Codex_Research_Handoff_v1"
STAGE18 = FROZEN / "stage18/portable/Stage18_Portable_Reproduction"
STAGE24 = FROZEN / "stage24/portable/Stage24_Portable_Reproduction"
GUAN = "Carbon footprint and nutrition estimation of Chinese cuisines.xlsx"
FACTOR = "Greenhouse gas emission factors (kgCO2e/kg)_production"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def worksheet(book, sheet):
    stream = book[sheet].values
    header = next(stream)
    return [dict(zip(header, row)) for row in stream]


def normalized(name):
    return " ".join(name.lower().split())


def guan_audit():
    book = load_workbook(HANDOFF / "raw_data" / GUAN, read_only=True, data_only=True)
    factors = {}
    duplicates = Counter()
    for row in worksheet(book, "Greenhouse gas emission factors"):
        value = row[FACTOR]
        if not isinstance(value, (int, float)) or not row["Ingredient "]:
            continue
        key = normalized(row["Ingredient "])
        factor = Decimal(str(value))
        if key in factors:
            duplicates[key] += 1
            if factors[key] != factor:
                raise ValueError(f"Conflicting production factors for {key}")
        factors[key] = factor
    recipes = [r for r in worksheet(book, "Recipe") if r["Recipe English name"]]
    book.close()
    eligible = defaultdict(set)
    exclusions = []
    missing = Counter()
    mapping = Counter()
    shared = set()
    parsed = 0
    retained_errors = []
    zero_mapped = Counter()
    zero_keys = set()
    for row in recipes:
        cuisine, name = row["Cuisine"], row["Recipe English name"]
        reason = None
        try:
            document = ast.literal_eval(row["Ingredient (g)"])
            weights = [(normalized(k), Decimal(str(v))) for k, v in document.items()
                       if isinstance(v, (int, float)) and v > 0]
            if len(weights) < 2:
                raise ValueError("too few positive weights")
        except (SyntaxError, TypeError, ValueError, AttributeError):
            exclusions.append({"cuisine": cuisine, "recipe": name, "reason": "unparseable"})
            continue
        parsed += 1
        total = sum(v for _, v in weights)
        major = {k for k, v in weights if v >= Decimal("0.05") * total}
        unmapped = sorted(major - factors.keys())
        if unmapped:
            missing.update(unmapped)
            reason = "unmapped major ingredients"
        elif not isinstance(row["CF(gCO2e)_production"], (int, float)):
            reason = "missing reported production total"
        else:
            reported = Decimal(str(row["CF(gCO2e)_production"]))
            rebuilt = sum(v * factors[k] for k, v in weights if k in major)
            if reported <= 0 or abs(rebuilt - reported) > Decimal("0.01") * reported:
                reason = "production total outside 1% tolerance"
        if reason:
            exclusions.append({"cuisine": cuisine, "recipe": name, "reason": reason,
                               "unmapped_major": unmapped})
            continue
        if name in eligible[cuisine]:
            raise ValueError(f"Duplicate eligible recipe {cuisine}/{name}")
        eligible[cuisine].add(name)
        retained_errors.append(float(abs(rebuilt - reported) / reported))
        for original, weight in document.items():
            if weight == 0:
                name_key = normalized(original)
                kind = "direct" if name_key in factors else "fallback"
                zero_mapped[kind] += 1
                zero_keys.add((kind, name_key))
        for key, _ in weights:
            category = "major_direct" if key in major else (
                "minor_direct" if key in factors else "minor_fallback")
            mapping[category] += 1
            shared.add(("fallback" if key not in factors else "direct", key))
    rebuilt_pairs = {(c, a, b) for c, names in eligible.items()
                     for a, b in combinations(sorted(names), 2)}
    archived = rows(STAGE18 / "inputs/Stage13_Guan_Pair_Results.csv")
    reference_pairs = {(p["cuisine"], *sorted((p["recipe_A"], p["recipe_B"])))
                       for p in archived}
    return {
        "source_rows": len(recipes), "parseable": parsed,
        "eligible": sum(map(len, eligible.values())),
        "cuisines": {c: len(names) for c, names in sorted(eligible.items())},
        "within_cuisine_pairs": len(rebuilt_pairs),
        "reference_rows": len(archived),
        "pairs_only_in_rebuild": sorted(rebuilt_pairs - reference_pairs),
        "pairs_only_in_reference": sorted(reference_pairs - rebuilt_pairs),
        "max_retained_relative_error": max(retained_errors, default=None),
        "positive_weight_mapping": dict(mapping),
        "shared_factor_keys": dict(Counter(kind for kind, _ in shared)),
        "zero_weight_occurrences_if_retained": dict(zero_mapped),
        "additional_factor_keys_if_zero_weights_retained": dict(
            Counter(kind for kind, _ in zero_keys - shared)),
        "production_factor_rows_after_normalization": len(factors),
        "zero_factors": sum(v == 0 for v in factors.values()),
        "negative_factors": sum(v < 0 for v in factors.values()),
        "equal_duplicate_factor_names": dict(duplicates),
        "unmapped_major_ingredients": dict(missing.most_common()),
        "exclusion_counts": dict(Counter(r["reason"] for r in exclusions)),
        "exclusions": exclusions,
    }


def audit():
    manifest = json.loads((HANDOFF / "provenance/PROVENANCE_MANIFEST.json").read_text())
    for entry in manifest:
        file = HANDOFF / entry["path"]
        if file.stat().st_size != entry["bytes"] or sha(file) != entry["sha256"]:
            raise ValueError(f"Invalid handoff item: {file}")
    raw = {}
    for stage18_name, name in [
        (GUAN.replace(" ", "_"), GUAN),
        ("dataFIELDv1.0.xlsx", "dataFIELDv1.0.xlsx"),
        ("Recipes_WWEIA_FCID_0510.csv", "Recipes_WWEIA_FCID_0510.csv"),
    ]:
        digest = sha(HANDOFF / "raw_data" / name)
        if digest != sha(STAGE18 / "inputs" / stage18_name) or digest != sha(STAGE24 / name):
            raise ValueError(f"Raw input differs across supplied packets: {name}")
        raw[name] = digest
    fcid_path = HANDOFF / "raw_data/Recipes_WWEIA_FCID_0510.csv"
    field_path = HANDOFF / "raw_data/dataFIELDv1.0.xlsx"
    fcid = pd.read_csv(fcid_path)
    linkage = load_workbook(field_path, read_only=True, data_only=True)
    sheet_sizes = {sheet.title: sheet.max_row for sheet in linkage}
    linkage.close()
    links = pd.read_excel(field_path, sheet_name="FCID linkages", skiprows=2)
    fields = ["FCID_Code", "CO2 eq / kg", "scaled SD (group SD*food mean/group mean).1"]
    for key in fields:
        links[key] = pd.to_numeric(links[key], errors="coerce")
    usable_links = links.dropna(subset=fields[:2])
    codes = set(usable_links[fields[0]].astype(int))
    sample = fcid[(fcid.Mod_Code == 0) & (fcid.WWEIA_0510_IND == 1)
                  & (fcid.Commodity_Weight > 0)]
    unmatched = sample.loc[~sample.FCID_Code.isin(codes)]
    link_conflicts = usable_links.groupby(fields[0])[fields[1]].nunique() > 1
    return {
        "handoff_hashes_verified": len(manifest), "raw_sha256": raw,
        "fcid": {
            "rows": len(fcid), "foods": int(fcid.Food_Code.nunique()),
            "columns": list(fcid.columns),
            "raw_duplicate_rows_beyond_first": int(fcid.duplicated().sum()),
            "raw_missing_key_or_mass": int(fcid[[
                "FCID_Code", "Food_Code", "Commodity_Weight"]].isna().any(axis=1).sum()),
            "raw_zero_weights": int((fcid.Commodity_Weight == 0).sum()),
            "raw_negative_weights": int((fcid.Commodity_Weight < 0).sum()),
            "baseline_positive_rows": len(sample),
            "baseline_unlinked_rows": len(unmatched),
            "baseline_unlinked_commodity_codes": int(unmatched.FCID_Code.nunique()),
            "baseline_foods_with_unlinked_lines": int(unmatched.Food_Code.nunique()),
        },
        "datafield": {
            "sheet_rows_including_headers": sheet_sizes,
            "usable_linkage_rows": len(usable_links),
            "distinct_matched_commodity_codes": len(codes),
            "conflicting_duplicate_mean_codes": int(link_conflicts.sum()),
            "zero_factor_rows": int((usable_links[fields[1]] == 0).sum()),
            "negative_factor_rows": int((usable_links[fields[1]] < 0).sum()),
            "rows_with_missing_scaled_sd": int(usable_links[fields[2]].isna().sum()),
        },
        "guan": guan_audit(),
    }


if __name__ == "__main__":
    results = audit()
    print(json.dumps(results, indent=2))
    guan = results["guan"]
    if (guan["eligible"], guan["within_cuisine_pairs"], len(guan["cuisines"])) != (61, 222, 8):
        raise SystemExit("Guan61 eligibility counts differ from the frozen protocol")
    if guan["pairs_only_in_rebuild"] or guan["pairs_only_in_reference"]:
        raise SystemExit("Guan61 identities differ from the frozen cohort")
