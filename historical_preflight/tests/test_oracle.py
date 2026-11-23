"""Check the historical implementation against an independent factor-corner LP."""
from itertools import product
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.optimize import linprog

from preflight.quid import quid_inverse_components

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evidence/frozen/stage18/portable/"
                       "Stage18_Portable_Reproduction/scripts"))
import corrected_oracle as oracle


def lp_span(codes, rank, interval, factors):
    n = len(codes)
    coefficients = np.array([factors[code] for code in codes])
    order = np.diff(np.eye(n), axis=0)
    variable_bounds = [(0, None)] * n
    variable_bounds[rank - 1] = interval
    args = dict(A_ub=order if n > 1 else None,
                b_ub=np.zeros(n - 1) if n > 1 else None,
                A_eq=np.ones((1, n)), b_eq=[1], bounds=variable_bounds)
    lower = linprog(coefficients, **args)
    upper = linprog(-coefficients, **args)
    assert lower.success and upper.success
    return lower.fun, -upper.fun


def reference(ca, cb, ia, ib, ra, rb, factors, radius):
    keys = sorted(set(ca) | set(cb))
    corners = [[factors[k] * (1 - radius), factors[k] * (1 + radius)] for k in keys]
    spans = []
    for values in product(*(sorted(set(c)) for c in corners)):
        corner = dict(zip(keys, values))
        amin, amax = lp_span(ca, ra, ia, corner)
        bmin, bmax = lp_span(cb, rb, ib, corner)
        spans.append((amin - bmax, amax - bmin))
    return min(v[0] for v in spans), max(v[1] for v in spans)


def evaluated(ca, cb, ia, ib, ra, rb, factors, radius):
    _, index, means = oracle.pair_union(
        ca, [factors[k] for k in ca], cb, [factors[k] for k in cb]
    )
    a = oracle.aggregate_vertices(oracle.interval_vertices(len(ca), ra, *ia), ca, index)
    b = oracle.aggregate_vertices(oracle.interval_vertices(len(cb), rb, *ib), cb, index)
    return oracle.robust_bounds_from_arrays(a, b, means, radius)


def draw_recipe(rng, index):
    n = int(rng.integers(1, 6))
    codes = rng.integers(0, 3, n).tolist()
    rank = int(rng.integers(1, n + 1))
    share = sorted(rng.dirichlet(np.ones(n)), reverse=True)[rank - 1]
    share = float(share)
    interval = (share, share) if index % 5 == 0 else (share * .9, min(1, share + .1))
    return codes, rank, interval


@pytest.mark.parametrize("seed", [27, 1805, 20261123])
def test_randomized_bounds(seed):
    rng = np.random.default_rng(seed)
    for index in range(40):
        ca, ra, ia = draw_recipe(rng, index)
        cb, rb, ib = draw_recipe(rng, index)
        factors = dict(enumerate(rng.uniform(.2, 4, 3)))
        radius = .25 if index % 2 else 0
        want = reference(ca, cb, ia, ib, ra, rb, factors, radius)
        got = evaluated(ca, cb, ia, ib, ra, rb, factors, radius)
        assert got == pytest.approx(want, abs=1e-9)
        assert evaluated(ca, cb, ia, ib, ra, rb, factors, radius) == got
        assert oracle.cert_direction(*got) == oracle.cert_direction(*want)


def test_shared_and_repeated_commodity_cancels():
    assert evaluated([0, 0], [0], (.5, 1), (1, 1), 1, 1, {0: 9}, .25) == (0, 0)
    assert oracle.cert_direction(0, 0) == "ABSTAIN"
    with pytest.raises(ValueError, match="factor mismatch"):
        oracle.pair_union([0], [1.0], [0], [2.0])
    with pytest.raises(KeyError):
        evaluated([0], [1], (1, 1), (1, 1), 1, 1, {0: 9}, .25)


def test_geometry_contains_ties_zeros_and_rejects_conflict():
    assert not oracle.interval_vertices(3, 1, 0, .2)
    assert not oracle.interval_vertices(3, 2, .3, .2)
    for vertex in oracle.interval_vertices(3, 3, 0, 0):
        assert sum(vertex) == pytest.approx(1)
        assert list(vertex) == sorted(vertex, reverse=True)
        assert vertex[-1] == 0
    vertices = oracle.interval_vertices(3, 2, .325, .335)
    assert any(np.allclose(v, [1/3, 1/3, 1/3]) for v in vertices)
    case = oracle.reviewer_counterexample()
    assert case["correct_dir"] == "ABSTAIN"
    assert case["old_corner_dir"] == "A"


def test_genuinely_nested_disclosure_preserves_certificate():
    ca, cb = [0, 1], [2]
    factors = {0: 1, 1: 2, 2: 10}
    wide = evaluated(ca, cb, (.5, 1), (1, 1), 1, 1, factors, .25)
    narrow = evaluated(ca, cb, (.7, .8), (1, 1), 1, 1, factors, .25)
    assert wide[0] <= narrow[0] <= narrow[1] <= wide[1]
    assert oracle.cert_direction(*wide) == oracle.cert_direction(*narrow) == "A"
    assert oracle.cert_direction(-1e-10, -1e-10) == "ABSTAIN"


@pytest.mark.parametrize("published,n,rank", [(.12, 8, 1), (0, 400, 1), (.055, 2, 2)])
def test_impossible_half_up_observation(published, n, rank):
    assert quid_inverse_components(published, n, rank) == []


def test_changing_resolution_and_boundaries():
    assert quid_inverse_components(.045, 3, 2) == [(.0425, .0475)]
    assert quid_inverse_components(.05, 3, 2) == [(.0475, .055)]
    assert quid_inverse_components(1, 1, 1) == [(1, 1)]
    assert quid_inverse_components(0, 3, 3) == [(0, .0025)]
    assert quid_inverse_components(float("nan"), 3, 3) == []
    with pytest.raises(ValueError):
        quid_inverse_components(.05, 3, 0)


@pytest.mark.parametrize("n", [2, 5, 8, 20, 37, 400])
def test_published_shares_are_contained(n):
    for i in sorted({1, min(n, 2), n}):
        lo, hi = (1 / n if i == 1 else 0), 1 / i
        for share in np.linspace(lo, hi, 801):
            publication = oracle.quid_publish(share)
            result = quid_inverse_components(publication, n, i)
            assert any(a - 1e-14 <= share <= b + 1e-14 for a, b in result)
