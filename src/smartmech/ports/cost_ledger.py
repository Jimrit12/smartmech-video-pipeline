"""Cost ledger port definition."""

from typing import Protocol

from smartmech.domain.budget import CostRecord


class CostLedgerPort(Protocol):
    """Protocol for recording and querying cost units."""

    async def record_cost(self, record: CostRecord) -> None:
        """Record cost units spent by an adapter operation."""
        ...

    async def get_run_cost(self, run_id: str) -> float:
        """Get aggregate spend for a specific run ID."""
        ...

    async def get_daily_cost(self) -> float:
        """Get aggregate spend across all runs in the last 24 hours."""
        ...
