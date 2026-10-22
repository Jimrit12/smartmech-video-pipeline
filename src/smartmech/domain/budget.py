"""Budget, cost tracking, and spend guard domain models."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class CostRecord(BaseModel):
    """Cost units recorded by an individual adapter execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    port: str = Field(min_length=1)
    adapter: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    cost_units: float = Field(ge=0.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    run_id: str = Field(min_length=1)


class BudgetConfig(BaseModel):
    """Budget limits governing execution spend."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    per_run_budget: float = Field(default=10.0, ge=0.1)
    per_day_budget: float = Field(default=50.0, ge=0.1)


class BudgetExceededError(Exception):
    """Raised when an operation would exceed either the per-run or per-day budget cap."""

    def __init__(
        self,
        message: str = "Budget exceeded",
        run_id: str = "",
        current_spend: float = 0.0,
        limit: float = 0.0,
    ) -> None:
        super().__init__(message)
        self.run_id = run_id
        self.current_spend = current_spend
        self.limit = limit

    def __reduce__(self) -> tuple[type, tuple[str, str, float, float]]:
        return (
            BudgetExceededError,
            (
                str(self.args[0]) if self.args else "Budget exceeded",
                self.run_id,
                self.current_spend,
                self.limit,
            ),
        )
