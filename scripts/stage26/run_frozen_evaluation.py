from __future__ import annotations

import argparse
import csv
import gzip
import inspect
import json
import multiprocessing
import os
from collections import Counter
from pathlib import Path
from time import perf_counter

import numpy as np

from food_carbon_cert.certification import Decision
from food_carbon_cert.data import load_guan, load_source_manifest, sha256_file
from freeze_manifest import verify_identities
from food_carbon_cert.stage26 import (
    BASELINE_ORDER,
    B0ShareOnly,
    B1FactorOnly,
    B2FixedStaged,
    B3WidthMixed,
    B4OneStepVoi,
    FactorAcquisition,
    LatentObservations,
    OasaTwoStep,
    PolicyComputationCache,
    PolicyId,
    ShareAcquisition,
    Stage26FoodState,
    Stage26PairState,
    StartingShareRegime,
    apply_observation,
    available_actions,
    build_loco_folds,
    build_m2_factor_model,
    build_within_cuisine_pairs,
    certify_stage26_state,
    generate_frozen_factor_worlds,
    make_starting_share_disclosure,
    normalize_guan_factor_table,
    observable_state_key,
    reconstruct_guan_cohort,
    run_hindsight_ceiling,
    score_immediate_action,
    select_baseline_champion,
    select_recipe_share_rank,
    state_value,
)

ROOT = Path(__file__).resolve().parents[2]
FINAL_ROOT = ROOT / "results/current/stage26"
FROZEN_MANIFEST = Path(__file__).with_name("frozen_run_manifest.json")
POLICY_IDS = ("B0", "B1", "B2", "B3", "B4", "P", "H")
BASELINE_IDS = ("B0", "B1", "B2", "B3", "B4")
REGIMES = tuple(StartingShareRegime)
SEEDS = tuple(range(26000, 26100))
TOLERANCE = 1e-12
RECORD_FIELDS = (
    "pair_id",
    "cuisine",
    "recipe_a_id",
    "recipe_b_id",
    "regime",
    "seed",
    "policy_id",
    "initial_certified",
    "no_action",
    "terminal_decision",
    "terminal_certified",
    "lower_bound",
    "upper_bound",
    "latent_difference",
    "cost_spent",
    "stopping_step",
    "budget_to_first_certificate",
    "first_action_id",
    "first_action_kind",
    "action_sequence",
    "tie_event_count",
    "containment_failures",
    "false_direction",
    "budget_violation",
    "repeated_action",
    "post_certificate_action",
)

_RECIPES = None
_M2 = None
_WORLDS = None


def initialize_worker(recipes, m2, worlds, seeds):
    global _RECIPES, _M2, _WORLDS, SEEDS
    _RECIPES, _M2, _WORLDS, SEEDS = recipes, m2, worlds, seeds


def baseline_pair_worker(task):
    pair_index, pair = task
    recipes = _RECIPES
    m2 = _M2
    worlds = _WORLDS
    recipe_a = recipes[pair.recipe_a_id]
    recipe_b = recipes[pair.recipe_b_id]
    cache = PolicyComputationCache()
    policies = (
        B0ShareOnly(cache),
        B1FactorOnly(cache),
        B2FixedStaged(cache),
        B3WidthMixed(cache),
        B4OneStepVoi(cache),
    )
    records = []
    values = np.zeros((len(BASELINE_IDS), len(REGIMES), len(SEEDS)), dtype=np.uint8)
    for regime_index, regime in enumerate(REGIMES):
        initial, rank_a, rank_b, keys = build_initial_state(
            recipe_a, recipe_b, m2, regime
        )
        for seed_index, seed in enumerate(SEEDS):
            world = worlds[seed]
            observations = LatentObservations(
                float(recipe_a.ingredients[rank_a - 1].share),
                float(recipe_b.ingredients[rank_b - 1].share),
                {key: world[key] for key in keys},
            )
            truth = latent_difference(recipe_a, recipe_b, world)
            for policy_index, policy in enumerate(policies):
                record = execute_policy(
                    policy,
                    initial,
                    observations,
                    pair,
                    recipe_a,
                    recipe_b,
                    regime,
                    seed,
                    truth,
                )
                records.append(record)
                values[policy_index, regime_index, seed_index] = int(
                    record["terminal_certified"]
                )
    return pair_index, records, values


def oasa_hindsight_pair_worker(task):
    pair_index, pair = task
    recipes = _RECIPES
    m2 = _M2
    worlds = _WORLDS
    recipe_a = recipes[pair.recipe_a_id]
    recipe_b = recipes[pair.recipe_b_id]
    cache = PolicyComputationCache()
    oasa = OasaTwoStep(cache)
    records = []
    oasa_values = np.zeros((len(REGIMES), len(SEEDS)), dtype=np.uint8)
    hindsight_values = np.zeros_like(oasa_values)
    for regime_index, regime in enumerate(REGIMES):
        initial, rank_a, rank_b, keys = build_initial_state(
            recipe_a, recipe_b, m2, regime
        )
        for seed_index, seed in enumerate(SEEDS):
            world = worlds[seed]
            observations = LatentObservations(
                float(recipe_a.ingredients[rank_a - 1].share),
                float(recipe_b.ingredients[rank_b - 1].share),
                {key: world[key] for key in keys},
            )
            truth = latent_difference(recipe_a, recipe_b, world)
            oasa_record = execute_policy(
                oasa,
                initial,
                observations,
                pair,
                recipe_a,
                recipe_b,
                regime,
                seed,
                truth,
            )
            records.append(oasa_record)
            oasa_values[regime_index, seed_index] = int(
                oasa_record["terminal_certified"]
            )
            hindsight_record = execute_hindsight(
                initial,
                observations,
                cache,
                pair,
                recipe_a,
                recipe_b,
                regime,
                seed,
                truth,
            )
            records.append(hindsight_record)
            hindsight_values[regime_index, seed_index] = int(
                hindsight_record["terminal_certified"]
            )
    return pair_index, records, oasa_values, hindsight_values


def build_initial_state(recipe_a, recipe_b, m2, regime):
    selection_a = select_recipe_share_rank(recipe_a, m2.intervals)
    selection_b = select_recipe_share_rank(recipe_b, m2.intervals)
    disclosure_a = make_starting_share_disclosure(
        ingredient_count=len(recipe_a.ingredients),
        rank=selection_a.rank,
        latent_share=recipe_a.ingredients[selection_a.rank - 1].share,
        regime=regime,
    )
    disclosure_b = make_starting_share_disclosure(
        ingredient_count=len(recipe_b.ingredients),
        rank=selection_b.rank,
        latent_share=recipe_b.ingredients[selection_b.rank - 1].share,
        regime=regime,
    )
    keys = {
        ingredient.factor_key
        for recipe in (recipe_a, recipe_b)
        for ingredient in recipe.ingredients
    }
    state = Stage26PairState(
        Stage26FoodState(
            recipe_a.recipe_id,
            tuple(ingredient.factor_key for ingredient in recipe_a.ingredients),
            selection_a.rank,
            disclosure_a.interval,
        ),
        Stage26FoodState(
            recipe_b.recipe_id,
            tuple(ingredient.factor_key for ingredient in recipe_b.ingredients),
            selection_b.rank,
            disclosure_b.interval,
        ),
        {key: m2.intervals[key] for key in keys},
        frozenset(),
        2,
    )
    return state, selection_a.rank, selection_b.rank, keys


def latent_difference(recipe_a, recipe_b, world) -> float:
    value_a = sum(
        float(ingredient.share) * world[ingredient.factor_key]
        for ingredient in recipe_a.ingredients
    )
    value_b = sum(
        float(ingredient.share) * world[ingredient.factor_key]
        for ingredient in recipe_b.ingredients
    )
    return value_a - value_b


def observation_contained(state, action, observed: float) -> bool:
    acquisition = action.acquisition
    if isinstance(acquisition, ShareAcquisition):
        food = state.food_a if acquisition.side.value == "A" else state.food_b
        return food.share_interval.contains(observed)
    if isinstance(acquisition, FactorAcquisition):
        interval = state.factor_intervals[acquisition.factor_key]
        return interval.lower <= observed <= interval.upper
    return False


def false_direction(decision: Decision, truth: float) -> bool:
    if decision is Decision.A_LOWER:
        return truth >= 0.0
    if decision is Decision.B_LOWER:
        return truth <= 0.0
    return False


def record_from_state(
    *,
    pair,
    recipe_a,
    recipe_b,
    regime,
    seed,
    policy_id,
    initial_certified,
    state,
    action_ids,
    first_kind,
    tie_events,
    containment_failures,
    repeated_action,
    post_certificate_action,
    budget_to_first,
    truth,
):
    result = certify_stage26_state(state)
    direction_error = false_direction(result.decision, truth)
    return {
        "pair_id": pair.pair_id,
        "cuisine": pair.cuisine,
        "recipe_a_id": recipe_a.recipe_id,
        "recipe_b_id": recipe_b.recipe_id,
        "regime": regime.value,
        "seed": seed,
        "policy_id": policy_id,
        "initial_certified": int(initial_certified),
        "no_action": int(not initial_certified and not action_ids),
        "terminal_decision": result.decision.value,
        "terminal_certified": int(result.decision is not Decision.ABSTAIN),
        "lower_bound": repr(result.lower_bound),
        "upper_bound": repr(result.upper_bound),
        "latent_difference": repr(truth),
        "cost_spent": state.spent,
        "stopping_step": len(action_ids),
        "budget_to_first_certificate": (
            "" if budget_to_first is None else budget_to_first
        ),
        "first_action_id": action_ids[0] if action_ids else "",
        "first_action_kind": first_kind,
        "action_sequence": "|".join(action_ids),
        "tie_event_count": tie_events,
        "containment_failures": containment_failures,
        "false_direction": int(direction_error),
        "budget_violation": int(state.spent > state.budget),
        "repeated_action": int(repeated_action),
        "post_certificate_action": int(post_certificate_action),
    }


def execute_policy(
    policy,
    initial,
    observations,
    pair,
    recipe_a,
    recipe_b,
    regime,
    seed,
    truth,
):
    state = initial
    initial_certified = state_value(state, policy.cache).certified
    action_ids: list[str] = []
    tie_events = 0
    containment_failures = 0
    repeated_action = False
    post_certificate_action = False
    budget_to_first = 0 if initial_certified else None
    while state.remaining_budget > 0:
        if state_value(state, policy.cache).certified:
            break
        decision = policy.choose_action(state, regime)
        if decision is None:
            break
        if decision.action.action_id in action_ids:
            repeated_action = True
        observed = observations.reveal(decision.action)
        if not observation_contained(state, decision.action, observed):
            containment_failures += 1
        if state_value(state, policy.cache).certified:
            post_certificate_action = True
        action_ids.append(decision.action.action_id)
        tie_events += decision.tied_best_count > 1
        state = apply_observation(state, decision.action.acquisition, observed)
        if budget_to_first is None and state_value(state, policy.cache).certified:
            budget_to_first = state.spent
    first_kind = (
        "SHARE"
        if action_ids and action_ids[0].startswith("share:")
        else "FACTOR" if action_ids else ""
    )
    return record_from_state(
        pair=pair,
        recipe_a=recipe_a,
        recipe_b=recipe_b,
        regime=regime,
        seed=seed,
        policy_id=policy.policy_id.value,
        initial_certified=initial_certified,
        state=state,
        action_ids=action_ids,
        first_kind=first_kind,
        tie_events=tie_events,
        containment_failures=containment_failures,
        repeated_action=repeated_action,
        post_certificate_action=post_certificate_action,
        budget_to_first=budget_to_first,
        truth=truth,
    )


def execute_hindsight(
    initial,
    observations,
    cache,
    pair,
    recipe_a,
    recipe_b,
    regime,
    seed,
    truth,
):
    initial_certified = state_value(initial, cache).certified
    run = run_hindsight_ceiling(initial, observations, cache=cache)
    state = initial
    action_ids: list[str] = []
    containment_failures = 0
    repeated_action = False
    post_certificate_action = False
    budget_to_first = 0 if initial_certified else None
    for executed in run.acquisitions:
        candidates = {
            action.action_id: action for action in available_actions(state, cache)
        }
        action = candidates[executed.action_id]
        if executed.action_id in action_ids:
            repeated_action = True
        if state_value(state, cache).certified:
            post_certificate_action = True
        if not observation_contained(state, action, executed.observed_value):
            containment_failures += 1
        action_ids.append(executed.action_id)
        state = apply_observation(state, action.acquisition, executed.observed_value)
        if budget_to_first is None and state_value(state, cache).certified:
            budget_to_first = state.spent
    if observable_state_key(state) != observable_state_key(run.terminal_state):
        raise AssertionError("hindsight replay does not match terminal state")
    first_kind = (
        "SHARE"
        if action_ids and action_ids[0].startswith("share:")
        else "FACTOR" if action_ids else ""
    )
    return record_from_state(
        pair=pair,
        recipe_a=recipe_a,
        recipe_b=recipe_b,
        regime=regime,
        seed=seed,
        policy_id="H",
        initial_certified=initial_certified,
        state=state,
        action_ids=action_ids,
        first_kind=first_kind,
        tie_events=0,
        containment_failures=containment_failures,
        repeated_action=repeated_action,
        post_certificate_action=post_certificate_action,
        budget_to_first=budget_to_first,
        truth=truth,
    )


def write_champions(output, cuisines, baseline_arrays, pair_indexes_by_cuisine):
    rows = []
    champion_indexes = {}
    for held_out in cuisines:
        training_scores = {}
        for policy_index, policy_id in enumerate(BASELINE_IDS):
            cuisine_values = []
            for cuisine in cuisines:
                if cuisine == held_out:
                    continue
                indexes = pair_indexes_by_cuisine[cuisine]
                cuisine_values.append(
                    float(np.mean(baseline_arrays[policy_index, indexes, :, :]))
                )
            training_scores[PolicyId(policy_id)] = float(np.mean(cuisine_values))
        champion = select_baseline_champion(training_scores)
        champion_indexes[held_out] = BASELINE_IDS.index(champion.policy_id.value)
        rows.append(
            {
                "held_out_cuisine": held_out,
                "champion": champion.policy_id.value,
                "training_score": repr(champion.training_score),
                "tie": int(champion.had_tie),
                "tied_policies": "|".join(
                    policy.value for policy in champion.tied_policy_ids
                ),
                **{
                    f"{policy_id}_training_score": repr(
                        training_scores[PolicyId(policy_id)]
                    )
                    for policy_id in BASELINE_IDS
                },
            }
        )
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows, champion_indexes


def structural_leakage_check(initial_states) -> dict[str, object]:
    policy = OasaTwoStep(PolicyComputationCache())
    state = initial_states[0]
    decision_a = policy.choose_action(state, StartingShareRegime.ORDER_ONLY)
    decision_b = policy.choose_action(state, StartingShareRegime.ORDER_ONLY)
    parameters = set(inspect.signature(policy.choose_action).parameters)
    score_parameters = set(inspect.signature(score_immediate_action).parameters)
    return {
        "status": (
            "PASS"
            if decision_a == decision_b
            and "latent" not in parameters
            and "observations" not in parameters
            and "latent" not in score_parameters
            and "observations" not in score_parameters
            else "FAIL"
        ),
        "decision_replay_equal": decision_a == decision_b,
        "policy_parameters": sorted(parameters),
        "score_parameters": sorted(score_parameters),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pass-id", choices=("pass1", "pass2"))
    mode.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    started = perf_counter()
    manifest = json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))
    source_manifest = load_source_manifest(ROOT / "data/manifests/source_files.json")
    expected = source_manifest.by_category("guan_external_recipe_workbook")
    source = load_guan(
        ROOT / "data/raw" / expected.expected_filename, expected=expected
    )
    factors = normalize_guan_factor_table(source)
    cohort = reconstruct_guan_cohort(source, factors=factors)
    m2 = build_m2_factor_model(cohort.eligible_recipes, factors)
    recipes = {recipe.recipe_id: recipe for recipe in cohort.eligible_recipes}
    pairs = build_within_cuisine_pairs(cohort.eligible_recipes)
    verify_identities(cohort, pairs, manifest)
    folds = build_loco_folds(cohort.eligible_recipes, pairs)
    worlds = generate_frozen_factor_worlds(m2.intervals)
    worker_count = int(os.environ.get("STAGE26_WORKERS", "4"))
    if (
        cohort.eligible_count != 61
        or len(pairs) != 222
        or len(folds) != 8
        or tuple(worlds) != SEEDS
        or manifest["configuration"]["budget"] != 2
    ):
        raise AssertionError("frozen configuration precondition failed")

    context = multiprocessing.get_context("spawn")
    if args.smoke:
        pair = min(
            pairs,
            key=lambda item: (
                len(recipes[item.recipe_a_id].ingredients)
                + len(recipes[item.recipe_b_id].ingredients)
            ),
        )
        seed = SEEDS[0]
        expected = len(POLICY_IDS) * len(REGIMES)
        with context.Pool(
            processes=1,
            initializer=initialize_worker,
            initargs=(recipes, m2, {seed: worlds[seed]}, (seed,)),
        ) as pool:
            def records():
                baseline = pool.apply(baseline_pair_worker, ((0, pair),))[1]
                mixed = pool.apply(oasa_hindsight_pair_worker, ((0, pair),))[1]
                return baseline + mixed

            first = records()
            replay = records()
        safety_fields = (
            "containment_failures", "false_direction", "budget_violation",
            "repeated_action", "post_certificate_action",
        )
        safety = {field: sum(int(row[field]) for row in first) for field in safety_fields}
        actions = sum(int(row["stopping_step"]) for row in first)
        first_actions = Counter(
            row["first_action_kind"] for row in first if row["first_action_kind"]
        )
        if (
            len(first) != expected
            or first != replay
            or any(safety.values())
            or set(first_actions) != {"SHARE", "FACTOR"}
        ):
            raise AssertionError("Stage 26 smoke failed")
        print(json.dumps({
            "mode": "smoke", "pair": pair.pair_id, "world_seed": seed,
            "trajectories": expected, "acquisitions": actions,
            "first_action_kinds": dict(first_actions),
            "deterministic_replay": True, "safety": safety,
        }, indent=2))
        return

    receipt = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if receipt["archived_manifest_sha256"] != sha256_file(FROZEN_MANIFEST):
        raise SystemExit("archived Stage 26 manifest differs from the run receipt")
    for name, digest in receipt["file_sha256"].items():
        if sha256_file(ROOT / name) != digest:
            raise SystemExit(f"Stage 26 code changed after the run receipt: {name}")
    output = FINAL_ROOT / args.pass_id
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"refusing to overwrite existing pass: {output}")
    output.mkdir(parents=True, exist_ok=True)
    worker_arguments = (recipes, m2, worlds, SEEDS)

    cuisines = tuple(sorted(cohort.cuisine_counts))
    pair_indexes_by_cuisine = {
        cuisine: np.array(
            [index for index, pair in enumerate(pairs) if pair.cuisine == cuisine],
            dtype=np.int64,
        )
        for cuisine in cuisines
    }
    baseline_arrays = np.zeros(
        (len(BASELINE_IDS), len(pairs), len(REGIMES), len(SEEDS)), dtype=np.uint8
    )
    oasa_array = np.zeros((len(pairs), len(REGIMES), len(SEEDS)), dtype=np.uint8)
    hindsight_array = np.zeros_like(oasa_array)
    first_counts: Counter[tuple[str, str, str, str]] = Counter()
    initial_or_no_action: Counter[tuple[str, str, str, str]] = Counter()
    cost_sums: Counter[tuple[str, str, str]] = Counter()
    trajectory_counts: Counter[tuple[str, str, str]] = Counter()
    budget_first_sums: Counter[tuple[str, str, str]] = Counter()
    budget_first_counts: Counter[tuple[str, str, str]] = Counter()
    tie_counts: Counter[str] = Counter()
    safety = Counter()
    records_path = output / "heldout_records.csv.gz"

    def absorb(record, pair_index, regime_index, seed_index):
        policy_id = record["policy_id"]
        if policy_id in BASELINE_IDS:
            baseline_arrays[
                BASELINE_IDS.index(policy_id), pair_index, regime_index, seed_index
            ] = int(record["terminal_certified"])
        elif policy_id == "P":
            oasa_array[pair_index, regime_index, seed_index] = int(
                record["terminal_certified"]
            )
        elif policy_id == "H":
            hindsight_array[pair_index, regime_index, seed_index] = int(
                record["terminal_certified"]
            )
        key = (policy_id, record["cuisine"], record["regime"])
        trajectory_counts[key] += 1
        cost_sums[key] += int(record["cost_spent"])
        tie_counts[policy_id] += int(record["tie_event_count"])
        if record["initial_certified"]:
            initial_or_no_action[
                (policy_id, record["cuisine"], record["regime"], "INITIAL")
            ] += 1
        elif record["no_action"]:
            initial_or_no_action[
                (policy_id, record["cuisine"], record["regime"], "NO_ACTION")
            ] += 1
        elif record["first_action_kind"]:
            first_counts[
                (
                    policy_id,
                    record["cuisine"],
                    record["regime"],
                    record["first_action_kind"],
                )
            ] += 1
        if record["budget_to_first_certificate"] != "":
            budget_first_sums[key] += int(record["budget_to_first_certificate"])
            budget_first_counts[key] += 1
        for field in (
            "containment_failures",
            "false_direction",
            "budget_violation",
            "repeated_action",
            "post_certificate_action",
        ):
            safety[field] += int(record[field])

    baseline_started = perf_counter()
    with gzip.open(records_path, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RECORD_FIELDS)
        writer.writeheader()
        with context.Pool(
            processes=worker_count, initializer=initialize_worker, initargs=worker_arguments
        ) as pool:
            results = pool.imap(baseline_pair_worker, enumerate(pairs), chunksize=1)
            for pair_index, records, values in results:
                baseline_arrays[:, pair_index, :, :] = values
                for record in records:
                    writer.writerow(record)
                    absorb(
                        record,
                        pair_index,
                        REGIMES.index(StartingShareRegime(record["regime"])),
                        int(record["seed"]) - SEEDS[0],
                    )
                if (pair_index + 1) % 20 == 0:
                    print(f"baseline pairs {pair_index + 1}/{len(pairs)}", flush=True)
    baseline_seconds = perf_counter() - baseline_started

    champion_rows, champion_indexes = write_champions(
        output / "fold_champions.csv",
        cuisines,
        baseline_arrays,
        pair_indexes_by_cuisine,
    )
    print("champions frozen", flush=True)

    policy_started = perf_counter()
    first_pair = pairs[0]
    first_recipe_a = recipes[first_pair.recipe_a_id]
    first_recipe_b = recipes[first_pair.recipe_b_id]
    leakage_state, _, _, _ = build_initial_state(
        first_recipe_a, first_recipe_b, m2, StartingShareRegime.ORDER_ONLY
    )
    initial_states_for_leakage = [leakage_state]
    with gzip.open(records_path, "at", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RECORD_FIELDS)
        with context.Pool(
            processes=worker_count, initializer=initialize_worker, initargs=worker_arguments
        ) as pool:
            results = pool.imap(
                oasa_hindsight_pair_worker, enumerate(pairs), chunksize=1
            )
            for pair_index, records, oasa_values, hindsight_values in results:
                oasa_array[pair_index, :, :] = oasa_values
                hindsight_array[pair_index, :, :] = hindsight_values
                for record in records:
                    writer.writerow(record)
                    absorb(
                        record,
                        pair_index,
                        REGIMES.index(StartingShareRegime(record["regime"])),
                        int(record["seed"]) - SEEDS[0],
                    )
                if (pair_index + 1) % 10 == 0:
                    print(f"OASA/H pairs {pair_index + 1}/{len(pairs)}", flush=True)
    policy_seconds = perf_counter() - policy_started

    champion_array = np.zeros_like(oasa_array)
    for cuisine in cuisines:
        indexes = pair_indexes_by_cuisine[cuisine]
        champion_array[indexes, :, :] = baseline_arrays[
            champion_indexes[cuisine], indexes, :, :
        ]

    coverage_rows = []
    for cuisine in cuisines:
        indexes = pair_indexes_by_cuisine[cuisine]
        for regime_index, regime in enumerate(REGIMES):
            for policy_index, policy_id in enumerate(BASELINE_IDS):
                coverage_rows.append(
                    {
                        "held_out_cuisine": cuisine,
                        "regime": regime.value,
                        "policy_id": policy_id,
                        "coverage": repr(
                            float(
                                np.mean(
                                    baseline_arrays[
                                        policy_index, indexes, regime_index, :
                                    ]
                                )
                            )
                        ),
                    }
                )
            for policy_id, values in (
                ("P", oasa_array),
                ("H", hindsight_array),
                ("CHAMPION", champion_array),
            ):
                coverage_rows.append(
                    {
                        "held_out_cuisine": cuisine,
                        "regime": regime.value,
                        "policy_id": policy_id,
                        "coverage": repr(
                            float(np.mean(values[indexes, regime_index, :]))
                        ),
                    }
                )
    with (output / "coverage_by_fold_regime.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(coverage_rows[0]))
        writer.writeheader()
        writer.writerows(coverage_rows)

    first_rows = []
    for policy_id in POLICY_IDS:
        for cuisine in cuisines:
            pair_count = len(pair_indexes_by_cuisine[cuisine])
            for regime in REGIMES:
                share = first_counts[(policy_id, cuisine, regime.value, "SHARE")]
                factor = first_counts[(policy_id, cuisine, regime.value, "FACTOR")]
                denominator = share + factor
                total = pair_count * len(SEEDS)
                initial = initial_or_no_action[
                    (policy_id, cuisine, regime.value, "INITIAL")
                ]
                no_action = initial_or_no_action[
                    (policy_id, cuisine, regime.value, "NO_ACTION")
                ]
                first_rows.append(
                    {
                        "policy_id": policy_id,
                        "held_out_cuisine": cuisine,
                        "regime": regime.value,
                        "share_first": share,
                        "factor_first": factor,
                        "acquisition_denominator": denominator,
                        "share_first_rate": (
                            "" if denominator == 0 else repr(share / denominator)
                        ),
                        "factor_first_rate": (
                            "" if denominator == 0 else repr(factor / denominator)
                        ),
                        "initially_certified": initial,
                        "no_action": no_action,
                        "excluded_rate": repr((initial + no_action) / total),
                    }
                )
    with (output / "first_action_rates.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(first_rows[0]))
        writer.writeheader()
        writer.writerows(first_rows)

    policy_arrays = {
        **{
            policy_id: baseline_arrays[index]
            for index, policy_id in enumerate(BASELINE_IDS)
        },
        "P": oasa_array,
        "H": hindsight_array,
        "CHAMPION": champion_array,
    }
    overall_coverage = {}
    regime_coverage = {}
    cuisine_coverage = {}
    for policy_id, values in policy_arrays.items():
        cuisine_means = [
            np.mean(values[pair_indexes_by_cuisine[cuisine], :, :])
            for cuisine in cuisines
        ]
        overall_coverage[policy_id] = float(np.mean(cuisine_means))
        regime_coverage[policy_id] = {
            regime.value: float(
                np.mean(
                    [
                        np.mean(
                            values[
                                pair_indexes_by_cuisine[cuisine],
                                regime_index,
                                :,
                            ]
                        )
                        for cuisine in cuisines
                    ]
                )
            )
            for regime_index, regime in enumerate(REGIMES)
        }
        cuisine_coverage[policy_id] = {
            cuisine: float(np.mean(values[pair_indexes_by_cuisine[cuisine], :, :]))
            for cuisine in cuisines
        }

    leakage = structural_leakage_check(initial_states_for_leakage)
    safety_payload = {
        **{
            field: safety[field]
            for field in (
                "containment_failures",
                "false_direction",
                "budget_violation",
                "repeated_action",
                "post_certificate_action",
            )
        },
        "leakage": leakage,
        "pass": (
            safety["containment_failures"] == 0
            and safety["false_direction"] == 0
            and safety["budget_violation"] == 0
            and safety["repeated_action"] == 0
            and safety["post_certificate_action"] == 0
            and leakage["status"] == "PASS"
        ),
    }
    (output / "safety.json").write_text(
        json.dumps(safety_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metrics = {
        "overall_coverage": overall_coverage,
        "regime_coverage": regime_coverage,
        "cuisine_coverage": cuisine_coverage,
        "primary_delta": overall_coverage["P"] - overall_coverage["CHAMPION"],
        "hindsight_regret": overall_coverage["H"] - overall_coverage["P"],
        "champions": champion_rows,
        "tie_counts": dict(sorted(tie_counts.items())),
        "total_trajectories": int(sum(trajectory_counts.values())),
        "mean_cost": {
            policy_id: float(
                sum(cost for (pid, _, _), cost in cost_sums.items() if pid == policy_id)
                / sum(
                    count
                    for (pid, _, _), count in trajectory_counts.items()
                    if pid == policy_id
                )
            )
            for policy_id in POLICY_IDS
        },
        "budget_to_first_certificate": {
            policy_id: (
                None
                if sum(
                    count
                    for (pid, _, _), count in budget_first_counts.items()
                    if pid == policy_id
                )
                == 0
                else float(
                    sum(
                        cost
                        for (pid, _, _), cost in budget_first_sums.items()
                        if pid == policy_id
                    )
                    / sum(
                        count
                        for (pid, _, _), count in budget_first_counts.items()
                        if pid == policy_id
                    )
                )
            )
            for policy_id in POLICY_IDS
        },
    }
    (output / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    np.savez_compressed(
        output / "primary_arrays.npz",
        baseline=baseline_arrays,
        oasa=oasa_array,
        hindsight=hindsight_array,
        champion=champion_array,
        pair_ids=np.array([pair.pair_id for pair in pairs]),
        pair_cuisines=np.array([pair.cuisine for pair in pairs]),
        pair_recipe_a=np.array([pair.recipe_a_id for pair in pairs]),
        pair_recipe_b=np.array([pair.recipe_b_id for pair in pairs]),
        cuisines=np.array(cuisines),
        regimes=np.array([regime.value for regime in REGIMES]),
        seeds=np.array(SEEDS),
    )
    runtime = {
        "baseline_seconds": baseline_seconds,
        "oasa_hindsight_seconds": policy_seconds,
        "total_seconds": perf_counter() - started,
    }
    (output / "runtime.json").write_text(
        json.dumps(runtime, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(runtime, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
