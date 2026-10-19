"""Composition root: binds concrete adapters to application ports."""

from pathlib import Path

from smartmech.adapters.fake_aligner import FakeAlignerAdapter
from smartmech.adapters.fake_image_gen import FakeImageGenAdapter
from smartmech.adapters.fake_planner import FakePlannerAdapter
from smartmech.adapters.fake_publisher import FakePublisherAdapter
from smartmech.adapters.fake_speech import FakeSpeechAdapter
from smartmech.adapters.fake_video_gen import FakeVideoGenAdapter
from smartmech.adapters.local_artifact_store import LocalArtifactStoreAdapter
from smartmech.adapters.memory_cost_ledger import MemoryCostLedgerAdapter
from smartmech.application.pipeline_runner import PipelineRunner
from smartmech.domain.autonomy import AutonomyLevel
from smartmech.domain.budget import BudgetConfig


def build_pipeline(
    output_dir: str = "output",
    dbos_sqlite_path: str = "smartmech_dbos.sqlite",
    per_run_budget: float = 10.0,
    per_day_budget: float = 50.0,
    autonomy_level: AutonomyLevel = AutonomyLevel.L1_HUMAN_APPROVAL,
) -> PipelineRunner:
    """Build fully assembled PipelineRunner with configured adapters."""
    artifacts_dir = Path(output_dir) / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    planner = FakePlannerAdapter()
    image_gen = FakeImageGenAdapter()
    video_gen = FakeVideoGenAdapter()
    speech = FakeSpeechAdapter()
    aligner = FakeAlignerAdapter()
    publisher = FakePublisherAdapter()
    artifact_store = LocalArtifactStoreAdapter(base_directory=artifacts_dir)
    cost_ledger = MemoryCostLedgerAdapter()
    budget_config = BudgetConfig(per_run_budget=per_run_budget, per_day_budget=per_day_budget)

    return PipelineRunner(
        planner=planner,
        image_gen=image_gen,
        video_gen=video_gen,
        speech=speech,
        aligner=aligner,
        publisher=publisher,
        artifact_store=artifact_store,
        cost_ledger=cost_ledger,
        budget_config=budget_config,
        dbos_sqlite_path=dbos_sqlite_path,
        output_directory=output_dir,
        autonomy_level=autonomy_level,
    )
