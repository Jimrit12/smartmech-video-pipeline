"""Application settings loaded from environment variables using pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from smartmech.domain.autonomy import AutonomyLevel


class PipelineSettings(BaseSettings):
    """Pipeline configuration settings with environment variable overrides."""

    model_config = SettingsConfigDict(
        env_prefix="SMARTMECH_",
        env_file=".env",
        extra="ignore",
    )

    output_dir: str = Field(default="output")
    dbos_sqlite_path: str = Field(default="smartmech_dbos.sqlite")
    per_run_budget: float = Field(default=10.0, ge=0.0)
    per_day_budget: float = Field(default=50.0, ge=0.0)
    autonomy_level: AutonomyLevel = Field(default=AutonomyLevel.L1_HUMAN_APPROVAL)
