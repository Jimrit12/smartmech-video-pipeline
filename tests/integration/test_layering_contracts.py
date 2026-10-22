"""Integration test proving all hexagonal layering contracts are green."""

from importlinter.cli import lint_imports


def test_layering_contracts_green() -> None:
    """Execute import-linter to verify all 7 hexagonal contracts are kept."""
    result = lint_imports()
    assert result == 0, "One or more import-linter hexagonal contracts failed"
