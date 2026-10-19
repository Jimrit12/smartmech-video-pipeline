"""Autonomy levels, publishing metadata, and safety defaults."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AutonomyLevel(StrEnum):
    """Autonomy level governing video publication."""

    L0_MANUAL = "L0"
    L1_HUMAN_APPROVAL = "L1"  # Default
    L2_AUTO_PUBLISH = "L2"


class PrivacyStatus(StrEnum):
    """Video privacy status on publication platform."""

    PRIVATE = "private"
    UNLISTED = "unlisted"
    PUBLIC = "public"


class PublishMetadata(BaseModel):
    """Metadata required to publish a completed YouTube Short."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(min_length=5, max_length=100)
    description: str = Field(min_length=10, max_length=5000)
    tags: list[str] = Field(
        default_factory=lambda: ["Shorts", "Construction", "Timelapse", "Architecture"]
    )
    privacy: PrivacyStatus = PrivacyStatus.PRIVATE
    synthetic_media_disclosure: bool = True
    made_for_kids: bool = False
