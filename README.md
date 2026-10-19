# Smartmech Video Pipeline

Autonomous, production-grade Python pipeline producing 30–40 s vertical (1080x1920) hyper-realistic construction-timelapse YouTube Shorts.

## Pipeline Lifecycle
```
Plan -> Keyframes -> Clips -> Voiceover -> Captions -> Composite -> QC -> Approval -> Publish
```

## Architecture
Strict hexagonal (ports and adapters) layered architecture enforced by import-linter:
- **`domain`**: Pure entities, value objects, schemas, invariants (stdlib + Pydantic only).
- **`ports`**: Adapter interfaces (Protocols) depending strictly on domain.
- **`application`**: Workflows, policies, use cases depending on domain + ports.
- **`adapters`**: Vendor and technology integrations depending on domain + ports only (adapters never import each other).
- **`interface`**: Typer CLI layer depending on application + compose only.
- **`compose`**: Composition root; the exclusive module allowed to import adapters and wire them into application ports.

## Requirements
- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- FFmpeg 9+ with libass and libx264 enabled

## Quick Start
```bash
# Set up environment
uv sync

# Run pipeline dry run
uv run smartmech run --dry-run
```

## Local Quality Gates
```bash
# Code formatting and linting
uv run ruff format --check
uv run ruff check

# Static type checking
uv run mypy --strict

# Test suite and branch coverage
uv run pytest --cov=smartmech.domain --cov=smartmech.application --cov-report=term-missing

# Architecture layering checks
uv run lint-imports

# Dependency vulnerability check
uv run pip-audit

# Secret leakage scan
gitleaks detect --no-git -v
```

## License
MIT (c) 2026 Jimrit
