"""DBOS durable workflow definitions for resumable step execution."""

from typing import Any

from dbos import DBOS, SetWorkflowID

from smartmech.application.pipeline_runner import PipelineRunner
from smartmech.domain.artifact import ProvenanceManifest, compute_artifact_key
from smartmech.domain.budget import CostRecord
from smartmech.domain.concept import Plan


class DurablePipelineEngine:
    """Provides DBOS step registration and durable execution for the pipeline."""

    def __init__(self, runner: PipelineRunner) -> None:
        self.runner = runner

    @staticmethod
    @DBOS.step()
    async def durable_step_plan(runner_ref: Any, run_id: str, prompt: str, seed: int) -> str:
        """Durable step: Plan generation."""
        plan: Plan = await runner_ref.planner.plan(prompt, seed)
        runner_ref.variation_memory.check_and_record(plan.concept)
        return str(plan.model_dump_json())

    @staticmethod
    @DBOS.step()
    async def durable_step_keyframes(
        runner_ref: Any, run_id: str, plan_json: str, seed: int
    ) -> list[str]:
        """Durable step: Keyframe generation."""
        plan = Plan.model_validate_json(plan_json)
        keys: list[str] = []
        for kf in plan.shot_list.keyframes:
            key = compute_artifact_key("image_gen", "fake", "v1", kf.prompt, seed + kf.index)
            if not await runner_ref.artifact_store.exists(key):
                await runner_ref.budget_guard.check_budget_before_call(run_id, estimated_cost=0.1)
                img = await runner_ref.image_gen.generate_image(
                    kf.prompt, plan.site_bible, seed + kf.index
                )
                manifest = ProvenanceManifest(
                    artifact_key=key,
                    run_id=run_id,
                    port="image_gen",
                    adapter="fake",
                    model_or_version="v1",
                    seed=seed + kf.index,
                    cost_units=0.1,
                    file_extension="png",
                )
                await runner_ref.artifact_store.put(key, img, manifest)
                await runner_ref.budget_guard.record_spend(
                    CostRecord(
                        port="image_gen",
                        adapter="fake",
                        operation="generate_image",
                        cost_units=0.1,
                        run_id=run_id,
                    )
                )
            keys.append(key)
        return keys

    async def run_durable_workflow(
        self,
        run_id: str,
        prompt: str = "Modern Skyscraper",
        seed: int = 42,
    ) -> dict[str, Any]:
        """Run workflow under DBOS SetWorkflowID for step checkpointing and resumption."""
        DBOS.destroy()
        _ = DBOS(config=self.runner.dbos_config)
        DBOS.launch()
        try:
            with SetWorkflowID(run_id):
                return await self.runner.execute_run(run_id=run_id, prompt=prompt, seed=seed)
        finally:
            DBOS.destroy()
