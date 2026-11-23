"""Conservative inverse for the frozen two-resolution half-up disclosure rule."""
from fractions import Fraction
from math import isfinite, ulp


def quid_inverse_components(published: float, n: int, i: int) -> list[tuple[float, float]]:
    """Return closures of attainable preimages for ranked share i (one-based)."""
    if not 1 <= i <= n:
        raise ValueError("Ingredient rank must be in 1..n")
    if not isfinite(published) or not 0 <= published <= 1:
        return []

    feasible_min = Fraction(1, n) if i == 1 else Fraction(0)
    feasible_max = Fraction(1, i)
    threshold = Fraction(1, 20)
    components: list[tuple[Fraction, Fraction]] = []
    for ticks, branch_min, branch_upper in ((200, Fraction(0), threshold),
                                           (100, threshold, None)):
        # Frozen publishers compute tick*step in binary floating point. Accept
        # that representation, then do all tie and feasibility checks exactly.
        center = Fraction(round(published * ticks), ticks)
        if abs(published - float(center)) > 2 * ulp(float(center)):
            continue
        half_step = Fraction(1, 2 * ticks)
        lower = max(feasible_min, branch_min, center - half_step)
        exclusive_upper = center + half_step
        if branch_upper is not None:
            exclusive_upper = min(exclusive_upper, branch_upper)
        if lower > feasible_max or lower >= exclusive_upper:
            continue
        upper = min(feasible_max, exclusive_upper)
        if components and lower <= components[-1][1]:
            previous_lower, previous_upper = components.pop()
            lower, upper = previous_lower, max(previous_upper, upper)
        components.append((lower, upper))
    return [(float(lo), float(hi)) for lo, hi in components]
