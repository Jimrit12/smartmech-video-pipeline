"""Tests for capabilities negotiation, fallback chains, and circuit breaker."""

import time

import pytest

from smartmech.application.negotiation import (
    AdapterCandidate,
    CapabilityMismatchError,
    CircuitBreaker,
    FallbackChain,
)
from smartmech.domain.capabilities import AdapterCapabilities


def test_circuit_breaker_trips_and_recovers() -> None:
    cb = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=0.01)
    assert cb.can_execute()

    cb.record_failure()
    assert cb.can_execute()

    # Second failure trips breaker
    cb.record_failure()
    assert cb.is_open
    assert not cb.can_execute()

    # Sleep past reset timeout to test half-open recovery
    time.sleep(0.02)
    assert cb.can_execute()
    assert not cb.is_open


@pytest.mark.asyncio
async def test_fallback_chain_executes_fallback_on_primary_failure() -> None:
    class FailingAdapter:
        async def run(self) -> str:
            raise RuntimeError("Primary vendor 503 error")

    class WorkingAdapter:
        async def run(self) -> str:
            return "fallback_success"

    caps = AdapterCapabilities(aspect_ratios=["9:16"])
    cand1 = AdapterCandidate("primary", FailingAdapter(), caps)
    cand2 = AdapterCandidate("secondary", WorkingAdapter(), caps)

    chain = FallbackChain("test_port", [cand1, cand2])

    result = await chain.execute_with_fallback(lambda a: a.run())
    assert result == "fallback_success"
    assert cand1.circuit_breaker.failure_count == 1
    assert cand2.circuit_breaker.failure_count == 0


def test_fallback_chain_filtering_capabilities() -> None:
    class MockAdapter:
        pass

    caps = AdapterCapabilities(
        aspect_ratios=["9:16"],
        min_duration_seconds=2.0,
        max_duration_seconds=8.0,
        supports_last_frame=False,
    )
    candidate = AdapterCandidate("cand", MockAdapter(), caps)
    chain = FallbackChain("video_port", [candidate])

    # Aspect ratio mismatch
    with pytest.raises(CapabilityMismatchError):
        chain.find_capable_candidate(required_aspect_ratio="16:9")

    # Duration below min
    with pytest.raises(CapabilityMismatchError):
        chain.find_capable_candidate(required_duration=1.0)

    # Duration above max
    with pytest.raises(CapabilityMismatchError):
        chain.find_capable_candidate(required_duration=10.0)

    # Requires last frame but not supported
    with pytest.raises(CapabilityMismatchError):
        chain.find_capable_candidate(require_last_frame=True)

    # Capable match
    found = chain.find_capable_candidate(required_duration=5.0)
    assert found.name == "cand"


@pytest.mark.asyncio
async def test_fallback_chain_all_fail_raises_last_error() -> None:
    class AlwaysFailingAdapter:
        async def run(self) -> str:
            raise ValueError("All adapters failed")

    caps = AdapterCapabilities(aspect_ratios=["9:16"])
    cand = AdapterCandidate("failing", AlwaysFailingAdapter(), caps)
    chain = FallbackChain("test_port", [cand])

    with pytest.raises(ValueError, match="All adapters failed"):
        await chain.execute_with_fallback(lambda a: a.run())
