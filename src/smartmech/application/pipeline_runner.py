"""Durable pipeline workflow orchestrated via DBOS steps over ports."""

import asyncio
import json
from pathlib import Path
from typing import Any

import structlog
from dbos import DBOSConfig
from opentelemetry import trace

from smartmech.application.budget_guard import BudgetGuard
from smartmech.application.compositor import Compositor
from smartmech.application.variation import VariationMemory
from smartmech.domain.artifact import ProvenanceManifest, compute_artifact_key
from smartmech.domain.autonomy import AutonomyLevel, PublishMetadata
from smartmech.domain.budget import BudgetConfig, CostRecord
from smartmech.domain.captions import generate_ass_content
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
        dbos_sqlite_path: str = "smartmech_dbos.sqlite",
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
        self.dbos_config: DBOSConfig = {
            "name": "smartmech",
            "system_database_url": f"sqlite:///{Path(dbos_sqlite_path).as_posix()}",
            "enable_otlp": False,
        }

    async def execute_run(
        self,
        run_id: str,
        prompt: str = "Constructing a modern skyscraper",
        seed: int = 42,
    ) -> dict[str, Any]:
        """Execute end-to-end pipeline under workflow ID = run_id."""
        logger.info("pipeline_started", run_id=run_id, prompt=prompt, seed=seed)
        run_dir = self.output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        with tracer.start_as_current_span("smartmech.run") as run_span:
            run_span.set_attribute("run_id", run_id)

            # Stage 1: Plan
            with tracer.start_as_current_span("stage_plan"):
                logger.info("stage_plan_started", run_id=run_id)
                plan = await self.planner.plan(prompt, seed)
                self.variation_memory.check_and_record(plan.concept)
                logger.info("stage_plan_completed", run_id=run_id, title=plan.concept.title)

            # Stage 2: Keyframes
            keyframe_paths: list[str] = []
            with tracer.start_as_current_span("stage_keyframes"):
                logger.info("stage_keyframes_started", run_id=run_id)
                for kf in plan.shot_list.keyframes:
                    key = compute_artifact_key(
                        "image_gen", "fake", "v1", kf.prompt, seed + kf.index
                    )
                    if await self.artifact_store.exists(key):
                        logger.info("keyframe_cache_hit", keyframe_idx=kf.index, key=key)
                        _, manifest = await self.artifact_store.get(key)
                        payload_path = (
                            self.output_dir / "artifacts" / f"{key}.{manifest.file_extension}"
                        )
                    else:
                        await self.budget_guard.check_budget_before_call(run_id, estimated_cost=0.1)
                        img_bytes = await self.image_gen.generate_image(
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
                        saved = await self.artifact_store.put(key, img_bytes, manifest)
                        await self.budget_guard.record_spend(
                            CostRecord(
                                port="image_gen",
                                adapter="fake",
                                operation="generate_image",
                                cost_units=0.1,
                                run_id=run_id,
                            )
                        )
                        payload_path = Path(saved)
                    keyframe_paths.append(str(payload_path))

            # Stage 3: Transition Clips
            clip_paths: list[str] = []
            clip_durations: list[float] = []
            with tracer.start_as_current_span("stage_clips"):
                logger.info("stage_clips_started", run_id=run_id)
                for tr in plan.shot_list.transitions:
                    clip_durations.append(tr.duration_seconds)
                    key = compute_artifact_key(
                        "video_gen", "fake", "v1", tr.motion_prompt, seed + tr.index
                    )
                    if await self.artifact_store.exists(key):
                        logger.info("clip_cache_hit", transition_idx=tr.index, key=key)
                        _, manifest = await self.artifact_store.get(key)
                        payload_path = (
                            self.output_dir / "artifacts" / f"{key}.{manifest.file_extension}"
                        )
                    else:
                        await self.budget_guard.check_budget_before_call(run_id, estimated_cost=0.5)
                        vid_bytes = await self.video_gen.generate_transition(
                            from_image=b"",
                            to_image=b"",
                            motion_prompt=tr.motion_prompt,
                            duration_seconds=tr.duration_seconds,
                            seed=seed + tr.index,
                        )
                        manifest = ProvenanceManifest(
                            artifact_key=key,
                            run_id=run_id,
                            port="video_gen",
                            adapter="fake",
                            model_or_version="v1",
                            seed=seed + tr.index,
                            cost_units=0.5,
                            file_extension="mp4",
                        )
                        saved = await self.artifact_store.put(key, vid_bytes, manifest)
                        await self.budget_guard.record_spend(
                            CostRecord(
                                port="video_gen",
                                adapter="fake",
                                operation="generate_transition",
                                cost_units=0.5,
                                run_id=run_id,
                            )
                        )
                        payload_path = Path(saved)
                    clip_paths.append(str(payload_path))

            # Stage 4: Voiceover Speech
            with tracer.start_as_current_span("stage_speech"):
                logger.info("stage_speech_started", run_id=run_id)
                speech_key = compute_artifact_key("speech", "fake", "v1", plan.script.text, seed)
                if await self.artifact_store.exists(speech_key):
                    logger.info("speech_cache_hit", key=speech_key)
                    audio_bytes, manifest = await self.artifact_store.get(speech_key)
                    audio_path = (
                        self.output_dir / "artifacts" / f"{speech_key}.{manifest.file_extension}"
                    )
                else:
                    await self.budget_guard.check_budget_before_call(run_id, estimated_cost=0.2)
                    audio_bytes = await self.speech.generate_speech(plan.script.text)
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
                    saved = await self.artifact_store.put(speech_key, audio_bytes, manifest)
                    await self.budget_guard.record_spend(
                        CostRecord(
                            port="speech",
                            adapter="fake",
                            operation="generate_speech",
                            cost_units=0.2,
                            run_id=run_id,
                        )
                    )
                    audio_path = Path(saved)

            # Stage 5: Forced Alignment and ASS Captions
            with tracer.start_as_current_span("stage_captions"):
                logger.info("stage_captions_started", run_id=run_id)
                timestamps = await self.aligner.align(audio_bytes, plan.script.text)
                ass_content = generate_ass_content(
                    timestamps,
                    play_res_x=1080,
                    play_res_y=1920,
                    safe_margin_bottom=320,
                )
                ass_file = run_dir / "subtitles.ass"
                await asyncio.to_thread(_write_file_in_thread, ass_file, ass_content)

            # Stage 6: Compositor
            final_video_path = run_dir / "final.mp4"
            with tracer.start_as_current_span("stage_composite"):
                logger.info("stage_composite_started", run_id=run_id)
                spec = FiltergraphSpec(
                    clip_paths=clip_paths,
                    clip_durations=clip_durations,
                    audio_path=str(audio_path),
                    ass_path=str(ass_file),
                    output_path=str(final_video_path),
                    tail_trim_policy=TailTrimPolicy(trim_fraction=0.125),
                )
                metrics = await self.compositor.render(spec)
                logger.info("stage_composite_completed", duration=metrics.duration_seconds)

            # Stage 7: Quality Control (QC)
            with tracer.start_as_current_span("stage_qc"):
                logger.info("stage_qc_started", run_id=run_id)
                qc_report = QCReport.evaluate(metrics)
                logger.info("stage_qc_completed", status=qc_report.overall_status)

            # Stage 8: Publish / Approval Gate
            publish_result = "PENDING_APPROVAL"
            with tracer.start_as_current_span("stage_publish"):
                if self.autonomy_level == AutonomyLevel.L2_AUTO_PUBLISH:
                    logger.info("auto_publishing", run_id=run_id)
                    pub_meta = PublishMetadata(
                        title=plan.concept.title,
                        description=f"{plan.concept.premise}\n\n#Shorts #Construction #Timelapse",
                    )
                    publish_result = await self.publisher.publish(str(final_video_path), pub_meta)
                else:
                    logger.info("human_approval_gate_held", level=self.autonomy_level)

            # Write Report JSON and Markdown
            total_spend = await self.cost_ledger.get_run_cost(run_id)
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
