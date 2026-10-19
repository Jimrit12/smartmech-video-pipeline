# Operational Runbook: smartmech-video-pipeline

## 1. Environment Setup

### Prerequisites
- Python 3.11 installed via `uv`
- `uv` package manager (`uv --version`)
- `git` and `gh` CLI authenticated
- `ffmpeg` and `ffprobe` (version 9+) with `libass` and `libx264`

### Installation
```bash
# Clone and enter directory
cd ~/projects/smartmech-video-pipeline

# Sync dependencies
uv sync

# Install editable with dev dependencies
uv pip install -e ".[dev]"
```

## 2. Quality Gates Checklist

Run all local gates prior to pushing:
```bash
# 1. Formatting
uv run ruff format --check .

# 2. Linting
uv run ruff check .

# 3. Static Type Analysis
uv run mypy --strict

# 4. Tests and Branch Coverage
uv run pytest --cov=smartmech.domain --cov=smartmech.application --cov-report=term-missing

# 5. Architecture Layer Enforcement
uv run lint-imports

# 6. Vulnerability Audit
uv run pip-audit

# 7. Secret Leakage Scan
gitleaks detect --no-git -v
```

## 3. Execution

### Dry Run (Local Mock Media)
```bash
uv run smartmech run --dry-run
```
Outputs:
- Generated video: `artifacts/<run_id>/final.mp4`
- Run Report: `artifacts/<run_id>/report.json` and `artifacts/<run_id>/report.md`

## 4. Failure Modes & Troubleshooting

### Import-Linter Failures
- `smartmech.domain` cannot import anything from other smartmech modules.
- `smartmech.ports` may only import `smartmech.domain`.
- `smartmech.application` may only import `smartmech.domain` and `smartmech.ports`.
- `smartmech.adapters` may only import `smartmech.domain` and `smartmech.ports`.
- Only `smartmech.compose` may import `smartmech.adapters`.

### FFmpeg Failures
- Verify `ffmpeg -hide_banner -filters` contains `subtitles` and `ass`.
- Verify `ffmpeg -hide_banner -encoders` contains `libx264`.

### DBOS Recovery
- SQLite database is stored at configured path (`smartmech_dbos.sqlite`).
- Re-running with the same `--run-id` resumes previously committed steps without re-execution.
