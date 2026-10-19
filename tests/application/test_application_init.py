"""Test application layer initialization."""

import smartmech.application


def test_application_init() -> None:
    assert hasattr(smartmech.application, "__all__")
