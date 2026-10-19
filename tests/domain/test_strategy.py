"""Tests for tail trim policy edge cases and chaining strategies."""

from smartmech.domain.strategy import ChainStrategy, TailTrimPolicy


def test_tail_trim_policy_non_positive_duration() -> None:
    policy = TailTrimPolicy(trim_fraction=0.125)
    assert policy.calculate_trimmed_duration(0.0) == 0.0
    assert policy.calculate_trimmed_duration(-5.0) == 0.0
    assert policy.calculate_trim_seconds(0.0) == 0.0
    assert policy.calculate_trim_seconds(-5.0) == 0.0


def test_chain_strategies_enum() -> None:
    assert ChainStrategy.ANCHOR_PARALLEL == "ANCHOR_PARALLEL"
    assert ChainStrategy.FIRST_LAST == "FIRST_LAST"
    assert ChainStrategy.TAIL_HANDOFF == "TAIL_HANDOFF"
