"""Hypothesis property tests for video duration and transition timing invariants."""

from hypothesis import given
from hypothesis import strategies as st

from smartmech.domain.concept import Keyframe, Script, ShotList, Transition


@given(
    st.lists(
        st.floats(min_value=4.0, max_value=8.0),
        min_size=5,
        max_size=5,
    )
)
def test_shot_list_duration_sum_invariant(durations: list[float]) -> None:
    keyframes = [
        Keyframe(
            index=i,
            title=f"Keyframe {i}",
            prompt="Valid construction frame",
            construction_progress_pct=i * 20.0,
        )
        for i in range(6)
    ]
    transitions = [
        Transition(
            index=i,
            from_keyframe_idx=i,
            to_keyframe_idx=i + 1,
            duration_seconds=durations[i],
            motion_prompt="Valid motion prompt transition",
        )
        for i in range(5)
    ]
    shot_list = ShotList(keyframes=keyframes, transitions=transitions)

    # Invariant: total raw duration must strictly equal the mathematical sum of all transitions
    assert abs(shot_list.total_raw_duration() - sum(durations)) < 1e-6
    assert 20.0 <= shot_list.total_raw_duration() <= 40.0


@given(
    st.integers(min_value=2, max_value=100),
    st.integers(min_value=100, max_value=200),
)
def test_script_pacing_duration_bounds(word_count: int, wpm: int) -> None:
    text = " ".join(["word"] * word_count)
    script = Script(text=text, pacing_words_per_minute=wpm)

    est_duration = script.estimated_duration_seconds()
    # Invariant: Estimated duration is always strictly positive and proportional to word count
    assert est_duration > 0.0
    assert est_duration <= (100 / 100) * 60.0
