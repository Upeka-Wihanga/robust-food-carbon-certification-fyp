from __future__ import annotations

from decimal import Decimal
from functools import reduce
from operator import add

from food_carbon_cert.stage26 import (
    is_major_source_ingredient,
    parse_guan_ingredient_dictionary,
)


def test_exact_five_percent_boundary_is_major() -> None:
    assert is_major_source_ingredient(Decimal("15.0"), Decimal("300.0"))


def test_fifteen_grams_is_minor_for_300_point_2_grams() -> None:
    assert not is_major_source_ingredient(Decimal("15.0"), Decimal("300.2"))


def test_fifteen_grams_is_major_for_299_point_8_grams() -> None:
    assert is_major_source_ingredient(Decimal("15.0"), Decimal("299.8"))


def test_decimal_accumulation_preserves_exact_boundary() -> None:
    ingredients = parse_guan_ingredient_dictionary(
        "{'Boundary': 15.0, 'A': 26.2, 'B': 95.9, 'C': 99.8, 'D': 63.1}"
    )
    total = sum((weight for _, weight in ingredients), Decimal("0"))

    assert total == Decimal("300.0")
    assert is_major_source_ingredient(ingredients[0][1], total)


def test_sanhe_style_fixture_documents_binary_float_failure() -> None:
    weights = (15.0, 26.2, 95.9, 99.8, 63.1)

    # Reproduce the old left-to-right float sum on Python versions whose sum()
    # uses compensated addition.
    legacy_total = reduce(add, weights, 0.0)
    assert legacy_total == 300.00000000000006
    assert weights[0] / legacy_total < 0.05

    decimal_weights = tuple(Decimal(str(value)) for value in weights)
    decimal_total = sum(decimal_weights, Decimal("0"))
    assert is_major_source_ingredient(decimal_weights[0], decimal_total)
