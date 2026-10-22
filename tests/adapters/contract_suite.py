"""Shared contract test suite assertions that every port adapter must pass."""

import asyncio
from pathlib import Path

from smartmech.domain.adapter_identity import AdapterIdentity
from smartmech.domain.artifact import ProvenanceManifest
from smartmech.domain.autonomy import PublishMetadata
from smartmech.domain.budget import CostRecord
from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.domain.concept import SiteBible
from smartmech.ports.aligner import AlignerPort
from smartmech.ports.artifact_store import ArtifactStorePort
from smartmech.ports.cost_ledger import CostLedgerPort
from smartmech.ports.image_gen import ImageGenPort
from smartmech.ports.planner import PlannerPort
from smartmech.ports.publisher import PublisherPort
from smartmech.ports.speech import SpeechPort
from smartmech.ports.video_gen import VideoGenPort


async def verify_planner_contract(planner: PlannerPort) -> None:
    """Verify any PlannerPort implementation satisfies the planner contract."""
    caps = planner.capabilities
    assert isinstance(caps, AdapterCapabilities)
    assert isinstance(planner.identity, AdapterIdentity)
    assert planner.cost_estimate_per_call >= 0.0

    plan = await planner.plan(prompt="Constructing a 50-story commercial tower", seed=42)
    assert len(plan.shot_list.keyframes) == 6
    assert len(plan.shot_list.transitions) == 5
    assert plan.script.word_count <= 100
    assert 30.0 <= plan.shot_list.total_raw_duration() <= 40.0


async def verify_image_gen_contract(image_gen: ImageGenPort) -> None:
    """Verify any ImageGenPort implementation satisfies the image generator contract."""
    caps = image_gen.capabilities
    assert isinstance(caps, AdapterCapabilities)
    assert isinstance(image_gen.identity, AdapterIdentity)
    assert image_gen.cost_estimate_per_call >= 0.0
    assert "9:16" in caps.aspect_ratios

    bible = SiteBible(
        location="Tokyo Bay",
        camera_rig="Fixed Rig",
        lens="24mm",
        height="10m",
        weather="Clear",
        light_direction="Dusk",
        palette=["#000000"],
        materials=["Steel"],
    )
    image_bytes = await image_gen.generate_image(
        prompt="Excavation underway", site_bible=bible, seed=1
    )
    assert isinstance(image_bytes, bytes)
    assert len(image_bytes) > 100  # Non-trivial image payload


async def verify_video_gen_contract(video_gen: VideoGenPort) -> None:
    """Verify any VideoGenPort implementation satisfies the video generator contract."""
    caps = video_gen.capabilities
    assert isinstance(caps, AdapterCapabilities)
    assert isinstance(video_gen.identity, AdapterIdentity)
    assert video_gen.cost_estimate_per_call >= 0.0
    assert "9:16" in caps.aspect_ratios

    dummy_frame = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
    video_bytes = await video_gen.generate_transition(
        from_image=dummy_frame,
        to_image=dummy_frame,
        motion_prompt="Transitioning from excavation to foundation",
        duration_seconds=5.0,
        seed=1,
    )
    assert isinstance(video_bytes, bytes)
    assert len(video_bytes) > 200


async def verify_speech_contract(speech: SpeechPort) -> None:
    """Verify any SpeechPort implementation satisfies the speech generator contract."""
    caps = speech.capabilities
    assert isinstance(caps, AdapterCapabilities)
    assert isinstance(speech.identity, AdapterIdentity)
    assert speech.cost_estimate_per_call >= 0.0

    audio_bytes = await speech.generate_speech(
        text="Thirty seconds of construction timelapse voiceover narrative."
    )
    assert isinstance(audio_bytes, bytes)
    assert len(audio_bytes) > 500


async def verify_aligner_contract(aligner: AlignerPort) -> None:
    """Verify any AlignerPort implementation satisfies the forced-aligner contract."""
    caps = aligner.capabilities
    assert isinstance(caps, AdapterCapabilities)
    assert isinstance(aligner.identity, AdapterIdentity)
    assert aligner.cost_estimate_per_call >= 0.0

    transcript = "Constructing fifty stories with millimeter precision."
    timestamps = await aligner.align(audio_bytes=b"RIFF\x00\x00\x00\x00WAVE", transcript=transcript)
    assert len(timestamps) > 0
    # Invariant: Timestamps must be non-decreasing
    for i in range(len(timestamps) - 1):
        assert timestamps[i].start_seconds <= timestamps[i].end_seconds
        assert timestamps[i].end_seconds <= timestamps[i + 1].start_seconds + 0.05


async def verify_publisher_contract(publisher: PublisherPort) -> None:
    """Verify any PublisherPort implementation satisfies the publisher contract."""
    caps = publisher.capabilities
    assert isinstance(caps, AdapterCapabilities)
    assert isinstance(publisher.identity, AdapterIdentity)
    assert publisher.cost_estimate_per_call >= 0.0

    metadata = PublishMetadata(
        title="Tower Rise #1",
        description="Timelapse of building assembly",
    )
    result_url = await publisher.publish(video_path="final.mp4", metadata=metadata)
    assert isinstance(result_url, str)
    assert len(result_url) > 5


async def verify_artifact_store_contract(store: ArtifactStorePort) -> None:
    """Verify any ArtifactStorePort implementation satisfies the content-addressed store contract."""
    key = "a" * 64
    assert not await store.exists(key)

    manifest = ProvenanceManifest(
        artifact_key=key,
        run_id="run-1",
        port="image_gen",
        adapter="fake",
        model_or_version="v1",
        seed=42,
        cost_units=0.5,
        file_extension="png",
    )
    payload = b"FAKE_PNG_PAYLOAD"

    saved_path = await store.put(key, payload, manifest)
    exists = await asyncio.to_thread(Path(saved_path).exists)
    assert exists
    assert await store.exists(key)

    loaded_payload, loaded_manifest = await store.get(key)
    assert loaded_payload == payload
    assert loaded_manifest.artifact_key == key
    assert loaded_manifest.run_id == "run-1"


async def verify_cost_ledger_contract(ledger: CostLedgerPort) -> None:
    """Verify any CostLedgerPort implementation satisfies the cost ledger contract."""
    assert await ledger.get_run_cost("run-xyz") == 0.0

    record = CostRecord(
        port="video_gen",
        adapter="fake",
        operation="generate_transition",
        cost_units=1.5,
        run_id="run-xyz",
    )
    await ledger.record_cost(record)
    assert await ledger.get_run_cost("run-xyz") == 1.5
    assert await ledger.get_daily_cost() >= 1.5
