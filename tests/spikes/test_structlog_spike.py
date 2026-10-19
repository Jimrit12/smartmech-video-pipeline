"""Spike test proving structlog JSON formatting and context bindings."""

import json
from io import StringIO

import structlog


def test_structlog_json_output() -> None:
    stream = StringIO()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=stream),
    )

    logger = structlog.get_logger()
    logger.info("step_completed", step="plan", duration_ms=120)

    output = stream.getvalue().strip()
    data = json.loads(output)
    assert data["event"] == "step_completed"
    assert data["level"] == "info"
    assert data["step"] == "plan"
    assert data["duration_ms"] == 120
