"""OpenTelemetry metrics and telemetry instrumentation."""

from opentelemetry import trace

tracer = trace.get_tracer("patchproof", "1.1.0")


def record_stage_span(stage_name: str, duration_ms: float, attributes: dict | None = None) -> None:
    """Record an OpenTelemetry span representing a pipeline stage."""
    with tracer.start_as_current_span(stage_name) as span:
        span.set_attribute("duration_ms", duration_ms)
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, v)
