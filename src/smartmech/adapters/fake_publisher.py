"""Fake publisher adapter simulating YouTube Shorts upload."""

import hashlib

from smartmech.domain.autonomy import PublishMetadata
from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.ports.publisher import PublisherPort


class FakePublisherAdapter(PublisherPort):
    """Simulates publishing a short without making real network requests."""

    def __init__(self, capabilities: AdapterCapabilities | None = None) -> None:
        self._capabilities = capabilities or AdapterCapabilities(
            aspect_ratios=["9:16"],
            min_duration_seconds=15.0,
            max_duration_seconds=60.0,
            supports_first_frame=False,
            supports_last_frame=False,
            supports_native_audio=True,
        )

    @property
    def capabilities(self) -> AdapterCapabilities:
        return self._capabilities

    async def publish(self, video_path: str, metadata: PublishMetadata) -> str:
        video_hash = hashlib.sha256(video_path.encode()).hexdigest()[:11]
        return f"https://youtube.com/shorts/{video_hash}"
