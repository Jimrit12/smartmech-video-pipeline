# ADR-0005: Adoption of Typer for Command-Line Interface

- **Status**: Accepted
- **Date**: 2026-10-19
- **Author**: Jimrit

## Purpose
Build a robust, type-annotated CLI for running the pipeline, executing dry runs, managing autonomy gates, and inspecting reports.

## License & Metadata
- **License**: MIT
- **Version**: `typer==0.27.3`

## Alternatives Evaluated
1. **argparse**: Standard library, but verbose, lacks modern type-hint parsing, requires boilerplate for nested subcommands.
2. **click**: Typer is built on Click, providing identical robustness while offering clean Python type annotations.

## Spike Evidence
Verified in [`tests/spikes/test_typer_spike.py`](file:///C:/Users/SHRIT-12/projects/smartmech-video-pipeline/tests/spikes/test_typer_spike.py):
- Proves CLI argument parsing, option flags (`--dry-run`, `--run-id`), and test invocation with `CliRunner`.

## Fallback Strategy
`argparse` standard library module.
