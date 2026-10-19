"""Aligner port definition for forced audio alignment."""

from typing import Protocol

from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.domain.captions import WordTimestamp


class AlignerPort(Protocol):
    """Protocol for generating word-level timestamps from audio and script."""

    @property
    def capabilities(self) -> AdapterCapabilities:
        """Declared adapter capabilities."""
        ...

    async def align(self, audio_bytes: bytes, transcript: str) -> list[WordTimestamp]:
        """Produce word timestamps for audio against transcript."""
        ...
