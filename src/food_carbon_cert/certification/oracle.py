"""Reconstructed one-rank robust certification oracle."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any

from food_carbon_cert.geometry.interval_polytope import one_rank_slab_vertices
from food_carbon_cert.uncertainty.factor_box import FactorInterval

from .certificate import CertificationResult, Decision
from .robust_bounds import calculate_robust_bounds

DEFAULT_ENGINEERING_TOLERANCE = 1e-12


@dataclass(frozen=True, slots=True)
class FoodUncertainty:
    """One food's ordered composition with one one-based rank-share interval."""

    commodity_codes: tuple[str, ...]
    rank: int
    lower_share: float
    upper_share: float
    clip_interval: bool = False

    def __init__(
        self,
        commodity_codes: Sequence[str],
        rank: int,
        lower_share: float,
        upper_share: float,
        *,
        clip_interval: bool = False,
    ) -> None:
        codes = tuple(commodity_codes)
        if not codes:
            raise ValueError("a food must contain at least one commodity code")
        if any(not isinstance(code, str) or not code for code in codes):
            raise ValueError("commodity codes must be nonempty strings")
        object.__setattr__(self, "commodity_codes", codes)
        object.__setattr__(self, "rank", rank)
        object.__setattr__(self, "lower_share", lower_share)
        object.__setattr__(self, "upper_share", upper_share)
        object.__setattr__(self, "clip_interval", clip_interval)

    @property
    def ingredient_count(self) -> int:
        """Return the number of ingredient positions."""

        return len(self.commodity_codes)


def classify_bounds(
    lower_bound: float,
    upper_bound: float,
    *,
    tolerance: float = DEFAULT_ENGINEERING_TOLERANCE,
) -> Decision:
    """Classify robust bounds using conservative strict sign conditions."""

    if not isfinite(lower_bound) or not isfinite(upper_bound):
        raise ValueError("robust bounds must be finite")
    if lower_bound > upper_bound:
        raise ValueError("lower_bound must not exceed upper_bound")
    if not isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("tolerance must be finite and nonnegative")
    if upper_bound < -tolerance:
        return Decision.A_LOWER
    if lower_bound > tolerance:
        return Decision.B_LOWER
    return Decision.ABSTAIN


def certify_pair(
    food_a: FoodUncertainty,
    food_b: FoodUncertainty,
    factor_intervals: Mapping[str, FactorInterval],
    *,
    tolerance: float = DEFAULT_ENGINEERING_TOLERANCE,
    metadata: Mapping[str, Any] | None = None,
) -> CertificationResult:
    """Certify a pair over complete one-rank interval composition polytopes."""

    vertices_a = one_rank_slab_vertices(
        food_a.ingredient_count,
        food_a.rank,
        food_a.lower_share,
        food_a.upper_share,
        clip=food_a.clip_interval,
    )
    vertices_b = one_rank_slab_vertices(
        food_b.ingredient_count,
        food_b.rank,
        food_b.lower_share,
        food_b.upper_share,
        clip=food_b.clip_interval,
    )
    union_codes = set(food_a.commodity_codes) | set(food_b.commodity_codes)
    missing_codes = union_codes.difference(factor_intervals)
    if missing_codes:
        missing = ", ".join(sorted(missing_codes))
        raise KeyError(f"missing factor intervals for commodity codes: {missing}")

    bounds = calculate_robust_bounds(
        vertices_a,
        food_a.commodity_codes,
        vertices_b,
        food_b.commodity_codes,
        factor_intervals,
    )
    if not isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("tolerance must be finite and nonnegative")
    effective_tolerance = max(tolerance, bounds.roundoff_margin)
    decision = classify_bounds(bounds.lower, bounds.upper, tolerance=effective_tolerance)
    return CertificationResult(
        lower_bound=bounds.lower,
        upper_bound=bounds.upper,
        decision=decision,
        tolerance=effective_tolerance,
        vertex_count_a=vertices_a.shape[0],
        vertex_count_b=vertices_b.shape[0],
        union_factor_count=len(union_codes),
        evaluated_vertex_pairs=bounds.evaluated_vertex_pairs,
        metadata={} if metadata is None else dict(metadata),
    )
