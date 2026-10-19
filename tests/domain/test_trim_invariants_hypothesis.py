"""Hypothesis property tests for tail-trim invariants."""

from hypothesis import given
from hypothesis import strategies as st

from smartmech.domain.strategy import TailTrimPolicy


@given(
    st.floats(min_value=1.0, max_value=60.0),
    st.floats(min_value=0.05, max_value=0.30),
)
def test_tail_trim_invariants(raw_duration: float, trim_fraction: float) -> None:
    policy = TailTrimPolicy(trim_fraction=trim_fraction)

    trimmed = policy.calculate_trimmed_duration(raw_duration)
    trimmed_seconds = policy.calculate_trim_seconds(raw_duration)

    # Invariants:
    # 1. Trimmed duration + trimmed seconds strictly equals raw duration
    assert abs((trimmed + trimmed_seconds) - raw_duration) < 1e-6

    # 2. Trimmed duration is strictly less than raw duration and strictly positive
    assert 0.0 < trimmed < raw_duration

    # 3. Default trim fraction 12.5% preserves 87.5% of duration
    default_policy = TailTrimPolicy()
    assert (
        abs(default_policy.calculate_trimmed_duration(raw_duration) - (raw_duration * 0.875)) < 1e-6
    )
