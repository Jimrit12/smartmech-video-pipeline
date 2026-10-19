"""Test durable workflow kill-mid-run and resumption using DBOS on SQLite."""

from pathlib import Path
from typing import Any, cast

from dbos import DBOS, DBOSConfig, SetWorkflowID


def test_kill_mid_run_and_resume_without_reinvoking_steps(tmp_path: Path) -> None:
    db_file = tmp_path / "resume_test_dbos.sqlite"
    raw_config: dict[str, Any] = {
        "name": "smartmech_resume",
        "system_database_url": f"sqlite:///{db_file.as_posix()}",
        "telemetry": {"disable_otlp": True},
    }
    config = cast("DBOSConfig", raw_config)

    step_executions = {
        "plan": 0,
        "keyframes": 0,
        "clips": 0,
        "composite": 0,
    }

    # Define DBOS steps with execution tracking
    @DBOS.step()
    def durable_step_plan() -> str:
        step_executions["plan"] += 1
        return "plan_data_recorded"

    @DBOS.step()
    def durable_step_keyframes(plan: str) -> list[str]:
        step_executions["keyframes"] += 1
        return [f"{plan}_kf0", f"{plan}_kf1"]

    @DBOS.step()
    def durable_step_clips(kfs: list[str]) -> str:
        step_executions["clips"] += 1
        return f"{'_'.join(kfs)}_clips_rendered"

    @DBOS.step()
    def durable_step_composite(clips: str) -> str:
        step_executions["composite"] += 1
        return f"{clips}_final.mp4"

    kill_switch = True

    @DBOS.workflow()
    def full_pipeline_workflow() -> str:
        p = durable_step_plan()
        k = durable_step_keyframes(p)
        if kill_switch:
            raise KeyboardInterrupt("Simulated process kill mid-run after keyframes")
        c = durable_step_clips(k)
        return durable_step_composite(c)

    workflow_id = "test-run-kill-resume-42"

    # --- Run 1: Interrupted mid-run after plan and keyframes ---
    DBOS.destroy()
    _ = DBOS(config=config)
    DBOS.launch()
    try:
        try:
            with SetWorkflowID(workflow_id):
                full_pipeline_workflow()
        except KeyboardInterrupt:
            pass
    finally:
        DBOS.destroy()

    # Verify state after Run 1: plan and keyframes completed once, clips not executed
    assert step_executions["plan"] == 1
    assert step_executions["keyframes"] == 1
    assert step_executions["clips"] == 0
    assert step_executions["composite"] == 0

    # --- Run 2: Resume exact same workflow ID ---
    _ = DBOS(config=config)
    DBOS.launch()
    kill_switch = False
    try:
        with SetWorkflowID(workflow_id):
            final_result = full_pipeline_workflow()
    finally:
        DBOS.destroy()

    # Resumption must NOT re-invoke the completed plan and keyframes steps!
    assert step_executions["plan"] == 1, "durable_step_plan must not re-execute on resume"
    assert step_executions["keyframes"] == 1, "durable_step_keyframes must not re-execute on resume"
    # Clips and composite completed in resumption
    assert step_executions["clips"] == 1
    assert step_executions["composite"] == 1
    assert "final.mp4" in final_result
