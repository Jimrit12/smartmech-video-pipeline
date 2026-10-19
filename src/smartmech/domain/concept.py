"""Planning domain entities, schemas, and continuity invariants."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SiteBible(BaseModel):
    """Immutable bible specifying fixed physical site attributes and continuity constraints."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    location: str = Field(min_length=3)
    camera_rig: str = Field(min_length=3)
    lens: str = Field(min_length=2)
    height: str = Field(min_length=2)
    weather: str = Field(min_length=3)
    light_direction: str = Field(min_length=3)
    palette: list[str] = Field(min_length=1)
    materials: list[str] = Field(min_length=1)

    def continuity_token(self) -> str:
        """Canonical string containing all physical continuity requirements."""
        return (
            f"Location: {self.location} | Rig: {self.camera_rig} | Lens: {self.lens} | "
            f"Height: {self.height} | Weather: {self.weather} | Light: {self.light_direction} | "
            f"Materials: {', '.join(self.materials)}"
        )


class Keyframe(BaseModel):
    """One of exactly six keyframe stages in the construction timelapse."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: int = Field(ge=0, le=5)
    title: str = Field(min_length=3)
    prompt: str = Field(min_length=10)
    construction_progress_pct: float = Field(ge=0.0, le=100.0)

    @field_validator("prompt")
    @classmethod
    def validate_no_prohibited_elements(cls, v: str) -> str:
        lower = v.lower()
        prohibited = ["logo", "watermark", "readable text", "letters", "close-up face", "billboard"]
        for item in prohibited:
            if item in lower:
                raise ValueError(f"Prompt contains prohibited element: '{item}'")
        return v


class Transition(BaseModel):
    """Transition video clip connecting consecutive keyframes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: int = Field(ge=0, le=4)
    from_keyframe_idx: int = Field(ge=0, le=4)
    to_keyframe_idx: int = Field(ge=1, le=5)
    duration_seconds: float = Field(ge=4.0, le=10.0)
    motion_prompt: str = Field(min_length=10)

    @model_validator(mode="after")
    def validate_indices(self) -> "Transition":
        if self.to_keyframe_idx != self.from_keyframe_idx + 1:
            raise ValueError(
                f"Transition must connect consecutive keyframes (got {self.from_keyframe_idx} -> {self.to_keyframe_idx})"
            )
        if self.index != self.from_keyframe_idx:
            raise ValueError(
                f"Transition index must match from_keyframe_idx ({self.index} != {self.from_keyframe_idx})"
            )
        return self


class ShotList(BaseModel):
    """Complete shot list containing exactly 6 keyframes and 5 transitions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    keyframes: list[Keyframe]
    transitions: list[Transition]

    @model_validator(mode="after")
    def validate_structure(self) -> "ShotList":
        if len(self.keyframes) != 6:
            raise ValueError(
                f"ShotList must contain exactly 6 keyframes, got {len(self.keyframes)}"
            )
        if len(self.transitions) != 5:
            raise ValueError(
                f"ShotList must contain exactly 5 transitions, got {len(self.transitions)}"
            )

        for i, kf in enumerate(self.keyframes):
            if kf.index != i:
                raise ValueError(f"Keyframe at position {i} has invalid index {kf.index}")

        for i, tr in enumerate(self.transitions):
            if tr.index != i:
                raise ValueError(f"Transition at position {i} has invalid index {tr.index}")

        return self

    def total_raw_duration(self) -> float:
        return sum(t.duration_seconds for t in self.transitions)


class Script(BaseModel):
    """Spoken voiceover narrative constrained to <= 100 words."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(min_length=5)
    pacing_words_per_minute: int = Field(default=150, ge=100, le=220)

    @property
    def word_count(self) -> int:
        words = re.findall(r"\b\w+\b", self.text)
        return len(words)

    @model_validator(mode="after")
    def validate_word_count(self) -> "Script":
        count = self.word_count
        if count > 100:
            raise ValueError(f"Script exceeds 100 words limit (contains {count} words)")
        return self

    def estimated_duration_seconds(self) -> float:
        return (self.word_count / self.pacing_words_per_minute) * 60.0


class Concept(BaseModel):
    """High-level architectural concept and storyline."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(min_length=3)
    premise: str = Field(min_length=10)
    building_type: str = Field(min_length=3)
    target_duration_seconds: float = Field(default=35.0, ge=30.0, le=40.0)


class Plan(BaseModel):
    """Aggregate plan combining concept, site bible, shot list, and voiceover script."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    concept: Concept
    site_bible: SiteBible
    shot_list: ShotList
    script: Script

    @model_validator(mode="after")
    def validate_continuity_fields(self) -> "Plan":
        """Verify that every keyframe prompt repeats continuity fields verbatim."""
        loc = self.site_bible.location
        lens = self.site_bible.lens
        rig = self.site_bible.camera_rig

        for kf in self.shot_list.keyframes:
            prompt = kf.prompt
            if loc not in prompt:
                raise ValueError(
                    f"Keyframe {kf.index} prompt does not contain location '{loc}' verbatim"
                )
            if lens not in prompt:
                raise ValueError(
                    f"Keyframe {kf.index} prompt does not contain lens '{lens}' verbatim"
                )
            if rig not in prompt:
                raise ValueError(
                    f"Keyframe {kf.index} prompt does not contain camera rig '{rig}' verbatim"
                )

        return self
