"""Test domain layer initialization."""

import smartmech.domain


def test_domain_init() -> None:
    assert hasattr(smartmech.domain, "__all__")
