"""In-memory SQLite cost ledger adapter tracking spend across runs and daily windows."""

import sqlite3
from datetime import UTC, datetime, timedelta

from smartmech.domain.budget import CostRecord
from smartmech.ports.cost_ledger import CostLedgerPort


class MemoryCostLedgerAdapter(CostLedgerPort):
    """In-memory SQLite-backed implementation of CostLedgerPort."""

    def __init__(self) -> None:
        self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    port TEXT NOT NULL,
                    adapter TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    cost_units REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    run_id TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cost_run_id ON cost_records (run_id)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cost_timestamp ON cost_records (timestamp)"
            )

    async def record_cost(self, record: CostRecord) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO cost_records (port, adapter, operation, cost_units, timestamp, run_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.port,
                    record.adapter,
                    record.operation,
                    record.cost_units,
                    record.timestamp.isoformat(),
                    record.run_id,
                ),
            )

    async def get_run_cost(self, run_id: str) -> float:
        cur = self._conn.execute(
            "SELECT COALESCE(SUM(cost_units), 0.0) FROM cost_records WHERE run_id = ?",
            (run_id,),
        )
        row = cur.fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0

    async def get_daily_cost(self) -> float:
        now = datetime.now(UTC)
        cutoff = (now - timedelta(hours=24)).isoformat()
        cur = self._conn.execute(
            "SELECT COALESCE(SUM(cost_units), 0.0) FROM cost_records WHERE timestamp >= ?",
            (cutoff,),
        )
        row = cur.fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0

    def all_records(self) -> list[CostRecord]:
        cur = self._conn.execute(
            "SELECT port, adapter, operation, cost_units, timestamp, run_id FROM cost_records ORDER BY id ASC"
        )
        return [
            CostRecord(
                port=row[0],
                adapter=row[1],
                operation=row[2],
                cost_units=row[3],
                timestamp=datetime.fromisoformat(row[4]),
                run_id=row[5],
            )
            for row in cur.fetchall()
        ]
