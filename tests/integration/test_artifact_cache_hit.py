"""Test content-addressed artifact cache hits across multiple runs."""

from pathlib import Path

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


@pytest.mark.asyncio
async def test_artifact_cache_hit_across_runs(tmp_path: Path) -> None:
    output_dir = tmp_path / "cache_test_output"
    artifacts_dir = output_dir / "artifacts"
    shared_store = LocalArtifactStoreAdapter(base_directory=artifacts_dir)

    ledger_run1 = MemoryCostLedgerAdapter()
    runner1 = PipelineRunner(
        planner=FakePlannerAdapter(),
        image_gen=FakeImageGenAdapter(),
        video_gen=FakeVideoGenAdapter(),
        speech=FakeSpeechAdapter(),
        aligner=FakeAlignerAdapter(),
        publisher=FakePublisherAdapter(),
        artifact_store=shared_store,
        cost_ledger=ledger_run1,
        output_directory=str(output_dir),
    )

    # First run populates store and pays cost units
    report1 = await runner1.execute_run(run_id="run_fresh_1", prompt="Cache test tower", seed=55)
    spend1 = await ledger_run1.get_run_cost("run_fresh_1")
    assert spend1 > 0.0
    assert report1["status"] == "PASS"

    # Second run with same inputs and shared store, but fresh ledger
    ledger_run2 = MemoryCostLedgerAdapter()
    runner2 = PipelineRunner(
        planner=FakePlannerAdapter(),
        image_gen=FakeImageGenAdapter(),
        video_gen=FakeVideoGenAdapter(),
        speech=FakeSpeechAdapter(),
        aligner=FakeAlignerAdapter(),
        publisher=FakePublisherAdapter(),
        artifact_store=shared_store,
        cost_ledger=ledger_run2,
        output_directory=str(output_dir),
    )

    report2 = await runner2.execute_run(run_id="run_fresh_2", prompt="Cache test tower", seed=55)
    spend2 = await ledger_run2.get_run_cost("run_fresh_2")

    # Invariant: identical requests across runs are NEVER paid twice
    assert spend2 == 0.0, "Second run must incur zero cost due to 100% artifact cache hits"
    assert report2["status"] == "PASS"
