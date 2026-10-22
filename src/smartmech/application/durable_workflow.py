"""Durable pipeline workflow delegation (D1: duplicate steps removed)."""

from typing import Any

from smartmech.application.pipeline_runner import PipelineRunner


class DurablePipelineEngine:
    """Delegates to PipelineRunner's native DBOS workflow."""

    def __init__(self, runner: PipelineRunner) -> None:
        self.runner = runner

    async def run_durable_workflow(
        self,
        run_id: str,
        prompt: str = "Modern Skyscraper",
        seed: int = 42,
    ) -> dict[str, Any]:
        """Delegate directly to runner's native DBOS workflow."""
        return await self.runner.execute_run(run_id=run_id, prompt=prompt, seed=seed)
