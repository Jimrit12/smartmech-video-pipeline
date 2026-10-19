"""Local filesystem content-addressed artifact store with atomic writes."""

import asyncio
import json
from pathlib import Path

from smartmech.domain.artifact import ProvenanceManifest
from smartmech.ports.artifact_store import ArtifactStorePort


def _write_atomic(target_path: Path, data: bytes) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_name(f"{target_path.name}.tmp")
    with open(temp_path, "wb") as f:
        f.write(data)
    temp_path.replace(target_path)


def _read_manifest(manifest_path: Path) -> ProvenanceManifest:
    with open(manifest_path, encoding="utf-8") as f:
        manifest_dict = json.load(f)
    return ProvenanceManifest.model_validate(manifest_dict)


def _read_artifact(payload_path: Path, manifest_path: Path) -> tuple[bytes, ProvenanceManifest]:
    with open(payload_path, "rb") as f:
        payload = f.read()
    manifest = _read_manifest(manifest_path)
    return payload, manifest


class LocalArtifactStoreAdapter(ArtifactStorePort):
    """Stores content-addressed artifacts with atomic rename writes and provenance manifests."""

    def __init__(self, base_directory: Path | str) -> None:
        self.base_dir = Path(base_directory)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def exists(self, key: str) -> bool:
        manifest_path = self.base_dir / f"{key}.manifest.json"
        return await asyncio.to_thread(manifest_path.exists)

    async def get(self, key: str) -> tuple[bytes, ProvenanceManifest]:
        manifest_path = self.base_dir / f"{key}.manifest.json"
        if not await asyncio.to_thread(manifest_path.exists):
            raise FileNotFoundError(f"Artifact {key} not found in store")

        manifest = await asyncio.to_thread(_read_manifest, manifest_path)
        payload_path = self.base_dir / f"{key}.{manifest.file_extension}"
        return await asyncio.to_thread(_read_artifact, payload_path, manifest_path)

    async def put(self, key: str, payload: bytes, manifest: ProvenanceManifest) -> str:
        payload_path = self.base_dir / f"{key}.{manifest.file_extension}"
        manifest_path = self.base_dir / f"{key}.manifest.json"

        # Atomic writes
        await asyncio.to_thread(_write_atomic, payload_path, payload)
        manifest_bytes = manifest.model_dump_json(indent=2).encode("utf-8")
        await asyncio.to_thread(_write_atomic, manifest_path, manifest_bytes)

        return str(payload_path.resolve())
