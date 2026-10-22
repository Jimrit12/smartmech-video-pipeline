"""Image generation port definition."""

from typing import Protocol

from smartmech.domain.adapter_identity import AdapterIdentity
from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.domain.concept import SiteBible


class ImageGenPort(Protocol):
    """Protocol for generating keyframe images."""

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

    async def generate_image(self, prompt: str, site_bible: SiteBible, seed: int) -> bytes:
        """Generate a single portrait keyframe image."""
        ...
