"""Fake publisher adapter simulating YouTube Shorts upload."""

import hashlib

from smartmech.domain.adapter_identity import AdapterIdentity
from smartmech.domain.autonomy import PublishMetadata
from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.ports.publisher import PublisherPort


class FakePublisherAdapter(PublisherPort):
    """Simulates publishing a short without making real network requests."""

    def __init__(
        self,
        capabilities: AdapterCapabilities | None = None,
        identity: AdapterIdentity | None = None,
    ) -> None:
        self._capabilities = capabilities or AdapterCapabilities(
            aspect_ratios=["9:16"],
            min_duration_seconds=15.0,
            max_duration_seconds=60.0,
            supports_first_frame=False,
            supports_last_frame=False,
            supports_native_audio=True,
        )
        self._identity = identity or AdapterIdentity(
            port="publisher",
            adapter_name="fake_publisher",
            model_or_version="stub_v1",
            cost_estimate_per_call=0.00,
        )

    @property
    def identity(self) -> AdapterIdentity:
        return self._identity

    @property
    def cost_estimate_per_call(self) -> float:
        return self._identity.cost_estimate_per_call

    @property
    def capabilities(self) -> AdapterCapabilities:
        return self._capabilities

    async def publish(self, video_path: str, metadata: PublishMetadata) -> str:
        video_hash = hashlib.sha256(video_path.encode()).hexdigest()[:11]
        return f"https://youtube.com/shorts/{video_hash}"
