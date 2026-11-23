from scripts.stage26.bootstrap_and_finalize import pooled_factor_first_rate


def test_pooled_switching_rate_uses_action_counts() -> None:
    rows = [
        {"factor_first": "1", "acquisition_denominator": "10"},
        {"factor_first": "90", "acquisition_denominator": "100"},
    ]
    assert pooled_factor_first_rate(rows) == 91 / 110
    assert pooled_factor_first_rate(
        [{"factor_first": "0", "acquisition_denominator": "0"}]
    ) is None
