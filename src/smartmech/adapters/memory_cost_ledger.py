"""In-memory cost ledger adapter tracking spend across runs and daily windows."""

from datetime import UTC, datetime, timedelta

from smartmech.domain.budget import CostRecord
from smartmech.ports.cost_ledger import CostLedgerPort


class MemoryCostLedgerAdapter(CostLedgerPort):
    """In-memory implementation of CostLedgerPort."""

    def __init__(self) -> None:
        self._records: list[CostRecord] = []

    async def record_cost(self, record: CostRecord) -> None:
        self._records.append(record)

    async def get_run_cost(self, run_id: str) -> float:
        return sum(r.cost_units for r in self._records if r.run_id == run_id)

    async def get_daily_cost(self) -> float:
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=24)
        return sum(r.cost_units for r in self._records if r.timestamp >= cutoff)

    def all_records(self) -> list[CostRecord]:
        return list(self._records)
