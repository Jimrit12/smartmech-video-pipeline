"""Speech generation port definition."""

from typing import Protocol

from smartmech.domain.adapter_identity import AdapterIdentity
from smartmech.domain.capabilities import AdapterCapabilities


class SpeechPort(Protocol):
    """Protocol for generating voiceover audio from script."""

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

    async def generate_speech(self, text: str, voice: str | None = None) -> bytes:
        """Synthesize narrative voiceover audio."""
        ...
