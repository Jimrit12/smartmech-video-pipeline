"""Integration tests for PipelineRunner kill-mid-run and resumption on SQLite with DBOS."""

import asyncio
import subprocess
import sys
import time
from pathlib import Path

import pytest

from smartmech.adapters.local_artifact_store import LocalArtifactStoreAdapter
from smartmech.adapters.memory_cost_ledger import MemoryCostLedgerAdapter
from smartmech.application.pipeline_runner import PipelineRunner
from tests.integration.run_pipeline_subprocess import (
    LoggingFakeAlignerAdapter,
    LoggingFakeImageGenAdapter,
    LoggingFakePlannerAdapter,
    LoggingFakePublisherAdapter,
    LoggingFakeSpeechAdapter,
    LoggingFakeVideoGenAdapter,
)


@pytest.mark.asyncio
async def test_kill_and_resume_in_process(tmp_path: Path) -> None:
    """Test in-process mid-run failure after keyframes and resumption with exact same run_id."""
    output_dir = tmp_path / "in_process_output"
    artifacts_dir = output_dir / "artifacts"
    db_file = tmp_path / "in_process_dbos.sqlite"
    call_log = tmp_path / "in_process_call_log.txt"

    run_id = "run-in-process-kill-resume-101"
    prompt = "Modern Sky Tower Construction"
    seed = 42

    store = LocalArtifactStoreAdapter(base_directory=artifacts_dir)
    ledger = MemoryCostLedgerAdapter()

    # --- Phase 1: Run with injected failure on the first video clip ---
    runner_failing = PipelineRunner(
        planner=LoggingFakePlannerAdapter(call_log),
        image_gen=LoggingFakeImageGenAdapter(call_log),
        video_gen=LoggingFakeVideoGenAdapter(call_log, raise_on_first_clip=True),
        speech=LoggingFakeSpeechAdapter(call_log),
        aligner=LoggingFakeAlignerAdapter(call_log),
        publisher=LoggingFakePublisherAdapter(call_log),
        artifact_store=store,
        cost_ledger=ledger,
        dbos_sqlite_path=str(db_file),
        output_directory=str(output_dir),
    )

    with pytest.raises(
        KeyboardInterrupt, match="Simulated in-process crash mid-run after keyframes"
    ):
        await runner_failing.execute_run(run_id=run_id, prompt=prompt, seed=seed)

    # Inspect call log before rerun
    log_before = call_log.read_text(encoding="utf-8").splitlines()
    planner_calls_before = [line for line in log_before if line.startswith("planner:")]
    image_calls_before = [line for line in log_before if line.startswith("image_gen:")]
    video_calls_before = [line for line in log_before if line.startswith("video_gen:")]

    assert len(planner_calls_before) == 1, "Planner should have run once before failure"
    assert len(image_calls_before) == 6, "All 6 keyframes should have completed before clip failure"
    assert len(video_calls_before) == 0, "No clips should have completed in failing run"

    # --- Phase 2: Resume exact same run_id with healthy video generator ---
    runner_resumed = PipelineRunner(
        planner=LoggingFakePlannerAdapter(call_log),
        image_gen=LoggingFakeImageGenAdapter(call_log),
        video_gen=LoggingFakeVideoGenAdapter(call_log, raise_on_first_clip=False),
        speech=LoggingFakeSpeechAdapter(call_log),
        aligner=LoggingFakeAlignerAdapter(call_log),
        publisher=LoggingFakePublisherAdapter(call_log),
        artifact_store=store,
        cost_ledger=ledger,
        dbos_sqlite_path=str(db_file),
        output_directory=str(output_dir),
    )

    report = await runner_resumed.execute_run(run_id=run_id, prompt=prompt, seed=seed)
    assert report["status"] == "PASS"

    video_path = Path(report["video_path"])
    assert await asyncio.to_thread(video_path.exists), "Final video should be produced"

    # Inspect call log after rerun: keyframes and planner must NOT be re-executed!
    log_after = call_log.read_text(encoding="utf-8").splitlines()
    planner_calls_after = [line for line in log_after if line.startswith("planner:")]
    image_calls_after = [line for line in log_after if line.startswith("image_gen:")]
    video_calls_after = [line for line in log_after if line.startswith("video_gen:")]
    speech_calls_after = [line for line in log_after if line.startswith("speech:")]
    aligner_calls_after = [line for line in log_after if line.startswith("aligner:")]

    assert len(planner_calls_after) == 1, "Planner must NOT be reinvoked on resume"
    assert len(image_calls_after) == 6, "Keyframes must NOT be reinvoked on resume"
    assert len(video_calls_after) == 5, "All 5 transition clips should be generated"
    assert len(speech_calls_after) == 1, "Speech should be generated"
    assert len(aligner_calls_after) == 1, "Aligner should be executed"


def test_kill_and_resume_subprocess(tmp_path: Path) -> None:
    """Test real OS subprocess terminated after keyframes and resumed to completion."""
    output_dir = tmp_path / "subprocess_output"
    artifacts_dir = output_dir / "artifacts"
    db_file = tmp_path / "subprocess_dbos.sqlite"
    call_log = tmp_path / "subprocess_call_log.txt"
    signal_file = tmp_path / "signal_ready_to_kill.txt"

    run_id = "run-subprocess-kill-resume-202"
    prompt = "Modern Sky Tower Timelapse"
    seed = 42

    helper_script = Path(__file__).parent / "run_pipeline_subprocess.py"

    # --- Phase 1: Launch subprocess configured to block on the first clip ---
    cmd = [
        sys.executable,
        str(helper_script),
        "--run-id",
        run_id,
        "--dbos-sqlite",
        str(db_file),
        "--artifacts-dir",
        str(artifacts_dir),
        "--output-dir",
        str(output_dir),
        "--call-log",
        str(call_log),
        "--signal-file",
        str(signal_file),
        "--block-on-first-clip",
    ]

    proc = subprocess.Popen(cmd)

    # Wait for the signal file indicating keyframes are complete and first clip began
    start_time = time.monotonic()
    while not signal_file.exists():
        if time.monotonic() - start_time > 60.0:
            proc.kill()
            raise TimeoutError("Subprocess did not reach keyframe completion within 60s")
        time.sleep(0.5)

    # Subprocess has completed keyframes and is waiting on clip: TERMINATE IT
    proc.terminate()
    try:
        proc.wait(timeout=10.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5.0)

    # Inspect call log before rerun
    log_before = call_log.read_text(encoding="utf-8").splitlines()
    planner_calls_before = [line for line in log_before if line.startswith("planner:")]
    image_calls_before = [line for line in log_before if line.startswith("image_gen:")]
    video_calls_before = [line for line in log_before if line.startswith("video_gen:")]

    assert len(planner_calls_before) == 1, "Planner should have run once before kill"
    assert len(image_calls_before) == 6, "All 6 keyframes should have completed before kill"
    assert len(video_calls_before) == 0, "No clips should have completed before kill"

    # --- Phase 2: Rerun with the exact same run_id ---
    store = LocalArtifactStoreAdapter(base_directory=artifacts_dir)
    ledger = MemoryCostLedgerAdapter()

    runner_resumed = PipelineRunner(
        planner=LoggingFakePlannerAdapter(call_log),
        image_gen=LoggingFakeImageGenAdapter(call_log),
        video_gen=LoggingFakeVideoGenAdapter(call_log, block_on_first_clip=False),
        speech=LoggingFakeSpeechAdapter(call_log),
        aligner=LoggingFakeAlignerAdapter(call_log),
        publisher=LoggingFakePublisherAdapter(call_log),
        artifact_store=store,
        cost_ledger=ledger,
        dbos_sqlite_path=str(db_file),
        output_directory=str(output_dir),
    )

    report = asyncio.run(runner_resumed.execute_run(run_id=run_id, prompt=prompt, seed=seed))
    assert report["status"] == "PASS"

    video_path = Path(report["video_path"])
    assert video_path.exists(), "Final video should exist after resume"

    # Inspect call log after rerun: planner and keyframes must NOT be invoked again!
    log_after = call_log.read_text(encoding="utf-8").splitlines()
    planner_calls_after = [line for line in log_after if line.startswith("planner:")]
    image_calls_after = [line for line in log_after if line.startswith("image_gen:")]
    video_calls_after = [line for line in log_after if line.startswith("video_gen:")]

    assert len(planner_calls_after) == 1, "Planner must NOT be reinvoked on rerun"
    assert len(image_calls_after) == 6, "Keyframes must NOT be reinvoked on rerun"
    assert len(video_calls_after) == 5, "All 5 transition clips should complete on rerun"
