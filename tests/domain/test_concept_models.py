"""Tests for planning domain models, invariants, and validators."""

import pytest
from pydantic import ValidationError

from smartmech.domain.concept import (
    Concept,
    Keyframe,
    Plan,
    Script,
    ShotList,
    SiteBible,
    Transition,
)


@pytest.fixture
def valid_site_bible() -> SiteBible:
    return SiteBible(
        location="Site Alpha",
        camera_rig="Fixed High Mast",
        lens="35mm Prime",
        height="20m",
        weather="Overcast",
        light_direction="North-East",
        palette=["#FFFFFF", "#000000"],
        materials=["Concrete", "Glass"],
    )


def test_site_bible_continuity_token(valid_site_bible: SiteBible) -> None:
    token = valid_site_bible.continuity_token()
    assert "Site Alpha" in token
    assert "Fixed High Mast" in token
    assert "35mm Prime" in token


def test_keyframe_prohibits_logos_and_watermarks() -> None:
    with pytest.raises(ValidationError, match="prohibited element"):
        Keyframe(
            index=0,
            title="Excavation",
            prompt="Site Alpha with corporate logo in background",
            construction_progress_pct=0.0,
        )


def test_keyframe_valid() -> None:
    kf = Keyframe(
        index=0,
        title="Excavation",
        prompt="Groundwork underway on pristine construction soil",
        construction_progress_pct=0.0,
    )
    assert kf.index == 0


def test_transition_valid_consecutive_indices() -> None:
    tr = Transition(
        index=0,
        from_keyframe_idx=0,
        to_keyframe_idx=1,
        duration_seconds=6.0,
        motion_prompt="Timelapse transition showing steel frame erection",
    )
    assert tr.duration_seconds == 6.0


def test_transition_rejects_non_consecutive_indices() -> None:
    with pytest.raises(ValidationError, match="consecutive keyframes"):
        Transition(
            index=0,
            from_keyframe_idx=0,
            to_keyframe_idx=2,  # Invalid jump
            duration_seconds=6.0,
            motion_prompt="Invalid skip transition",
        )

    with pytest.raises(ValidationError, match="Transition index must match"):
        Transition(
            index=1,
            from_keyframe_idx=0,
            to_keyframe_idx=1,
            duration_seconds=6.0,
            motion_prompt="Index mismatch transition",
        )


def test_shot_list_must_have_exactly_6_keyframes_and_5_transitions() -> None:
    # 5 keyframes instead of 6
    keyframes = [
        Keyframe(
            index=i,
            title=f"Keyframe {i}",
            prompt="Valid prompt text",
            construction_progress_pct=i * 20.0,
        )
        for i in range(5)
    ]
    transitions = [
        Transition(
            index=i,
            from_keyframe_idx=i,
            to_keyframe_idx=i + 1,
            duration_seconds=7.0,
            motion_prompt="Valid motion text",
        )
        for i in range(4)
    ]
    with pytest.raises(ValidationError, match="exactly 6 keyframes"):
        ShotList(keyframes=keyframes, transitions=transitions)


def test_shot_list_indices_order() -> None:
    # 6 keyframes with scrambled indices
    keyframes = [
        Keyframe(
            index=5 - i,
            title=f"Keyframe {i}",
            prompt="Valid prompt text",
            construction_progress_pct=i * 20.0,
        )
        for i in range(6)
    ]
    transitions = [
        Transition(
            index=i,
            from_keyframe_idx=i,
            to_keyframe_idx=i + 1,
            duration_seconds=7.0,
            motion_prompt="Valid motion text",
        )
        for i in range(5)
    ]
    with pytest.raises(ValidationError, match="invalid index"):
        ShotList(keyframes=keyframes, transitions=transitions)


def test_script_word_count_limit() -> None:
    too_long = " ".join(["construction"] * 105)
    with pytest.raises(ValidationError, match="exceeds 100 words"):
        Script(text=too_long)

    valid_text = " ".join(["engineering"] * 50)
    script = Script(text=valid_text)
    assert script.word_count == 50
    assert script.estimated_duration_seconds() > 0


def test_plan_requires_verbatim_continuity_in_every_keyframe(valid_site_bible: SiteBible) -> None:
    concept = Concept(title="Build", premise="Valid premise text", building_type="Office")

    # Missing location
    keyframes_no_loc = [
        Keyframe(
            index=i,
            title=f"Keyframe {i}",
            prompt="Fixed High Mast and 35mm Prime without location",
            construction_progress_pct=i * 20.0,
        )
        for i in range(6)
    ]
    transitions = [
        Transition(
            index=i,
            from_keyframe_idx=i,
            to_keyframe_idx=i + 1,
            duration_seconds=7.0,
            motion_prompt="Valid motion text",
        )
        for i in range(5)
    ]
    shot_list = ShotList(keyframes=keyframes_no_loc, transitions=transitions)
    script = Script(text="Short valid voiceover script.")

    with pytest.raises(ValidationError, match="location 'Site Alpha' verbatim"):
        Plan(concept=concept, site_bible=valid_site_bible, shot_list=shot_list, script=script)

    # Missing lens
    keyframes_no_lens = [
        Keyframe(
            index=i,
            title=f"Keyframe {i}",
            prompt="Site Alpha and Fixed High Mast without lens",
            construction_progress_pct=i * 20.0,
        )
        for i in range(6)
    ]
    shot_list_no_lens = ShotList(keyframes=keyframes_no_lens, transitions=transitions)
    with pytest.raises(ValidationError, match="lens '35mm Prime' verbatim"):
        Plan(
            concept=concept, site_bible=valid_site_bible, shot_list=shot_list_no_lens, script=script
        )

    # Missing rig
    keyframes_no_rig = [
        Keyframe(
            index=i,
            title=f"Keyframe {i}",
            prompt="Site Alpha and 35mm Prime without rig",
            construction_progress_pct=i * 20.0,
        )
        for i in range(6)
    ]
    shot_list_no_rig = ShotList(keyframes=keyframes_no_rig, transitions=transitions)
    with pytest.raises(ValidationError, match="camera rig 'Fixed High Mast' verbatim"):
        Plan(
            concept=concept, site_bible=valid_site_bible, shot_list=shot_list_no_rig, script=script
        )
