"""SQLite cost ledger adapter persisting spend across runs, daily windows, and process restarts."""

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from smartmech.domain.budget import CostRecord
from smartmech.ports.cost_ledger import CostLedgerPort


class SQLiteCostLedgerAdapter(CostLedgerPort):
    """SQLite-backed implementation of CostLedgerPort."""

    def __init__(self, db_path: Path | str = "smartmech_ledger.db") -> None:
        self.db_path = str(db_path)
        if self.db_path == ":memory:":
            self._mem_conn: sqlite3.Connection | None = sqlite3.connect(
                ":memory:", check_same_thread=False
            )
        else:
            self._mem_conn = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._mem_conn is not None:
            return self._mem_conn
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
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
                conn.execute("CREATE INDEX IF NOT EXISTS idx_cost_run_id ON cost_records (run_id)")
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_cost_timestamp ON cost_records (timestamp)"
                )
        finally:
            if self._mem_conn is None:
                conn.close()

    async def record_cost(self, record: CostRecord) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
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
        finally:
            if self._mem_conn is None:
                conn.close()

    async def get_run_cost(self, run_id: str) -> float:
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT COALESCE(SUM(cost_units), 0.0) FROM cost_records WHERE run_id = ?",
                (run_id,),
            )
            row = cur.fetchone()
            return float(row[0]) if row and row[0] is not None else 0.0
        finally:
            if self._mem_conn is None:
                conn.close()

    async def get_daily_cost(self) -> float:
        now = datetime.now(UTC)
        cutoff = (now - timedelta(hours=24)).isoformat()
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT COALESCE(SUM(cost_units), 0.0) FROM cost_records WHERE timestamp >= ?",
                (cutoff,),
            )
            row = cur.fetchone()
            return float(row[0]) if row and row[0] is not None else 0.0
        finally:
            if self._mem_conn is None:
                conn.close()

    def all_records(self) -> list[CostRecord]:
        conn = self._get_connection()
        try:
            cur = conn.execute(
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
        finally:
            if self._mem_conn is None:
                conn.close()
