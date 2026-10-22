"""Variation memory preventing duplicate or overly similar video concepts across runs and process restarts."""

import re
import sqlite3
from pathlib import Path

from smartmech.domain.concept import Concept


class ConceptTooSimilarError(Exception):
    """Raised when a proposed concept is too similar to one of the last N executed runs."""


class VariationMemory:
    """SQLite-backed sliding-window memory tracking recent concepts to enforce creative variety."""

    def __init__(
        self,
        db_path: Path | str = "smartmech_variation.db",
        window_size: int = 5,
        max_similarity_threshold: float = 0.70,
    ) -> None:
        self.db_path = str(db_path)
        self.window_size = window_size
        self.max_similarity_threshold = max_similarity_threshold
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
                    CREATE TABLE IF NOT EXISTS concept_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        premise TEXT NOT NULL,
                        building_type TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
        finally:
            if self._mem_conn is None:
                conn.close()

    def _extract_tokens(self, text: str) -> set[str]:
        words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", text.lower())
        return set(words)

    def calculate_similarity(self, a: Concept, b: Concept) -> float:
        """Compute Jaccard token similarity over title, premise, and building type."""
        tokens_a = self._extract_tokens(f"{a.title} {a.premise} {a.building_type}")
        tokens_b = self._extract_tokens(f"{b.title} {b.premise} {b.building_type}")

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        return len(intersection) / len(union)

    def check_and_record(self, candidate: Concept) -> None:
        """Verify candidate is sufficiently novel; raises ConceptTooSimilarError if too similar."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """
                SELECT title, premise, building_type, payload_json
                FROM concept_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (self.window_size,),
            )
            past_rows = cur.fetchall()

            for row in past_rows:
                past_title, past_premise, past_building_type, _ = row
                past_concept = Concept(
                    title=past_title,
                    premise=past_premise,
                    building_type=past_building_type,
                )
                similarity = self.calculate_similarity(candidate, past_concept)
                if similarity > self.max_similarity_threshold:
                    raise ConceptTooSimilarError(
                        f"Candidate concept '{candidate.title}' is too similar to past run '{past_title}' "
                        f"({similarity:.2%} similarity > {self.max_similarity_threshold:.0%})"
                    )

            with conn:
                conn.execute(
                    """
                    INSERT INTO concept_history (title, premise, building_type, payload_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        candidate.title,
                        candidate.premise,
                        candidate.building_type,
                        candidate.model_dump_json(),
                    ),
                )
        finally:
            if self._mem_conn is None:
                conn.close()

    def history(self) -> list[Concept]:
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """
                SELECT payload_json
                FROM concept_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (self.window_size,),
            )
            rows = cur.fetchall()
            return [Concept.model_validate_json(r[0]) for r in reversed(rows)]
        finally:
            if self._mem_conn is None:
                conn.close()
