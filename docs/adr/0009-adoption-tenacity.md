# ADR-0009: Adoption of Tenacity for Transient Error Retries

- **Status**: Accepted
- **Date**: 2026-10-19
- **Author**: Jimrit

## Purpose
Retry transient errors (HTTP 429 rate limit, 5xx server errors, network timeouts) with exponential backoff and jitter, while immediately raising non-transient content policy refusals.

## License & Metadata
- **License**: Apache-2.0
- **Version**: `tenacity==9.2.1`

## Alternatives Evaluated
1. **backoff**: Good, but Tenacity offers finer declarative control over retry predicates, stop conditions, and asyncio integration.
2. **Custom retry loops**: High boilerplate, error-prone backoff and jitter calculations.

## Spike Evidence
Verified in [`tests/spikes/test_tenacity_spike.py`](file:///C:/Users/SHRIT-12/projects/smartmech-video-pipeline/tests/spikes/test_tenacity_spike.py):
- Transient errors retried up to stop limit.
- Non-transient safety/policy refusals fail immediately without retries.

## Fallback Strategy
Custom decorator with exponential backoff algorithm.
