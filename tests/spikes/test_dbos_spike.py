"""Spike test proving DBOS durable execution on SQLite with step idempotency and no telemetry."""

from pathlib import Path
from typing import Any, cast

from dbos import DBOS, DBOSConfig, SetWorkflowID


def test_dbos_sqlite_durable_execution(tmp_path: Path) -> None:
    db_file = tmp_path / "spike_dbos.sqlite"
    raw_config: dict[str, Any] = {
        "name": "smartmech_spike",
        "system_database_url": f"sqlite:///{db_file.as_posix()}",
        "telemetry": {"disable_otlp": True},
    }
    config = cast("DBOSConfig", raw_config)

    # Ensure clean instance
    DBOS.destroy()
    _ = DBOS(config=config)

    execution_counter = {"step_a": 0, "step_b": 0}

    @DBOS.step()
    def step_a() -> str:
        execution_counter["step_a"] += 1
        return "step_a_completed"

    @DBOS.step()
    def step_b(prev: str) -> str:
        execution_counter["step_b"] += 1
        return f"{prev}_and_step_b_completed"

    @DBOS.workflow()
    def pipeline_workflow() -> str:
        res_a = step_a()
        return step_b(res_a)

    DBOS.launch()
    try:
        # First execution under workflow ID
        workflow_id = "test-workflow-run-001"
        with SetWorkflowID(workflow_id):
            result1 = pipeline_workflow()

        assert result1 == "step_a_completed_and_step_b_completed"
        assert execution_counter["step_a"] == 1
        assert execution_counter["step_b"] == 1

        # Second execution with identical workflow ID (resuming/idempotency)
        with SetWorkflowID(workflow_id):
            result2 = pipeline_workflow()

        assert result2 == "step_a_completed_and_step_b_completed"
        # Crucial invariant: steps must NOT re-execute on rerun
        assert execution_counter["step_a"] == 1
        assert execution_counter["step_b"] == 1
    finally:
        DBOS.destroy()
