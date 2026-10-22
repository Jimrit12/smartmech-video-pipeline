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
from smartmech.compose.settings import PipelineSettings
from smartmech.domain.autonomy import AutonomyLevel
from smartmech.domain.budget import BudgetConfig


def build_pipeline(
    output_dir: str | None = None,
    dbos_sqlite_path: str | None = None,
    per_run_budget: float | None = None,
    per_day_budget: float | None = None,
    autonomy_level: AutonomyLevel | None = None,
    settings: PipelineSettings | None = None,
) -> PipelineRunner:
    """Build fully assembled PipelineRunner with configured adapters."""
    cfg = settings or PipelineSettings()
    eff_output_dir = output_dir or cfg.output_dir
    eff_dbos_path = dbos_sqlite_path or cfg.dbos_sqlite_path
    eff_run_budget = per_run_budget if per_run_budget is not None else cfg.per_run_budget
    eff_day_budget = per_day_budget if per_day_budget is not None else cfg.per_day_budget
    eff_autonomy = autonomy_level or cfg.autonomy_level

    artifacts_dir = Path(eff_output_dir) / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    planner = FakePlannerAdapter()
    image_gen = FakeImageGenAdapter()
    video_gen = FakeVideoGenAdapter()
    speech = FakeSpeechAdapter()
    aligner = FakeAlignerAdapter()
    publisher = FakePublisherAdapter()
    artifact_store = LocalArtifactStoreAdapter(base_directory=artifacts_dir)
    cost_ledger = MemoryCostLedgerAdapter()
    budget_config = BudgetConfig(per_run_budget=eff_run_budget, per_day_budget=eff_day_budget)

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
        dbos_sqlite_path=eff_dbos_path,
        output_directory=eff_output_dir,
        autonomy_level=eff_autonomy,
    )
