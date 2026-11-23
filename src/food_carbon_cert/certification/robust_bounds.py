"""Whole-polytope robust endpoint calculation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from sys import float_info

import numpy as np
from numpy.typing import ArrayLike

from food_carbon_cert.uncertainty.factor_box import FactorInterval


@dataclass(frozen=True, slots=True)
class RobustBounds:
    """Extrema and audit counts for a complete pairwise uncertainty set."""

    lower: float
    upper: float
    evaluated_vertex_pairs: int
    roundoff_margin: float = 0.0


def calculate_robust_bounds(
    vertices_a: ArrayLike,
    commodity_codes_a: Sequence[str],
    vertices_b: ArrayLike,
    commodity_codes_b: Sequence[str],
    factor_intervals: Mapping[str, FactorInterval],
) -> RobustBounds:
    """Evaluate robust bounds over normalized composition-vertex pairs."""

    array_a = np.asarray(vertices_a, dtype=np.float64)
    array_b = np.asarray(vertices_b, dtype=np.float64)
    if array_a.ndim != 2 or array_b.ndim != 2:
        raise ValueError("composition vertices must be two-dimensional arrays")
    if array_a.shape[0] == 0 or array_b.shape[0] == 0:
        raise ValueError("each food must have at least one feasible vertex")
    if array_a.shape[1] != len(commodity_codes_a):
        raise ValueError("food A vertex width does not match its commodity codes")
    if array_b.shape[1] != len(commodity_codes_b):
        raise ValueError("food B vertex width does not match its commodity codes")

    ordered_codes = tuple(dict.fromkeys((*commodity_codes_a, *commodity_codes_b)))
    missing = set(ordered_codes).difference(factor_intervals)
    if missing:
        raise KeyError(
            f"missing factor intervals for commodity codes: {sorted(missing)}"
        )
    evaluated_pairs = int(array_a.shape[0] * array_b.shape[0])
    if len(ordered_codes) == 1:
        # Both normalized foods have exactly unit mass on the same factor.
        return RobustBounds(0.0, 0.0, evaluated_pairs)
    code_indexes = {code: index for index, code in enumerate(ordered_codes)}

    aggregated_a = np.zeros((array_a.shape[0], len(ordered_codes)), dtype=np.float64)
    for ingredient_index, code in enumerate(commodity_codes_a):
        aggregated_a[:, code_indexes[code]] += array_a[:, ingredient_index]
    aggregated_b = np.zeros((array_b.shape[0], len(ordered_codes)), dtype=np.float64)
    for ingredient_index, code in enumerate(commodity_codes_b):
        aggregated_b[:, code_indexes[code]] += array_b[:, ingredient_index]

    differences = aggregated_a[:, np.newaxis, :] - aggregated_b[np.newaxis, :, :]
    lowers = np.array(
        [factor_intervals[code].lower for code in ordered_codes], dtype=np.float64
    )
    uppers = np.array(
        [factor_intervals[code].upper for code in ordered_codes], dtype=np.float64
    )
    factor_scale = max(float(np.max(np.abs(lowers))), float(np.max(np.abs(uppers))))
    operations = 8 + 4 * (array_a.shape[1] + array_b.shape[1])
    roundoff_margin = factor_scale * (float_info.epsilon * operations)
    pair_lowers = np.sum(
        np.where(differences >= 0.0, differences * lowers, differences * uppers),
        axis=2,
    )
    pair_uppers = np.sum(
        np.where(differences >= 0.0, differences * uppers, differences * lowers),
        axis=2,
    )
    return RobustBounds(
        float(np.min(pair_lowers)),
        float(np.max(pair_uppers)),
        evaluated_pairs,
        roundoff_margin,
    )
