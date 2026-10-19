"""Adapter capabilities declaration."""

from pydantic import BaseModel, ConfigDict, Field


class AdapterCapabilities(BaseModel):
    """Declared capabilities of a media generation or processing adapter."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    aspect_ratios: list[str] = Field(default_factory=lambda: ["9:16"])
    min_duration_seconds: float = Field(default=0.0, ge=0.0)
    max_duration_seconds: float = Field(default=10.0, ge=0.0)
    supports_first_frame: bool = True
    supports_last_frame: bool = False
    supports_native_audio: bool = False
    max_concurrent_requests: int = Field(default=5, ge=1)
    requests_per_minute: int = Field(default=60, ge=1)
