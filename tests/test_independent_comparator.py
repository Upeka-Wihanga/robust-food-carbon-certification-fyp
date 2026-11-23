from __future__ import annotations

import numpy as np

from food_carbon_cert.certification import (
    DEFAULT_ENGINEERING_TOLERANCE,
    FoodUncertainty,
    certify_pair,
)
from food_carbon_cert.uncertainty import FactorInterval
from tests.helpers.independent_lp import (
    independent_classification,
    independent_lp_bounds,
)


def _random_slab(
    rng: np.random.Generator, ingredient_count: int, rank: int, case: int
) -> tuple[float, float]:
    feasible_lower = 1.0 / ingredient_count if rank == 1 else 0.0
    feasible_upper = 1.0 / rank
    center = float(rng.uniform(feasible_lower, feasible_upper))
    if case % 10 == 0:
        return center, center
    half_width = float(rng.uniform(0.0, 0.3 * (feasible_upper - feasible_lower)))
    return max(feasible_lower, center - half_width), min(
        feasible_upper, center + half_width
    )


def test_vertex_oracle_matches_independent_lp_factor_corner_comparator() -> None:
    rng = np.random.default_rng(14001724)
    case_count = 100
    classification_mismatches = 0
    maximum_lower_error = 0.0
    maximum_upper_error = 0.0

    for case in range(case_count):
        count_a = int(rng.integers(2, 6))
        count_b = int(rng.integers(2, 6))
        rank_a = int(rng.integers(1, count_a + 1))
        rank_b = int(rng.integers(1, count_b + 1))
        lower_a, upper_a = _random_slab(rng, count_a, rank_a, case)
        lower_b, upper_b = _random_slab(rng, count_b, rank_b, case + 3)

        codes_a = tuple(
            f"a{int(rng.integers(0, max(2, count_a - 1)))}" for _ in range(count_a)
        )
        codes_b_list: list[str] = []
        for index in range(count_b):
            if index == 0 or rng.random() < 0.45:
                codes_b_list.append(codes_a[int(rng.integers(0, count_a))])
            else:
                codes_b_list.append(f"b{int(rng.integers(0, max(2, count_b - 1)))}")
        codes_b = tuple(codes_b_list)

        factor_intervals: dict[str, FactorInterval] = {}
        for code in sorted(set(codes_a) | set(codes_b)):
            lower = float(rng.uniform(0.01, 4.0))
            factor_intervals[code] = FactorInterval(
                lower, lower + float(rng.uniform(0.01, 4.0))
            )

        food_a = FoodUncertainty(codes_a, rank_a, lower_a, upper_a)
        food_b = FoodUncertainty(codes_b, rank_b, lower_b, upper_b)
        production = certify_pair(food_a, food_b, factor_intervals)
        independent = independent_lp_bounds(food_a, food_b, factor_intervals)
        independent_decision = independent_classification(
            independent, tolerance=DEFAULT_ENGINEERING_TOLERANCE
        )

        lower_error = abs(production.lower_bound - independent.lower)
        upper_error = abs(production.upper_bound - independent.upper)
        maximum_lower_error = max(maximum_lower_error, lower_error)
        maximum_upper_error = max(maximum_upper_error, upper_error)
        classification_mismatches += production.decision is not independent_decision
        assert np.isclose(production.lower_bound, independent.lower, rtol=0.0, atol=1e-8)
        assert np.isclose(production.upper_bound, independent.upper, rtol=0.0, atol=1e-8)
        assert production.decision is independent_decision

    print(
        "independent-comparator summary: "
        f"cases={case_count}, "
        f"classification_mismatches={classification_mismatches}, "
        f"maximum_lower_error={maximum_lower_error:.17g}, "
        f"maximum_upper_error={maximum_upper_error:.17g}"
    )
