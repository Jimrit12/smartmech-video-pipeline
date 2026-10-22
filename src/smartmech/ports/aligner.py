"""Aligner port definition for forced audio alignment."""

from typing import Protocol

from smartmech.domain.adapter_identity import AdapterIdentity
from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.domain.captions import WordTimestamp


class AlignerPort(Protocol):
    """Protocol for generating word-level timestamps from audio and script."""

    @property
    def identity(self) -> AdapterIdentity:
        """Declared adapter identity."""
        ...

    @property
    def cost_estimate_per_call(self) -> float:
        """Estimated cost units per invocation."""
        ...

    @property
    def capabilities(self) -> AdapterCapabilities:
        """Declared adapter capabilities."""
        ...

    async def align(self, audio_bytes: bytes, transcript: str) -> list[WordTimestamp]:
        """Produce word timestamps for audio against transcript."""
        ...
