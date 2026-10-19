"""Spike test proving pydantic-settings behavior and secret masking."""

import os

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TEST_SMARTMECH_")

    env_name: str = "test"
    secret_key: SecretStr = SecretStr("initial_secret")


def test_settings_secret_masking() -> None:
    settings = AppSettings()
    # Ensure repr masks the secret
    assert "initial_secret" not in repr(settings)
    assert settings.secret_key.get_secret_value() == "initial_secret"


def test_settings_env_override() -> None:
    os.environ["TEST_SMARTMECH_ENV_NAME"] = "custom_env"
    try:
        settings = AppSettings()
        assert settings.env_name == "custom_env"
    finally:
        os.environ.pop("TEST_SMARTMECH_ENV_NAME", None)
