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
