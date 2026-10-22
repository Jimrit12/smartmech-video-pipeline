"""Adapter capabilities negotiation, fallback chains, rate limiting, and circuit breaker."""

import asyncio
import time
from collections.abc import Callable
from typing import Any, TypeVar

from aiolimiter import AsyncLimiter
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from smartmech.domain.capabilities import AdapterCapabilities

T = TypeVar("T")


class CapabilityMismatchError(Exception):
    """Raised when no adapter in the fallback chain satisfies the required capabilities."""


class CircuitBreakerOpenError(Exception):
    """Raised when an adapter's circuit is currently open due to excessive failures."""


class ContentPolicyRefusalError(Exception):
    """Raised when a vendor rejects content due to policy/safety violation. Never retried."""


class TransientAdapterError(Exception):
    """Raised on transient vendor failures (5xx, rate limits, timeouts). Retried with backoff."""


def is_transient_error(exc: BaseException) -> bool:
    """Determine if an exception represents a transient, retryable failure."""
    if isinstance(exc, ContentPolicyRefusalError):
        return False
    if isinstance(exc, TransientAdapterError):
        return True
    msg = str(exc).lower()
    # Never retry policy refusals or safety blocks
    if any(
        term in msg
        for term in ["content policy", "safety violation", "prompt refused", "moderation"]
    ):
        return False
    # Retry 5xx, rate limit, timeout, temporary network errors
    if any(
        term in msg
        for term in [
            "500",
            "502",
            "503",
            "504",
            "rate limit",
            "timeout",
            "temporarily unavailable",
            "connection reset",
        ]
    ):
        return True
    return False


class CircuitBreaker:
    """Tracks adapter error rates and temporarily trips open after consecutive failures."""

    def __init__(self, failure_threshold: int = 3, reset_timeout_seconds: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.is_open = False

    def can_execute(self) -> bool:
        if not self.is_open:
            return True
        if self.last_failure_time is not None:
            if time.monotonic() - self.last_failure_time >= self.reset_timeout_seconds:
                # Half-open: attempt recovery
                self.is_open = False
                self.failure_count = 0
                return True
        return False

    def record_success(self) -> None:
        self.failure_count = 0
        self.is_open = False
        self.last_failure_time = None

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True


class AdapterCandidate:
    """An adapter instance with its capabilities, circuit breaker, rate limiter, and retry logic."""

    def __init__(
        self,
        name: str,
        adapter: Any,
        capabilities: AdapterCapabilities,
        max_retries: int = 3,
        retry_multiplier: float = 0.05,
    ) -> None:
        self.name = name
        self.adapter = adapter
        self.capabilities = capabilities
        self.circuit_breaker = CircuitBreaker()
        self.semaphore = asyncio.Semaphore(capabilities.max_concurrent_requests)
        self.rate_limiter = AsyncLimiter(
            max_rate=capabilities.requests_per_minute,
            time_period=60.0,
        )
        self.max_retries = max_retries
        self.retry_multiplier = retry_multiplier
        self.invocation_count = 0

    async def execute(self, operation: Callable[[Any], Any]) -> Any:
        """Execute an adapter operation bounded by concurrency, rate limits, and tenacity retries."""
        async with self.semaphore:
            async with self.rate_limiter:
                async for attempt in AsyncRetrying(
                    retry=retry_if_exception(is_transient_error),
                    stop=stop_after_attempt(self.max_retries),
                    wait=wait_exponential(multiplier=self.retry_multiplier, min=0.01, max=0.5),
                    reraise=True,
                ):
                    with attempt:
                        self.invocation_count += 1
                        return await operation(self.adapter)


class FallbackChain:
    """Ordered fallback chain of adapters for a specific port."""

    def __init__(self, port_name: str, candidates: list[AdapterCandidate]) -> None:
        self.port_name = port_name
        self.candidates = candidates

    def find_capable_candidate(
        self,
        required_aspect_ratio: str = "9:16",
        required_duration: float | None = None,
        require_last_frame: bool = False,
    ) -> AdapterCandidate:
        """Find the first available and capable adapter whose circuit is closed."""
        for candidate in self.candidates:
            caps = candidate.capabilities
            if required_aspect_ratio not in caps.aspect_ratios:
                continue
            if required_duration is not None:
                if (
                    required_duration < caps.min_duration_seconds
                    or required_duration > caps.max_duration_seconds
                ):
                    continue
            if require_last_frame and not caps.supports_last_frame:
                continue
            if candidate.circuit_breaker.can_execute():
                return candidate

        raise CapabilityMismatchError(
            f"No available and capable adapter found in fallback chain for port '{self.port_name}' "
            f"(aspect_ratio={required_aspect_ratio}, duration={required_duration}, last_frame={require_last_frame})"
        )

    async def execute_with_fallback(
        self,
        operation: Callable[[Any], Any],
        required_aspect_ratio: str = "9:16",
        required_duration: float | None = None,
        require_last_frame: bool = False,
    ) -> Any:
        """Execute operation against primary candidate, falling back to next available on failure."""
        last_error: Exception | None = None
        for candidate in self.candidates:
            caps = candidate.capabilities
            if required_aspect_ratio not in caps.aspect_ratios:
                continue
            if required_duration is not None:
                if (
                    required_duration < caps.min_duration_seconds
                    or required_duration > caps.max_duration_seconds
                ):
                    continue
            if require_last_frame and not caps.supports_last_frame:
                continue
            if not candidate.circuit_breaker.can_execute():
                continue

            try:
                res = await candidate.execute(operation)
                candidate.circuit_breaker.record_success()
                return res
            except Exception as exc:
                candidate.circuit_breaker.record_failure()
                last_error = exc

        if last_error is not None:
            raise last_error
        raise CapabilityMismatchError(
            f"No capable candidate could execute operation for {self.port_name}"
        )
