"""Video generation port definition."""

from typing import Protocol

from smartmech.domain.adapter_identity import AdapterIdentity
from smartmech.domain.capabilities import AdapterCapabilities


class VideoGenPort(Protocol):
    """Protocol for generating video transitions between keyframe anchors."""

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

    async def generate_transition(
        self,
        from_image: bytes,
        to_image: bytes | None,
        motion_prompt: str,
        duration_seconds: float,
        seed: int,
    ) -> bytes:
        """Generate transition clip bytes."""
        ...
