"""Spike test proving aiolimiter rate limiting behavior."""

import time

import pytest
from aiolimiter import AsyncLimiter


@pytest.mark.asyncio
async def test_aiolimiter_rate_limiting() -> None:
    # 2 calls allowed per 0.2 seconds (each token regenerates in 0.1s)
    limiter = AsyncLimiter(max_rate=2, time_period=0.2)
    start = time.perf_counter()

    for _ in range(3):
        async with limiter:
            pass

    elapsed = time.perf_counter() - start
    # The 3rd acquire must wait for the token to replenish (at least 0.08s)
    assert elapsed >= 0.08
