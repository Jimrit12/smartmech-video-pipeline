"""Durable pipeline workflow orchestrated via DBOS steps over ports."""

import asyncio
import json
from pathlib import Path
from typing import Any

import structlog
from dbos import DBOS, DBOSConfig, SetWorkflowID
from opentelemetry import trace

from smartmech.application.budget_guard import BudgetGuard
from smartmech.application.compositor import Compositor
from smartmech.application.variation import VariationMemory
from smartmech.domain.artifact import ProvenanceManifest, compute_artifact_key
from smartmech.domain.autonomy import AutonomyLevel, PublishMetadata
from smartmech.domain.budget import BudgetConfig, CostRecord
from smartmech.domain.captions import generate_ass_content
from smartmech.domain.concept import Plan, SiteBible
from smartmech.domain.filtergraph import FiltergraphSpec
from smartmech.domain.qc import QCReport
from smartmech.domain.strategy import TailTrimPolicy
from smartmech.ports.aligner import AlignerPort
from smartmech.ports.artifact_store import ArtifactStorePort
from smartmech.ports.cost_ledger import CostLedgerPort
from smartmech.ports.image_gen import ImageGenPort
from smartmech.ports.planner import PlannerPort
from smartmech.ports.publisher import PublisherPort
from smartmech.ports.speech import SpeechPort
from smartmech.ports.video_gen import VideoGenPort

logger = structlog.get_logger()
tracer = trace.get_tracer("smartmech.pipeline")


def _write_file_in_thread(path: Path, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _write_json_in_thread(path: Path, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class PipelineRunner:
    """Orchestrates the 8-stage pipeline using DBOS steps and port adapters."""

    def __init__(
        self,
        planner: PlannerPort,
        image_gen: ImageGenPort,
        video_gen: VideoGenPort,
        speech: SpeechPort,
        aligner: AlignerPort,
        publisher: PublisherPort,
        artifact_store: ArtifactStorePort,
        cost_ledger: CostLedgerPort,
        budget_config: BudgetConfig | None = None,
        dbos_sqlite_path: str | None = None,
        output_directory: str = "output",
        autonomy_level: AutonomyLevel = AutonomyLevel.L1_HUMAN_APPROVAL,
    ) -> None:
        self.planner = planner
        self.image_gen = image_gen
        self.video_gen = video_gen
        self.speech = speech
        self.aligner = aligner
        self.publisher = publisher
        self.artifact_store = artifact_store
        self.cost_ledger = cost_ledger
        self.budget_config = budget_config or BudgetConfig()
        self.budget_guard = BudgetGuard(cost_ledger, self.budget_config)
        self.compositor = Compositor()
        self.variation_memory = VariationMemory()
        self.output_dir = Path(output_directory)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.autonomy_level = autonomy_level

        # Configure DBOS with local SQLite and telemetry disabled
        effective_dbos_path = (
            dbos_sqlite_path
            if dbos_sqlite_path is not None
            else str(self.output_dir / "smartmech_dbos.sqlite")
        )
        self.dbos_config: DBOSConfig = {
            "name": "smartmech",
            "system_database_url": f"sqlite:///{Path(effective_dbos_path).as_posix()}",
            "enable_otlp": False,
        }

    # =========================================================================
    # DBOS STEPS: Each stage returns small serializable values, never raw bytes
    # =========================================================================

    @staticmethod
    @DBOS.step()
    async def step_plan(runner: "PipelineRunner", run_id: str, prompt: str, seed: int) -> str:
        """Stage 1 DBOS Step: Plan generation."""
        with tracer.start_as_current_span("stage_plan"):
            logger.info("stage_plan_started", run_id=run_id)
            plan = await runner.planner.plan(prompt, seed)
            runner.variation_memory.check_and_record(plan.concept)
            logger.info("stage_plan_completed", run_id=run_id, title=plan.concept.title)
            return str(plan.model_dump_json())

    @staticmethod
    @DBOS.step()
    async def step_keyframe(
        runner: "PipelineRunner",
        run_id: str,
        kf_prompt: str,
        site_bible_json: str,
        seed: int,
        kf_index: int,
    ) -> str:
        """Stage 2 DBOS Step: Keyframe image generation (returns artifact key)."""
        site_bible = SiteBible.model_validate_json(site_bible_json)
        key = compute_artifact_key("image_gen", "fake", "v1", kf_prompt, seed + kf_index)
        if await runner.artifact_store.exists(key):
            logger.info("keyframe_cache_hit", keyframe_idx=kf_index, key=key)
            return key

        await runner.budget_guard.check_budget_before_call(run_id, estimated_cost=0.1)
        img_bytes = await runner.image_gen.generate_image(kf_prompt, site_bible, seed + kf_index)
        manifest = ProvenanceManifest(
            artifact_key=key,
            run_id=run_id,
            port="image_gen",
            adapter="fake",
            model_or_version="v1",
            seed=seed + kf_index,
            cost_units=0.1,
            file_extension="png",
        )
        await runner.artifact_store.put(key, img_bytes, manifest)
        await runner.budget_guard.record_spend(
            CostRecord(
                port="image_gen",
                adapter="fake",
                operation="generate_image",
                cost_units=0.1,
                run_id=run_id,
            )
        )
        return key

    @staticmethod
    @DBOS.step()
    async def step_clip(
        runner: "PipelineRunner",
        run_id: str,
        motion_prompt: str,
        duration_seconds: float,
        seed: int,
        tr_index: int,
        from_kf_key: str,
        to_kf_key: str | None,
    ) -> str:
        """Stage 3 DBOS Step: Transition clip generation (returns artifact key)."""
        key = compute_artifact_key("video_gen", "fake", "v1", motion_prompt, seed + tr_index)
        if await runner.artifact_store.exists(key):
            logger.info("clip_cache_hit", transition_idx=tr_index, key=key)
            return key

        from_img, _ = await runner.artifact_store.get(from_kf_key)
        to_img = None
        if to_kf_key:
            to_img, _ = await runner.artifact_store.get(to_kf_key)

        await runner.budget_guard.check_budget_before_call(run_id, estimated_cost=0.5)
        vid_bytes = await runner.video_gen.generate_transition(
            from_image=from_img,
            to_image=to_img,
            motion_prompt=motion_prompt,
            duration_seconds=duration_seconds,
            seed=seed + tr_index,
        )
        manifest = ProvenanceManifest(
            artifact_key=key,
            run_id=run_id,
            port="video_gen",
            adapter="fake",
            model_or_version="v1",
            seed=seed + tr_index,
            cost_units=0.5,
            file_extension="mp4",
        )
        await runner.artifact_store.put(key, vid_bytes, manifest)
        await runner.budget_guard.record_spend(
            CostRecord(
                port="video_gen",
                adapter="fake",
                operation="generate_transition",
                cost_units=0.5,
                run_id=run_id,
            )
        )
        return key

    @staticmethod
    @DBOS.step()
    async def step_speech(
        runner: "PipelineRunner",
        run_id: str,
        script_text: str,
        seed: int,
    ) -> str:
        """Stage 4 DBOS Step: Voiceover speech synthesis (returns artifact key)."""
        speech_key = compute_artifact_key("speech", "fake", "v1", script_text, seed)
        if await runner.artifact_store.exists(speech_key):
            logger.info("speech_cache_hit", key=speech_key)
            return speech_key

        await runner.budget_guard.check_budget_before_call(run_id, estimated_cost=0.2)
        audio_bytes = await runner.speech.generate_speech(script_text)
        manifest = ProvenanceManifest(
            artifact_key=speech_key,
            run_id=run_id,
            port="speech",
            adapter="fake",
            model_or_version="v1",
            seed=seed,
            cost_units=0.2,
            file_extension="wav",
        )
        await runner.artifact_store.put(speech_key, audio_bytes, manifest)
        await runner.budget_guard.record_spend(
            CostRecord(
                port="speech",
                adapter="fake",
                operation="generate_speech",
                cost_units=0.2,
                run_id=run_id,
            )
        )
        return speech_key

    @staticmethod
    @DBOS.step()
    async def step_alignment(
        runner: "PipelineRunner",
        run_id: str,
        speech_key: str,
        script_text: str,
        run_dir_str: str,
    ) -> str:
        """Stage 5 DBOS Step: Forced alignment and ASS caption generation (returns ass path)."""
        audio_bytes, _ = await runner.artifact_store.get(speech_key)
        timestamps = await runner.aligner.align(audio_bytes, script_text)
        ass_content = generate_ass_content(
            timestamps,
            play_res_x=1080,
            play_res_y=1920,
            safe_margin_bottom=320,
        )
        ass_file = Path(run_dir_str) / "subtitles.ass"
        await asyncio.to_thread(_write_file_in_thread, ass_file, ass_content)
        return str(ass_file)

    @staticmethod
    @DBOS.step()
    async def step_composite(
        runner: "PipelineRunner",
        run_id: str,
        clip_keys: list[str],
        clip_durations: list[float],
        speech_key: str,
        ass_path: str,
        final_video_path_str: str,
    ) -> str:
        """Stage 6 DBOS Step: Composite clips, audio, and captions (returns video path)."""
        clip_paths: list[str] = []
        for ck in clip_keys:
            _, manifest = await runner.artifact_store.get(ck)
            p = runner.output_dir / "artifacts" / f"{ck}.{manifest.file_extension}"
            clip_paths.append(str(p))

        _, speech_manifest = await runner.artifact_store.get(speech_key)
        audio_path = (
            runner.output_dir / "artifacts" / f"{speech_key}.{speech_manifest.file_extension}"
        )

        spec = FiltergraphSpec(
            clip_paths=clip_paths,
            clip_durations=clip_durations,
            audio_path=str(audio_path),
            ass_path=ass_path,
            output_path=final_video_path_str,
            tail_trim_policy=TailTrimPolicy(trim_fraction=0.125),
        )
        await runner.compositor.render(spec)
        return final_video_path_str

    @staticmethod
    @DBOS.step()
    async def step_qc(
        runner: "PipelineRunner",
        run_id: str,
        final_video_path_str: str,
    ) -> str:
        """Stage 7 DBOS Step: Quality control validation (returns qc_report json)."""
        metrics = await runner.compositor.probe(final_video_path_str)
        qc_report = QCReport.evaluate(metrics)
        return str(qc_report.model_dump_json())

    @staticmethod
    @DBOS.step()
    async def step_publish_gate(
        runner: "PipelineRunner",
        run_id: str,
        final_video_path_str: str,
        plan_title: str,
        plan_premise: str,
        autonomy_level_str: str,
        qc_status_str: str,
    ) -> str:
        """Stage 8 DBOS Step: Publish / human approval gate (returns status string)."""
        publish_result = "PENDING_APPROVAL"
        if autonomy_level_str == AutonomyLevel.L2_AUTO_PUBLISH.value and qc_status_str == "PASS":
            logger.info("auto_publishing", run_id=run_id)
            pub_meta = PublishMetadata(
                title=plan_title,
                description=f"{plan_premise}\n\n#Shorts #Construction #Timelapse",
            )
            publish_result = await runner.publisher.publish(final_video_path_str, pub_meta)
        else:
            logger.info("human_approval_gate_held", level=autonomy_level_str)
        return publish_result

    # =========================================================================
    # DBOS WORKFLOW
    # =========================================================================

    @staticmethod
    @DBOS.workflow()
    async def _durable_pipeline_workflow(
        runner: "PipelineRunner",
        run_id: str,
        prompt: str,
        seed: int,
    ) -> dict[str, Any]:
        """Durable workflow orchestrating all 8 stages as discrete steps."""
        logger.info("pipeline_started", run_id=run_id, prompt=prompt, seed=seed)
        run_dir = runner.output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        with tracer.start_as_current_span("smartmech.run") as run_span:
            run_span.set_attribute("run_id", run_id)

            # Stage 1: Plan
            plan_json = await PipelineRunner.step_plan(runner, run_id, prompt, seed)
            plan = Plan.model_validate_json(plan_json)

            # Stage 2: Keyframes
            keyframe_keys: list[str] = []
            with tracer.start_as_current_span("stage_keyframes"):
                logger.info("stage_keyframes_started", run_id=run_id)
                for kf in plan.shot_list.keyframes:
                    key = await PipelineRunner.step_keyframe(
                        runner,
                        run_id,
                        kf.prompt,
                        plan.site_bible.model_dump_json(),
                        seed,
                        kf.index,
                    )
                    keyframe_keys.append(key)

            # Stage 3: Transition Clips
            clip_keys: list[str] = []
            clip_durations: list[float] = []
            with tracer.start_as_current_span("stage_clips"):
                logger.info("stage_clips_started", run_id=run_id)
                for tr in plan.shot_list.transitions:
                    clip_durations.append(tr.duration_seconds)
                    from_kf = keyframe_keys[tr.from_keyframe_idx]
                    to_kf = keyframe_keys[tr.to_keyframe_idx]
                    clip_key = await PipelineRunner.step_clip(
                        runner,
                        run_id,
                        tr.motion_prompt,
                        tr.duration_seconds,
                        seed,
                        tr.index,
                        from_kf,
                        to_kf,
                    )
                    clip_keys.append(clip_key)

            # Stage 4: Voiceover Speech
            with tracer.start_as_current_span("stage_speech"):
                logger.info("stage_speech_started", run_id=run_id)
                speech_key = await PipelineRunner.step_speech(
                    runner, run_id, plan.script.text, seed
                )

            # Stage 5: Forced Alignment and ASS Captions
            with tracer.start_as_current_span("stage_captions"):
                logger.info("stage_captions_started", run_id=run_id)
                ass_path = await PipelineRunner.step_alignment(
                    runner, run_id, speech_key, plan.script.text, str(run_dir)
                )

            # Stage 6: Compositor
            final_video_path = run_dir / "final.mp4"
            with tracer.start_as_current_span("stage_composite"):
                logger.info("stage_composite_started", run_id=run_id)
                await PipelineRunner.step_composite(
                    runner,
                    run_id,
                    clip_keys,
                    clip_durations,
                    speech_key,
                    ass_path,
                    str(final_video_path),
                )
                logger.info("stage_composite_completed", output=str(final_video_path))

            # Stage 7: Quality Control (QC)
            with tracer.start_as_current_span("stage_qc"):
                logger.info("stage_qc_started", run_id=run_id)
                qc_report_json = await PipelineRunner.step_qc(runner, run_id, str(final_video_path))
                qc_report = QCReport.model_validate_json(qc_report_json)
                logger.info("stage_qc_completed", status=qc_report.overall_status)

            # Stage 8: Publish / Approval Gate
            with tracer.start_as_current_span("stage_publish"):
                publish_result = await PipelineRunner.step_publish_gate(
                    runner,
                    run_id,
                    str(final_video_path),
                    plan.concept.title,
                    plan.concept.premise,
                    runner.autonomy_level.value,
                    qc_report.overall_status.value,
                )

            # Write Report JSON and Markdown
            total_spend = await runner.cost_ledger.get_run_cost(run_id)
            report_data = {
                "run_id": run_id,
                "status": qc_report.overall_status.value,
                "video_path": str(final_video_path.resolve()),
                "total_spend": total_spend,
                "qc_report": qc_report.model_dump(),
                "plan": plan.model_dump(),
                "publish_status": publish_result,
            }
            report_json_path = run_dir / "report.json"
            await asyncio.to_thread(_write_json_in_thread, report_json_path, report_data)

            report_md_path = run_dir / "report.md"
            md_content = (
                f"""# Pipeline Run Report: {run_id}

- **Title**: {plan.concept.title}
- **Status**: {qc_report.overall_status.value}
- **Output Video**: `{final_video_path.name}`
- **Total Spend**: {total_spend:.2f} cost units
- **Publish Status**: {publish_result}

## Quality Gates
| Gate | Status | Detail |
|---|---|---|
"""
                + "\n".join(
                    f"| {g.name} | {g.status.value} | {g.detail} |" for g in qc_report.gates
                )
                + "\n"
            )
            await asyncio.to_thread(_write_file_in_thread, report_md_path, md_content)

            logger.info("pipeline_completed", run_id=run_id, final_video=str(final_video_path))
            return report_data

    async def execute_run(
        self,
        run_id: str,
        prompt: str = "Constructing a modern skyscraper",
        seed: int = 42,
    ) -> dict[str, Any]:
        """Execute end-to-end pipeline under workflow ID = run_id using DBOS."""
        managed_dbos = False
        import dbos._dbos as _dbos_mod

        if _dbos_mod._dbos_global_instance is None:
            _ = DBOS(config=self.dbos_config)
            DBOS.launch()
            managed_dbos = True
        elif not _dbos_mod._dbos_global_instance._launched:
            DBOS.launch()
        try:
            with SetWorkflowID(run_id):
                return await self._durable_pipeline_workflow(self, run_id, prompt, seed)
        finally:
            if managed_dbos:
                DBOS.destroy()
                try:
                    loop = asyncio.get_running_loop()
                    loop._default_executor = None  # type: ignore[attr-defined]
                except Exception:
                    pass
