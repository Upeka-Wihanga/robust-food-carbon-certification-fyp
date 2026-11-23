from __future__ import annotations

import random

import numpy as np
import pytest

from food_carbon_cert.certification import calculate_robust_bounds
from food_carbon_cert.uncertainty import FactorInterval, fixed_composition_bounds


def _reference_bounds(
    vertices_a: np.ndarray,
    codes_a: tuple[str, ...],
    vertices_b: np.ndarray,
    codes_b: tuple[str, ...],
    intervals: dict[str, FactorInterval],
) -> tuple[float, float]:
    bounds = [
        fixed_composition_bounds(
            vertex_a,
            codes_a,
            vertex_b,
            codes_b,
            intervals,
        )
        for vertex_a in vertices_a
        for vertex_b in vertices_b
    ]
    return min(lower for lower, _ in bounds), max(upper for _, upper in bounds)


def test_vectorized_bounds_match_reference_loop_on_random_repeated_keys() -> None:
    generator = random.Random(26026)
    numpy_generator = np.random.default_rng(26026)

    for _ in range(100):
        ingredient_count_a = generator.randint(2, 8)
        ingredient_count_b = generator.randint(2, 8)
        vertex_count_a = generator.randint(1, 20)
        vertex_count_b = generator.randint(1, 20)
        key_count = generator.randint(2, 6)
        keys = tuple(f"k{index}" for index in range(key_count))
        codes_a = tuple(generator.choice(keys) for _ in range(ingredient_count_a))
        codes_b = tuple(generator.choice(keys) for _ in range(ingredient_count_b))
        vertices_a = numpy_generator.dirichlet(
            np.ones(ingredient_count_a), size=vertex_count_a
        )
        vertices_b = numpy_generator.dirichlet(
            np.ones(ingredient_count_b), size=vertex_count_b
        )
        intervals = {
            key: FactorInterval(
                lower := generator.uniform(0.0, 5.0),
                lower + generator.uniform(0.0, 5.0),
            )
            for key in keys
        }

        optimized = calculate_robust_bounds(
            vertices_a, codes_a, vertices_b, codes_b, intervals
        )
        reference_lower, reference_upper = _reference_bounds(
            vertices_a, codes_a, vertices_b, codes_b, intervals
        )

        assert optimized.lower == pytest.approx(reference_lower, abs=1e-12)
        assert optimized.upper == pytest.approx(reference_upper, abs=1e-12)
        assert optimized.evaluated_vertex_pairs == vertex_count_a * vertex_count_b
