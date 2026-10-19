"""Spike test proving Hypothesis property-based testing."""

from hypothesis import given
from hypothesis import strategies as st


def trim_tail(duration: float, trim_fraction: float = 0.125) -> float:
    """Trim a fixed fraction from the end of a clip."""
    if duration <= 0.0:
        return 0.0
    return duration * (1.0 - trim_fraction)


@given(st.floats(min_value=1.0, max_value=60.0))
def test_hypothesis_trim_invariant(duration: float) -> None:
    trimmed = trim_tail(duration, 0.125)
    assert 0.0 < trimmed < duration
    assert abs(trimmed - duration * 0.875) < 1e-6
