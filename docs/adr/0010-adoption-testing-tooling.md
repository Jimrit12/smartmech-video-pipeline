# ADR-0010: Adoption of Advanced Testing Tooling (Hypothesis, Syrupy, Pytest-Recording)

- **Status**: Accepted
- **Date**: 2026-10-19
- **Author**: Jimrit

## Purpose
Comprehensive automated testing:
- **`hypothesis`**: Property-based testing for timing, clip trims, audio duration sum invariants.
- **`syrupy`**: Snapshot testing for complex ffmpeg filtergraph command-line invocations.
- **`pytest-recording` (VCR.py)**: Deterministic, scrubbed network recording for external vendor HTTP calls.

## License & Metadata
- **Hypothesis**: MPL-2.0 (`hypothesis==6.170.2`)
- **Syrupy**: MIT (`syrupy==6.1.1`)
- **Pytest-recording**: MIT (`pytest-recording==0.14.0`)

## Spike Evidence
Verified in:
- [`tests/spikes/test_hypothesis_spike.py`](file:///C:/Users/SHRIT-12/projects/smartmech-video-pipeline/tests/spikes/test_hypothesis_spike.py): Property invariants on tail trim.
- [`tests/spikes/test_syrupy_spike.py`](file:///C:/Users/SHRIT-12/projects/smartmech-video-pipeline/tests/spikes/test_syrupy_spike.py): Snapshot matching for CLI commands.

## Fallback Strategy
Standard unit assertions and manual golden file comparisons.
