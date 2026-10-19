"""Content-addressed artifact store port definition."""

from typing import Protocol

from smartmech.domain.artifact import ProvenanceManifest


class ArtifactStorePort(Protocol):
    """Protocol for content-addressed persistence of artifacts and manifests."""

    async def exists(self, key: str) -> bool:
        """Check if an artifact with key already exists in the store."""
        ...

    async def get(self, key: str) -> tuple[bytes, ProvenanceManifest]:
        """Retrieve stored artifact payload and its provenance manifest."""
        ...

    async def put(self, key: str, payload: bytes, manifest: ProvenanceManifest) -> str:
        """Atomically persist artifact payload and provenance manifest; returns absolute path."""
        ...
