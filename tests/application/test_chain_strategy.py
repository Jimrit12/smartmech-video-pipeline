"""Tests for chaining strategies, capability negotiation, and fallback chains in PipelineRunner."""

from pathlib import Path

import pytest

from smartmech.adapters.fake_aligner import FakeAlignerAdapter
from smartmech.adapters.fake_image_gen import FakeImageGenAdapter
from smartmech.adapters.fake_planner import FakePlannerAdapter
from smartmech.adapters.fake_publisher import FakePublisherAdapter
from smartmech.adapters.fake_speech import FakeSpeechAdapter
from smartmech.adapters.fake_video_gen import FakeVideoGenAdapter
from smartmech.adapters.local_artifact_store import LocalArtifactStoreAdapter
from smartmech.adapters.memory_cost_ledger import MemoryCostLedgerAdapter
from smartmech.application.negotiation import (
    AdapterCandidate,
    CapabilityMismatchError,
    FallbackChain,
)
from smartmech.application.pipeline_runner import PipelineRunner
from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.domain.strategy import ChainStrategy


def test_tail_handoff_rejected_at_configuration_time(tmp_path: Path) -> None:
    """TAIL_HANDOFF is deferred in M2 and must be rejected at configuration time with a clear error."""
    with pytest.raises(ValueError, match=r"TAIL_HANDOFF.*deferred.*0012"):
        PipelineRunner(
            planner=FakePlannerAdapter(),
            image_gen=FakeImageGenAdapter(),
            video_gen=FakeVideoGenAdapter(),
            speech=FakeSpeechAdapter(),
            aligner=FakeAlignerAdapter(),
            publisher=FakePublisherAdapter(),
            artifact_store=LocalArtifactStoreAdapter(tmp_path / "artifacts"),
            cost_ledger=MemoryCostLedgerAdapter(),
            output_directory=str(tmp_path),
            chain_strategy=ChainStrategy.TAIL_HANDOFF,
        )


@pytest.mark.asyncio
async def test_first_last_negotiation_fails_when_adapter_lacks_support(tmp_path: Path) -> None:
    """When FIRST_LAST is configured, adapters without supports_last_frame must fail negotiation."""
    caps_without_last = AdapterCapabilities(
        aspect_ratios=["9:16"],
        supports_first_frame=True,
        supports_last_frame=False,
    )
    unsupported_video_gen = FakeVideoGenAdapter(capabilities=caps_without_last)

    runner = PipelineRunner(
        planner=FakePlannerAdapter(),
        image_gen=FakeImageGenAdapter(),
        video_gen=unsupported_video_gen,
        speech=FakeSpeechAdapter(),
        aligner=FakeAlignerAdapter(),
        publisher=FakePublisherAdapter(),
        artifact_store=LocalArtifactStoreAdapter(tmp_path / "artifacts"),
        cost_ledger=MemoryCostLedgerAdapter(),
        output_directory=str(tmp_path),
        chain_strategy=ChainStrategy.FIRST_LAST,
    )

    with pytest.raises(CapabilityMismatchError, match="No available and capable adapter found"):
        await runner.execute_run("test_first_last_fail", "First last negotiation test", 42)


@pytest.mark.asyncio
async def test_fallback_chain_and_circuit_breaker_in_runner(tmp_path: Path) -> None:
    """Test that PipelineRunner executes secondary adapter in FallbackChain when primary fails."""
    primary_called = 0
    secondary_called = 0

    class FailingVideoGen(FakeVideoGenAdapter):
        async def generate_transition(
            self,
            from_image: bytes,
            to_image: bytes | None,
            motion_prompt: str,
            duration_seconds: float,
            seed: int,
        ) -> bytes:
            nonlocal primary_called
            primary_called += 1
            raise RuntimeError("Primary video vendor outage 503")

    class WorkingVideoGen(FakeVideoGenAdapter):
        async def generate_transition(
            self,
            from_image: bytes,
            to_image: bytes | None,
            motion_prompt: str,
            duration_seconds: float,
            seed: int,
        ) -> bytes:
            nonlocal secondary_called
            secondary_called += 1
            return await super().generate_transition(
                from_image, to_image, motion_prompt, duration_seconds, seed
            )

    failing_adapter = FailingVideoGen()
    working_adapter = WorkingVideoGen()

    cand1 = AdapterCandidate("failing_primary", failing_adapter, failing_adapter.capabilities)
    cand2 = AdapterCandidate("working_secondary", working_adapter, working_adapter.capabilities)
    custom_video_chain = FallbackChain("video_gen", [cand1, cand2])

    runner = PipelineRunner(
        planner=FakePlannerAdapter(),
        image_gen=FakeImageGenAdapter(),
        video_gen=failing_adapter,
        speech=FakeSpeechAdapter(),
        aligner=FakeAlignerAdapter(),
        publisher=FakePublisherAdapter(),
        artifact_store=LocalArtifactStoreAdapter(tmp_path / "artifacts"),
        cost_ledger=MemoryCostLedgerAdapter(),
        output_directory=str(tmp_path),
        video_gen_chain=custom_video_chain,
    )

    report = await runner.execute_run("test_fallback_run", "Fallback verification tower", 10)
    assert report["status"] == "PASS"
    assert primary_called >= 1, "Primary adapter should have been attempted"
    assert secondary_called == 5, "Secondary adapter should have completed all 5 transitions"
    assert cand1.circuit_breaker.failure_count >= 1, (
        "Primary circuit breaker should have recorded failures"
    )
