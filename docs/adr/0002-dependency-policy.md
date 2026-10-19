# ADR-0002: Dependency Management and Evaluation Policy

- **Status**: Accepted
- **Date**: 2026-10-19
- **Author**: Jimrit

## Context
Third-party dependencies introduce security vulnerabilities, license incompatibilities (such as copyleft viral GPL), and API volatility. A rigorous policy is required before introducing any external dependency.

## Decision
1. **Spike-First Rule**: Before adopting any dependency, we must write a spike test in `tests/spikes/` proving the exact required behavior under Python 3.11, and record an Architecture Decision Record (ADR) detailing:
   - Purpose
   - License (Permissive only: MIT, Apache-2.0, BSD, or MPL-2.0)
   - Last release date
   - Alternatives evaluated
   - Spike evidence (`tests/spikes/...`)
   - Fallback strategy if abandoned or deprecated
2. **Banned Dependencies**:
   - `ffmpeg-python`, `moviepy`, `comfy-cli`, `Remotion`, `Piper`
   - Any GPL-licensed code linked into the application process
   - Note: `edge-tts` (LGPL, unofficial endpoint) is banned from core and only considered as an optional isolated adapter in later milestones.
3. **Pinning**: All dependencies are locked exactly in `uv.lock`.
4. **Audit Gates**: `pip-audit` runs in CI to verify zero known vulnerabilities.

## Consequences
- No accidental licensing contamination.
- Fast, predictable CI builds.
- Clear documented rationale and test evidence for every adopted library.
