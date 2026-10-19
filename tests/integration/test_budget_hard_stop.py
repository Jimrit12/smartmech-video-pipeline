"""Test budget hard-stop preventing runaway adapter costs."""

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
from smartmech.domain.budget import BudgetConfig, BudgetExceededError


@pytest.mark.asyncio
async def test_budget_hard_stop_halts_pipeline_on_ceiling(tmp_path: Path) -> None:
    output_dir = tmp_path / "budget_test_output"
    store = LocalArtifactStoreAdapter(base_directory=output_dir / "artifacts")
    ledger = MemoryCostLedgerAdapter()

    # Extremely low budget: 0.2 units (not enough for 6 keyframes at 0.1 each)
    tight_budget = BudgetConfig(per_run_budget=0.25, per_day_budget=50.0)

    runner = PipelineRunner(
        planner=FakePlannerAdapter(),
        image_gen=FakeImageGenAdapter(),
        video_gen=FakeVideoGenAdapter(),
        speech=FakeSpeechAdapter(),
        aligner=FakeAlignerAdapter(),
        publisher=FakePublisherAdapter(),
        artifact_store=store,
        cost_ledger=ledger,
        budget_config=tight_budget,
        output_directory=str(output_dir),
    )

    with pytest.raises(BudgetExceededError, match="per-run budget"):
        await runner.execute_run(
            run_id="run_budget_breached", prompt="Over budget skyscraper", seed=77
        )

    # Verify execution halted: spend stopped exactly before breaching limit
    recorded_spend = await ledger.get_run_cost("run_budget_breached")
    assert recorded_spend <= 0.25
