from fractions import Fraction

import pytest

from food_carbon_cert.certification import Decision, FoodUncertainty, certify_pair
from food_carbon_cert.disclosure import ShareInterval
from food_carbon_cert.geometry.interval_polytope import (
    InfeasibleRankIntervalError,
    one_rank_slab_vertices,
)
from food_carbon_cert.uncertainty import FactorInterval
from food_carbon_cert.stage26.policies import state_value
from food_carbon_cert.stage26.state import (
    Stage26FoodState,
    Stage26PairState,
    certify_stage26_state,
)


def test_sub_picounit_interval_keeps_both_certificate_endpoints() -> None:
    lower, point, upper = 0.6, 0.6 + 3e-13, 0.6 + 7e-13
    codes = ("high", "low")
    result = certify_pair(
        FoodUncertainty(codes, 1, lower, upper),
        FoodUncertainty(codes, 1, point, point),
        {"high": FactorInterval(10, 10), "low": FactorInterval(0, 0)},
    )
    # For two shares with factors 10 and 0, D is exactly 10 * (x_A - x_B).
    assert result.lower_bound == float(10 * (Fraction(lower) - Fraction(point)))
    assert result.upper_bound == float(10 * (Fraction(upper) - Fraction(point)))
    assert result.decision is Decision.ABSTAIN


def test_identical_shared_factor_cancels_at_large_scale() -> None:
    result = certify_pair(
        FoodUncertainty(("same",) * 6, 1, 1 / 6, 1 / 6),
        FoodUncertainty(("same",), 1, 1, 1),
        {"same": FactorInterval(1e16, 2e16)},
    )
    assert (result.lower_bound, result.upper_bound) == (0.0, 0.0)
    assert result.decision is Decision.ABSTAIN


def test_interval_just_outside_feasibility_raises() -> None:
    with pytest.raises(InfeasibleRankIntervalError):
        one_rank_slab_vertices(2, 1, 0.5 - 5e-13, 0.5 - 1e-13, clip=True)


def test_roundoff_margin_reaches_disclosure_and_policy_scoring() -> None:
    state = Stage26PairState(
        Stage26FoodState("a", ("a",) * 6, 1, ShareInterval.point(1 / 6)),
        Stage26FoodState("b", ("b",), 1, ShareInterval.point(1)),
        {"a": FactorInterval(1e16, 1e16), "b": FactorInterval(1e16, 1e16)},
        frozenset(),
        budget=2,
    )
    certificate = certify_stage26_state(state)
    assert certificate.decision is Decision.ABSTAIN
    assert certificate.tolerance > 1e-12
    assert not state_value(state).certified
