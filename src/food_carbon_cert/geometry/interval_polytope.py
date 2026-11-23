"""Complete one-rank slab intersections of the ordered simplex."""

from __future__ import annotations

from itertools import combinations
from math import isfinite

import numpy as np
from numpy.typing import NDArray

from .ordered_simplex import ordered_simplex_vertices, rank_feasible_interval
from .vertices import is_ordered_simplex_point


class InfeasibleRankIntervalError(ValueError):
    """Raised when a rank-share interval has no valid requested interpretation."""


def _validated_interval(
    ingredient_count: int,
    rank: int,
    lower: float,
    upper: float,
    *,
    clip: bool,
    atol: float,
) -> tuple[float, float]:
    if not isfinite(lower) or not isfinite(upper):
        raise ValueError("rank interval bounds must be finite")
    if lower > upper:
        raise ValueError("rank interval lower bound must not exceed its upper bound")
    if atol < 0.0:
        raise ValueError("atol must be nonnegative")

    feasible_lower, feasible_upper = rank_feasible_interval(ingredient_count, rank)
    if clip:
        clipped_lower = max(lower, feasible_lower)
        clipped_upper = min(upper, feasible_upper)
        if clipped_lower > clipped_upper:
            raise InfeasibleRankIntervalError(
                "rank interval does not intersect the rank-feasible range"
            )
        return clipped_lower, clipped_upper

    if lower < feasible_lower - atol or upper > feasible_upper + atol:
        raise InfeasibleRankIntervalError(
            "rank interval extends outside the feasible range; pass clip=True "
            "to request explicit clipping"
        )
    clipped_lower = max(lower, feasible_lower)
    clipped_upper = min(upper, feasible_upper)
    if clipped_lower > clipped_upper:
        raise InfeasibleRankIntervalError(
            "rank interval does not intersect the rank-feasible range"
        )
    return clipped_lower, clipped_upper


def one_rank_slab_vertices(
    ingredient_count: int,
    rank: int,
    lower: float,
    upper: float,
    *,
    clip: bool = False,
    atol: float = 1e-12,
) -> NDArray[np.float64]:
    """Enumerate every vertex of an ordered simplex intersected by one rank slab.

    Public ranks are one-based, matching the research documents. The complete
    construction retains original simplex vertices inside the slab and adds
    intersections of every original simplex edge with each slab boundary.

    Args:
        ingredient_count: Number of ordered ingredient positions.
        rank: One-based ingredient rank constrained by the disclosure.
        lower: Inclusive lower share bound for the selected rank.
        upper: Inclusive upper share bound for the selected rank.
        clip: Explicitly clip the interval to the rank-feasible range. Without
            this flag, an interval extending outside that range is rejected.
        atol: Numerical tolerance for validating computed compositions.

    Returns:
        A two-dimensional array containing every distinct slab-polytope vertex.

    Raises:
        InfeasibleRankIntervalError: If the requested interval is infeasible.
    """

    lower, upper = _validated_interval(
        ingredient_count, rank, lower, upper, clip=clip, atol=atol
    )
    coordinate = rank - 1
    simplex_vertices = ordered_simplex_vertices(ingredient_count)
    candidates: list[NDArray[np.float64]] = []

    for vertex in simplex_vertices:
        value = vertex[coordinate]
        if lower <= value <= upper:
            candidates.append(vertex)

    boundaries = (lower,) if lower == upper else (lower, upper)
    for left_index, right_index in combinations(range(ingredient_count), 2):
        left = simplex_vertices[left_index]
        right = simplex_vertices[right_index]
        left_value = left[coordinate]
        right_value = right[coordinate]
        difference = right_value - left_value
        if difference == 0.0:
            continue

        for boundary in boundaries:
            if min(left_value, right_value) < boundary < max(left_value, right_value):
                interpolation = (boundary - left_value) / difference
                candidates.append(left + interpolation * (right - left))

    if not candidates:
        raise InfeasibleRankIntervalError("rank interval has no feasible composition")
    # A feasible vertex must never be removed just because it is close to another
    # vertex. Even small differences can change a strict robust sign.
    vertices = np.unique(np.vstack(candidates), axis=0)
    if any(
        not is_ordered_simplex_point(vertex, atol=atol)
        or not lower - atol <= vertex[coordinate] <= upper + atol
        for vertex in vertices
    ):
        raise ArithmeticError("rank slab vertex failed numerical feasibility validation")
    return vertices
