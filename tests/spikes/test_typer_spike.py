"""Spike test proving Typer CLI behavior and argument parsing."""

from typer.testing import CliRunner

from smartmech.interface.cli import app

runner = CliRunner()


def test_typer_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "smartmech 0.1.0" in result.stdout


def test_typer_dry_run_flag() -> None:
    result = runner.invoke(app, ["run", "--dry-run", "--run-id", "test-run-123"])
    assert result.exit_code == 0
    assert "dry_run=True" in result.stdout
    assert "test-run-123" in result.stdout
