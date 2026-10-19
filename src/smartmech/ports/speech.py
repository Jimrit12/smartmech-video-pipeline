"""Speech generation port definition."""

from typing import Protocol

from smartmech.domain.capabilities import AdapterCapabilities


class SpeechPort(Protocol):
    """Protocol for generating voiceover audio from script."""

    @property
    def capabilities(self) -> AdapterCapabilities:
        """Declared adapter capabilities."""
        ...

    async def generate_speech(self, text: str, voice: str | None = None) -> bytes:
        """Synthesize narrative voiceover audio."""
        ...
