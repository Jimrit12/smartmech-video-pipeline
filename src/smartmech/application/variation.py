"""Variation memory preventing duplicate or overly similar video concepts across runs."""

import re

from smartmech.domain.concept import Concept


class ConceptTooSimilarError(Exception):
    """Raised when a proposed concept is too similar to one of the last N executed runs."""


class VariationMemory:
    """Sliding-window memory tracking recent concepts to enforce creative variety."""

    def __init__(self, window_size: int = 5, max_similarity_threshold: float = 0.70) -> None:
        self.window_size = window_size
        self.max_similarity_threshold = max_similarity_threshold
        self._history: list[Concept] = []

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
        for past_concept in self._history:
            similarity = self.calculate_similarity(candidate, past_concept)
            if similarity > self.max_similarity_threshold:
                raise ConceptTooSimilarError(
                    f"Candidate concept '{candidate.title}' is too similar to past run '{past_concept.title}' "
                    f"({similarity:.2%} similarity > {self.max_similarity_threshold:.0%})"
                )

        self._history.append(candidate)
        if len(self._history) > self.window_size:
            self._history.pop(0)

    def history(self) -> list[Concept]:
        return list(self._history)
