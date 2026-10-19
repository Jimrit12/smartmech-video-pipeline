# ADR-0006: Adoption of Structlog for Structured Logging

- **Status**: Accepted
- **Date**: 2026-10-19
- **Author**: Jimrit

## Purpose
Produce structured JSON logs containing timestamp, event, level, run ID, step context, and duration metrics.

## License & Metadata
- **License**: Apache-2.0 / MIT
- **Version**: `structlog==26.1.0`

## Alternatives Evaluated
1. **logging (stdlib)**: Requires custom JSON formatters and lacks ergonomic contextual key-value binding across asynchronous execution.
2. **loguru**: Global state makes per-pipeline instance configuration difficult in multi-tenant or concurrent contexts.

## Spike Evidence
Verified in [`tests/spikes/test_structlog_spike.py`](file:///C:/Users/SHRIT-12/projects/smartmech-video-pipeline/tests/spikes/test_structlog_spike.py):
- JSON rendering with timestamp, log level, event, and contextual kwargs.

## Fallback Strategy
Standard library `logging` with `json.dumps` formatter.
