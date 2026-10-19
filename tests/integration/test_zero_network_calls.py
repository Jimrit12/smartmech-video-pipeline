"""Test verifying zero real network calls during pipeline execution."""

import asyncio
import socket
from pathlib import Path
from unittest.mock import patch

import pytest

from smartmech.adapters.fake_aligner import FakeAlignerAdapter
from smartmech.adapters.fake_image_gen import FakeImageGenAdapter
from smartmech.adapters.fake_planner import FakePlannerAdapter
from smartmech.adapters.fake_publisher import FakePublisherAdapter
from smartmech.adapters.fake_speech import FakeSpeechAdapter
from smartmech.adapters.fake_video_gen import FakeVideoGenAdapter
from smartmech.adapters.local_artifact_store import LocalArtifactStoreAdapter
from smartmech.adapters.memory_cost_ledger import MemoryCostLedgerAdapter
from smartmech.application.pipeline_runner import PipelineRunner


class RealNetworkAttemptError(Exception):
    """Raised if an unmocked network connection is attempted."""


def forbidden_connect(*args: object, **kwargs: object) -> None:
    raise RealNetworkAttemptError("Zero real network calls permitted during dry-run!")


@pytest.mark.asyncio
async def test_zero_real_network_calls_during_pipeline(tmp_path: Path) -> None:
    output_dir = tmp_path / "offline_output"
    store = LocalArtifactStoreAdapter(base_directory=output_dir / "artifacts")
    ledger = MemoryCostLedgerAdapter()

    runner = PipelineRunner(
        planner=FakePlannerAdapter(),
        image_gen=FakeImageGenAdapter(),
        video_gen=FakeVideoGenAdapter(),
        speech=FakeSpeechAdapter(),
        aligner=FakeAlignerAdapter(),
        publisher=FakePublisherAdapter(),
        artifact_store=store,
        cost_ledger=ledger,
        output_directory=str(output_dir),
    )

    # Monkeypatch socket connect to fail if any network connection is attempted
    with patch.object(socket.socket, "connect", side_effect=forbidden_connect):
        report = await runner.execute_run(
            run_id="run_offline_verified", prompt="Offline Skyscraper", seed=99
        )

    assert report["status"] == "PASS"
    video_exists = await asyncio.to_thread(Path(report["video_path"]).exists)
    assert video_exists
