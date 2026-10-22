"""Content-addressed artifact key calculation and provenance manifest."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def compute_canonical_input_hash(data: Any) -> str:
    """Compute deterministic SHA-256 hash of canonical input data."""
    if isinstance(data, BaseModel):
        serialized = json.dumps(data.model_dump(), sort_keys=True)
    elif isinstance(data, (dict, list)):
        serialized = json.dumps(data, sort_keys=True)
    elif isinstance(data, bytes):
        return hashlib.sha256(data).hexdigest()
    else:
        serialized = str(data)

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_artifact_key(
    port: str,
    adapter: str,
    model_or_version: str,
    canonical_input: Any,
    seed: int,
    input_artifact_keys: list[str] | None = None,
) -> str:
    """Compute content-addressed key = hash(port, adapter, model/version, canonical input, seed, input_keys)."""
    input_hash = compute_canonical_input_hash(canonical_input)
    if input_artifact_keys:
        parents_str = "|".join(sorted(input_artifact_keys))
        components = f"{port}|{adapter}|{model_or_version}|{input_hash}|{seed}|{parents_str}"
    else:
        components = f"{port}|{adapter}|{model_or_version}|{input_hash}|{seed}"
    return hashlib.sha256(components.encode("utf-8")).hexdigest()


class ProvenanceManifest(BaseModel):
    """Immutable audit record detailing generation parameters and provenance of an artifact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_key: str = Field(min_length=64, max_length=64)
    run_id: str = Field(min_length=1)
    port: str = Field(min_length=1)
    adapter: str = Field(min_length=1)
    model_or_version: str = Field(min_length=1)
    seed: int
    cost_units: float = Field(ge=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    file_extension: str = Field(min_length=1)
