"""Spike test proving Pydantic v2 exact behavior for domain modeling."""

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class SampleDomainEntity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    word_count: int = Field(ge=0, le=100)
    aspect_ratio: str = Field(pattern=r"^\d+:\d+$")


def test_pydantic_valid_instance() -> None:
    entity = SampleDomainEntity(id="ent-1", word_count=42, aspect_ratio="9:16")
    assert entity.id == "ent-1"
    assert entity.word_count == 42
    assert entity.aspect_ratio == "9:16"


def test_pydantic_validation_failure() -> None:
    with pytest.raises(ValidationError):
        SampleDomainEntity(id="", word_count=101, aspect_ratio="invalid")


def test_pydantic_immutability() -> None:
    entity = SampleDomainEntity(id="ent-1", word_count=10, aspect_ratio="9:16")
    with pytest.raises(ValidationError):
        # Mutating frozen model via setattr should raise ValidationError at runtime
        entity.word_count = 20
