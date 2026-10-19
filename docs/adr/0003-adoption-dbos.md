# ADR-0003: Adoption of DBOS for Durable Execution

- **Status**: Accepted
- **Date**: 2026-10-19
- **Author**: Jimrit

## Purpose
Provide durable execution and workflow orchestration over local SQLite database. Workflow ID equals pipeline Run ID. Each pipeline stage is recorded as a DBOS step; workflow resumption skips completed steps without duplicate computation.

## License & Metadata
- **License**: Apache-2.0
- **Version**: 3.3.0 (PyPI release 2026-10-18)

## Alternatives Evaluated
1. **Temporal / Cadence**: Heavyweight, requires external daemon clusters, unsuitable for lightweight CLI/local development.
2. **Prefect / Airflow**: Excessive overhead and dependencies; heavyweight server/worker architecture.
3. **Custom SQLite State Machine**: High maintenance burden, prone to race conditions and manual transaction handling.

## Spike Evidence
Verified in [`tests/spikes/test_dbos_spike.py`](file:///C:/Users/SHRIT-12/projects/smartmech-video-pipeline/tests/spikes/test_dbos_spike.py):
- DBOS initialized with local SQLite system database (`sqlite:///<path>`).
- Telemetry disabled (`telemetry: {'disable_otlp': True}`).
- Durable step execution and idempotency: re-running with the same `SetWorkflowID` retrieves saved results without re-executing steps.

## Fallback Strategy
If DBOS becomes unavailable or incompatible, our port abstraction (`WorkflowEngine` port) allows seamless replacement with a lightweight SQLite transaction log.
