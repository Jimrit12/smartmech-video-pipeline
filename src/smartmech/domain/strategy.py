"""Chaining strategies and tail-trim policies."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ChainStrategy(StrEnum):
    """Transition generation chaining strategy."""

    ANCHOR_PARALLEL = (
        "ANCHOR_PARALLEL"  # Default: all transitions generated in parallel against keyframe anchors
    )
    FIRST_LAST = "FIRST_LAST"  # First and last frames supplied as constraints
    TAIL_HANDOFF = "TAIL_HANDOFF"  # Sequential generation where tail of prior clip feeds next


class TailTrimPolicy(BaseModel):
    """Policy for trimming the unstable ending (tail) of AI-generated video clips."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    trim_fraction: float = Field(default=0.125, ge=0.0, le=0.5)  # 12.5% default

    def calculate_trimmed_duration(self, raw_duration: float) -> float:
        """Calculate clip duration after applying tail trim."""
        if raw_duration <= 0.0:
            return 0.0
        return raw_duration * (1.0 - self.trim_fraction)

    def calculate_trim_seconds(self, raw_duration: float) -> float:
        """Calculate exact seconds trimmed from the end."""
        if raw_duration <= 0.0:
            return 0.0
        return raw_duration * self.trim_fraction
