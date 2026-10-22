"""Publisher port definition for video upload platforms."""

from typing import Protocol

from smartmech.domain.adapter_identity import AdapterIdentity
from smartmech.domain.autonomy import PublishMetadata
from smartmech.domain.capabilities import AdapterCapabilities


class PublisherPort(Protocol):
    """Protocol for publishing the final video with metadata."""

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

    async def publish(self, video_path: str, metadata: PublishMetadata) -> str:
        """Publish video to destination platform and return published ID/URL."""
        ...
