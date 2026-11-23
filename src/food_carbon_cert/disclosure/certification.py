"""Robust certification over possibly disconnected disclosure sets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from food_carbon_cert.certification import (
    DEFAULT_ENGINEERING_TOLERANCE,
    CertificationResult,
    FoodUncertainty,
    certify_pair,
    classify_bounds,
)
from food_carbon_cert.uncertainty import FactorInterval

from .models import DisclosureSet


class InfeasibleDisclosureError(ValueError):
    """Raised when no disclosure component is feasible for a selected rank."""


@dataclass(frozen=True, slots=True)
class FoodDisclosure:
    """One food whose selected rank may have multiple share components."""

    commodity_codes: tuple[str, ...]
    rank: int
    disclosure: DisclosureSet

    def __init__(
        self,
        commodity_codes: Sequence[str],
        rank: int,
        disclosure: DisclosureSet,
    ) -> None:
        codes = tuple(commodity_codes)
        if not codes:
            raise ValueError("a food must contain at least one commodity code")
        if any(not isinstance(code, str) or not code for code in codes):
            raise ValueError("commodity codes must be nonempty strings")
        if not isinstance(disclosure, DisclosureSet):
            raise TypeError("disclosure must be a DisclosureSet")
        object.__setattr__(self, "commodity_codes", codes)
        object.__setattr__(self, "rank", rank)
        object.__setattr__(self, "disclosure", disclosure)

    @property
    def ingredient_count(self) -> int:
        """Return the number of ingredient positions."""

        return len(self.commodity_codes)

    def feasible_disclosure(self) -> DisclosureSet:
        """Return components intersected with this rank's feasible range."""

        return self.disclosure.clip_to_rank(self.ingredient_count, self.rank)


def certify_disclosure_pair(
    food_a: FoodDisclosure,
    food_b: FoodDisclosure,
    factor_intervals: Mapping[str, FactorInterval],
    *,
    tolerance: float = DEFAULT_ENGINEERING_TOLERANCE,
    metadata: Mapping[str, Any] | None = None,
) -> CertificationResult:
    """Certify over every Cartesian pair of feasible disclosure components.

    The validated single-interval oracle is called unchanged for each component
    pair. The overall lower bound is the minimum component-pair lower bound and
    the overall upper bound is the maximum component-pair upper bound, so a
    sign is certified only when it survives every component.
    """

    feasible_a = food_a.feasible_disclosure()
    feasible_b = food_b.feasible_disclosure()
    if not feasible_a:
        raise InfeasibleDisclosureError(
            "food A disclosure has no rank-feasible component"
        )
    if not feasible_b:
        raise InfeasibleDisclosureError(
            "food B disclosure has no rank-feasible component"
        )

    component_results: list[CertificationResult] = []
    vertex_counts_a: list[int] = []
    vertex_counts_b: list[int] = []
    for index_a, component_a in enumerate(feasible_a.components):
        for index_b, component_b in enumerate(feasible_b.components):
            result = certify_pair(
                FoodUncertainty(
                    food_a.commodity_codes,
                    food_a.rank,
                    float(component_a.lower),
                    float(component_a.upper),
                ),
                FoodUncertainty(
                    food_b.commodity_codes,
                    food_b.rank,
                    float(component_b.lower),
                    float(component_b.upper),
                ),
                factor_intervals,
                tolerance=tolerance,
            )
            component_results.append(result)
            if index_b == 0:
                vertex_counts_a.append(result.vertex_count_a)
            if index_a == 0:
                vertex_counts_b.append(result.vertex_count_b)

    lower_bound = min(result.lower_bound for result in component_results)
    upper_bound = max(result.upper_bound for result in component_results)
    effective_tolerance = max(result.tolerance for result in component_results)
    result_metadata = {} if metadata is None else dict(metadata)
    result_metadata["disclosure"] = {
        "component_count_a": len(feasible_a.components),
        "component_count_b": len(feasible_b.components),
        "component_pair_count": len(component_results),
        "component_bounds": [
            (result.lower_bound, result.upper_bound) for result in component_results
        ],
    }
    union_codes = set(food_a.commodity_codes) | set(food_b.commodity_codes)
    return CertificationResult(
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        decision=classify_bounds(lower_bound, upper_bound, tolerance=effective_tolerance),
        tolerance=effective_tolerance,
        vertex_count_a=sum(vertex_counts_a),
        vertex_count_b=sum(vertex_counts_b),
        union_factor_count=len(union_codes),
        evaluated_vertex_pairs=sum(
            result.evaluated_vertex_pairs for result in component_results
        ),
        metadata=result_metadata,
    )


DisclosedFood = FoodDisclosure
