"""In-memory SQLite cost ledger adapter tracking spend across runs and daily windows."""

from smartmech.adapters.sqlite_cost_ledger import SQLiteCostLedgerAdapter


class MemoryCostLedgerAdapter(SQLiteCostLedgerAdapter):
    """In-memory SQLite-backed implementation of CostLedgerPort."""

    def __init__(self) -> None:
        super().__init__(db_path=":memory:")
