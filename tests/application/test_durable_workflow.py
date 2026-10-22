"""Tests for PipelineRunner DBOS step execution and workflow."""

import asyncio
from pathlib import Path

import pytest
from dbos import DBOS

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
from smartmech.domain.concept import Plan


def _check_exists(p: str) -> bool:
    return Path(p).exists()


@pytest.mark.asyncio
async def test_durable_pipeline_runner_steps_and_workflow(tmp_path: Path) -> None:
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

    DBOS.destroy()
    _ = DBOS(config=runner.dbos_config)
    DBOS.launch()
    try:
        # 1. Test step_plan directly
        plan_json = await PipelineRunner.step_plan(runner, "run-engine-1", "Durable Tower", 42)
        assert "The Rise of Sky-Tower" in plan_json
        plan = Plan.model_validate_json(plan_json)

        # 2. Test step_keyframe directly
        kf = plan.shot_list.keyframes[0]
        kf_key = await PipelineRunner.step_keyframe(
            runner, "run-engine-1", kf.prompt, plan.site_bible.model_dump_json(), 42, 0
        )
        assert len(kf_key) == 64

        # 3. Test step_speech directly
        speech_key = await PipelineRunner.step_speech(runner, "run-engine-1", plan.script.text, 42)
        assert len(speech_key) == 64

        # 4. Test step_alignment directly
        run_dir = output_dir / "run-engine-1"
        run_dir.mkdir(parents=True, exist_ok=True)
        ass_path = await PipelineRunner.step_alignment(
            runner, "run-engine-1", speech_key, plan.script.text, str(run_dir)
        )
        assert await asyncio.to_thread(_check_exists, ass_path)
    finally:
        DBOS.destroy()

    # 5. Test full DBOS workflow execution via DurablePipelineEngine delegation
    runner.variation_memory = VariationMemory()
    engine = DurablePipelineEngine(runner)
    report = await engine.run_durable_workflow(
        run_id="run-engine-1", prompt="Ocean Bridge", seed=100
    )
    assert report["status"] == "PASS"
    assert await asyncio.to_thread(_check_exists, report["video_path"])
