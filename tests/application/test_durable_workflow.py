"""Tests for DurablePipelineEngine step execution and resumption."""

import asyncio
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
from smartmech.application.durable_workflow import DurablePipelineEngine
from smartmech.application.pipeline_runner import PipelineRunner
from smartmech.application.variation import VariationMemory


@pytest.mark.asyncio
async def test_durable_pipeline_engine_run(tmp_path: Path) -> None:
    output_dir = tmp_path / "engine_output"
    store = LocalArtifactStoreAdapter(base_directory=output_dir / "artifacts")
    ledger = MemoryCostLedgerAdapter()
    db_file = tmp_path / "durable_engine.sqlite"

    runner = PipelineRunner(
        planner=FakePlannerAdapter(),
        image_gen=FakeImageGenAdapter(),
        video_gen=FakeVideoGenAdapter(),
        speech=FakeSpeechAdapter(),
        aligner=FakeAlignerAdapter(),
        publisher=FakePublisherAdapter(),
        artifact_store=store,
        cost_ledger=ledger,
        dbos_sqlite_path=str(db_file),
        output_directory=str(output_dir),
    )

    engine = DurablePipelineEngine(runner)

    # Test step_plan static method
    plan_json = await DurablePipelineEngine.durable_step_plan(
        runner, "run-engine-1", "Durable Tower", 42
    )
    assert "The Rise of Sky-Tower" in plan_json

    # Test step_keyframes static method
    keys = await DurablePipelineEngine.durable_step_keyframes(runner, "run-engine-1", plan_json, 42)
    assert len(keys) == 6

    # Test run_durable_workflow
    runner.variation_memory = VariationMemory()
    report = await engine.run_durable_workflow(
        run_id="run-engine-1", prompt="Ocean Bridge", seed=100
    )
    assert report["status"] == "PASS"
    exists = await asyncio.to_thread(Path(report["video_path"]).exists)
    assert exists
