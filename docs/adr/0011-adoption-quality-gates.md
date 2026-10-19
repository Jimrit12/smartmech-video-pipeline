# ADR-0011: Adoption of Code Quality and Security Gates (Ruff, Mypy, Import-Linter, Pip-Audit, Gitleaks)

- **Status**: Accepted
- **Date**: 2026-10-19
- **Author**: Jimrit

## Purpose
Enforce rigorous static analysis, security auditing, and architectural integrity:
- **`ruff`**: High-performance linting and code formatting (`ruff==0.17.1`).
- **`mypy`**: Strict static type checking (`mypy==2.4.0`).
- **`import-linter`**: Mechanical enforcement of hexagonal layers contract (`import-linter==2.15`).
- **`pip-audit`**: Vulnerability auditing for all declared packages (`pip-audit==2.10.1`).
- **`gitleaks`**: Detection of committed credentials and API keys (`v8.30.1`).

## License & Metadata
All adopted tools use permissive open-source licenses (MIT / Apache-2.0 / BSD-2-Clause).

## Fallback Strategy
Standard black, flake8, bandit, and git-secrets.
