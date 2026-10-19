# ADR-0004: Adoption of Pydantic and Pydantic-Settings

- **Status**: Accepted
- **Date**: 2026-10-19
- **Author**: Jimrit

## Purpose
Domain entity validation, schema enforcement, immutable value objects, and secure configuration management with secret masking.

## License & Metadata
- **License**: MIT
- **Versions**: `pydantic==2.14.1`, `pydantic-settings==2.16.0`

## Alternatives Evaluated
1. **dataclasses / attrs**: Lacks declarative schema validation, regex validation, serialization, and secret redaction.
2. **marshmallow**: Verbose, separated schemas from domain objects, slower performance compared to Pydantic v2 Rust core.

## Spike Evidence
Verified in:
- [`tests/spikes/test_pydantic_spike.py`](file:///C:/Users/SHRIT-12/projects/smartmech-video-pipeline/tests/spikes/test_pydantic_spike.py): Proves field validation, regex constraints, and frozen immutability.
- [`tests/spikes/test_pydantic_settings_spike.py`](file:///C:/Users/SHRIT-12/projects/smartmech-video-pipeline/tests/spikes/test_pydantic_settings_spike.py): Proves `SecretStr` masking in representation and environment variable override capabilities.

## Fallback Strategy
Standard library `dataclasses` with custom `__post_init__` validation and manual environment parsing.
