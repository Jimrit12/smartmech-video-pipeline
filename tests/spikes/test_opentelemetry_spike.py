"""Spike test proving OpenTelemetry tracer and span generation."""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def test_opentelemetry_span_creation() -> None:
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    tracer = trace.get_tracer("smartmech.spike")
    with tracer.start_as_current_span("stage_keyframes") as span:
        span.set_attribute("keyframe_count", 6)
        span.set_attribute("stage", "keyframes")

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "stage_keyframes"
    assert spans[0].attributes["keyframe_count"] == 6  # type: ignore[index]
