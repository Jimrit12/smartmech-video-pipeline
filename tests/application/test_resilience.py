"""Tests for tenacity retries, content-policy non-retry, and aiolimiter rate bounds (D6)."""

import asyncio
import time
from typing import Any

import pytest

from smartmech.application.negotiation import (
    AdapterCandidate,
    ContentPolicyRefusalError,
    TransientAdapterError,
)
from smartmech.domain.capabilities import AdapterCapabilities


class DummyMockAdapter:
    def __init__(self) -> None:
        self.call_count = 0


@pytest.mark.asyncio
async def test_transient_5xx_retried_with_backoff() -> None:
    """Assert that a transient 5xx is retried with backoff and succeeds on subsequent attempt."""
    adapter = DummyMockAdapter()
    caps = AdapterCapabilities(max_concurrent_requests=5, requests_per_minute=600)
    candidate = AdapterCandidate(
        "mock_vendor",
        adapter,
        caps,
        max_retries=4,
        retry_multiplier=0.01,
    )

    attempts = 0
    start_time = time.monotonic()

    async def transient_operation(ad: DummyMockAdapter) -> str:
        nonlocal attempts
        attempts += 1
        ad.call_count += 1
        if attempts < 3:
            raise TransientAdapterError(f"HTTP 503 Service Unavailable (attempt {attempts})")
        return "success_after_retries"

    result = await candidate.execute(transient_operation)
    elapsed = time.monotonic() - start_time

    assert result == "success_after_retries"
    assert attempts == 3, "Operation should have been attempted 3 times"
    assert candidate.invocation_count == 3
    assert elapsed >= 0.02, "Backoff wait should have introduced delay between retries"


@pytest.mark.asyncio
async def test_content_policy_refusal_fails_immediately_zero_retries() -> None:
    """Assert that a content-policy refusal fails immediately with zero retries."""
    adapter = DummyMockAdapter()
    caps = AdapterCapabilities(max_concurrent_requests=5, requests_per_minute=600)
    candidate = AdapterCandidate(
        "moderated_vendor",
        adapter,
        caps,
        max_retries=4,
        retry_multiplier=0.01,
    )

    attempts = 0

    async def refused_operation(ad: DummyMockAdapter) -> str:
        nonlocal attempts
        attempts += 1
        ad.call_count += 1
        raise ContentPolicyRefusalError("Content policy refusal: prompt violates safety guidelines")

    with pytest.raises(ContentPolicyRefusalError, match="violates safety guidelines"):
        await candidate.execute(refused_operation)

    assert attempts == 1, "Content-policy refusal must fail immediately with zero retries"
    assert candidate.invocation_count == 1


@pytest.mark.asyncio
async def test_requests_bounded_by_declared_rate_limit() -> None:
    """Assert that requests to an adapter are bounded by its declared rate limit."""
    adapter = DummyMockAdapter()
    # 60 requests per minute = 1 request per second
    caps = AdapterCapabilities(max_concurrent_requests=5, requests_per_minute=60)
    candidate = AdapterCandidate(
        "rate_limited_vendor",
        adapter,
        caps,
        max_retries=1,
    )
    # Manually configure rate limiter to 2 requests per 0.20 seconds for deterministic fast test
    from aiolimiter import AsyncLimiter

    candidate.rate_limiter = AsyncLimiter(max_rate=2, time_period=0.20)

    start_time = time.monotonic()

    async def quick_task(_ad: Any) -> int:
        return 1

    # Execute 4 requests when limit is 2 per 0.20s: 3rd and 4th requests must be throttled
    results = await asyncio.gather(
        candidate.execute(quick_task),
        candidate.execute(quick_task),
        candidate.execute(quick_task),
        candidate.execute(quick_task),
    )
    elapsed = time.monotonic() - start_time

    assert sum(results) == 4
    assert elapsed >= 0.18, f"Rate limiter should throttle requests; took {elapsed:.3f} s"


@pytest.mark.asyncio
async def test_requests_bounded_by_concurrency_semaphore() -> None:
    """Assert that concurrent calls to an adapter never exceed max_concurrent_requests."""
    adapter = DummyMockAdapter()
    caps = AdapterCapabilities(max_concurrent_requests=2, requests_per_minute=6000)
    candidate = AdapterCandidate("concurrency_vendor", adapter, caps)

    current_concurrent = 0
    max_concurrent_observed = 0

    async def slow_task(_ad: Any) -> None:
        nonlocal current_concurrent, max_concurrent_observed
        current_concurrent += 1
        max_concurrent_observed = max(max_concurrent_observed, current_concurrent)
        await asyncio.sleep(0.05)
        current_concurrent -= 1

    await asyncio.gather(*(candidate.execute(slow_task) for _ in range(6)))

    assert max_concurrent_observed <= 2, (
        f"Concurrency exceeded limit: {max_concurrent_observed} > 2"
    )
