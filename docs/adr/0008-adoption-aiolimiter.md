# ADR-0008: Adoption of Aiolimiter for Rate Limiting

- **Status**: Accepted
- **Date**: 2026-10-19
- **Author**: Jimrit

## Purpose
Enforce per-vendor concurrency and rate limits (e.g. requests per minute / second) across asynchronous API adapters.

## License & Metadata
- **License**: Apache-2.0
- **Version**: `aiolimiter==1.3.0`

## Alternatives Evaluated
1. **asyncio.Semaphore**: Controls concurrency but does not enforce time-window rate limits (leaky bucket).
2. **ratelimit**: Synchronous only; blocks the asyncio event loop.

## Spike Evidence
Verified in [`tests/spikes/test_aiolimiter_spike.py`](file:///C:/Users/SHRIT-12/projects/smartmech-video-pipeline/tests/spikes/test_aiolimiter_spike.py):
- `AsyncLimiter` enforcing rate limits across async tasks without blocking the event loop.

## Fallback Strategy
Custom token bucket implementation using `asyncio.sleep` and monotonic clocks.

## Production Implementation
Wired into `smartmech.application.negotiation.AdapterCandidate`:
- Each candidate maintains an `AsyncLimiter` configured with `capabilities.requests_per_minute` over a 60.0s time period.
- Operations are executed inside `async with self.rate_limiter:` in tandem with `async with self.semaphore:` bounded by `capabilities.max_concurrent_requests`.

