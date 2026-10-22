"""Adapter identity model declaring vendor, port, version, and cost."""

from pydantic import BaseModel, ConfigDict, Field


class AdapterIdentity(BaseModel):
    """Declared identity and pricing of a vendor or technology adapter."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    port: str = Field(min_length=1)
    adapter_name: str = Field(min_length=1)
    model_or_version: str = Field(min_length=1)
    cost_estimate_per_call: float = Field(default=0.0, ge=0.0)
