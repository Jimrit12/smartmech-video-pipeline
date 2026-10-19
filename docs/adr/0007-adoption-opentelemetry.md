# ADR-0007: Adoption of OpenTelemetry SDK for Distributed Tracing

- **Status**: Accepted
- **Date**: 2026-10-19
- **Author**: Jimrit

## Purpose
Instrument execution stages with standard OpenTelemetry spans and attributes for timing, performance profiling, and step traceability.

## License & Metadata
- **License**: Apache-2.0
- **Version**: `opentelemetry-sdk==1.45.1`, `opentelemetry-api==1.45.1`

## Alternatives Evaluated
1. **Manual Timers**: Fragile, ad-hoc attribute storage, lacks standard exporter interfaces.
2. **Datadog / New Relic proprietary SDKs**: Vendor lock-in; violates open-standard requirements.

## Spike Evidence
Verified in [`tests/spikes/test_opentelemetry_spike.py`](file:///C:/Users/SHRIT-12/projects/smartmech-video-pipeline/tests/spikes/test_opentelemetry_spike.py):
- `TracerProvider`, `SimpleSpanProcessor`, and `InMemorySpanExporter` verifying span creation and custom attribute attachment.

## Fallback Strategy
Lightweight custom span context manager recording start/stop timestamps.
