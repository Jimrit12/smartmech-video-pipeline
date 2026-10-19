"""Command-line interface for smartmech."""

import asyncio
from datetime import UTC, datetime

import typer

from smartmech.compose.factory import build_pipeline

app = typer.Typer(
    name="smartmech",
    help="Autonomous construction-timelapse YouTube Shorts pipeline",
    no_args_is_help=True,
)


@app.command()
def run(
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="Run pipeline with local mock media generation (default: True in M0-M2)",
    ),
    run_id: str | None = typer.Option(
        None,
        "--run-id",
        help="Custom run ID for resuming or identifying execution",
    ),
    prompt: str = typer.Option(
        "Constructing a futuristic 50-story modular skyscraper",
        "--prompt",
        "-p",
        help="Architectural construction prompt",
    ),
    seed: int = typer.Option(
        42,
        "--seed",
        "-s",
        help="Deterministic pseudo-random seed",
    ),
    output_dir: str = typer.Option(
        "output",
        "--output-dir",
        "-o",
        help="Base directory for artifacts and reports",
    ),
) -> None:
    """Execute the pipeline from plan to final video."""
    effective_run_id = run_id or f"run_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    typer.echo(
        f"Starting smartmech pipeline (run_id={effective_run_id}, dry_run={dry_run}, seed={seed})"
    )

    runner = build_pipeline(output_dir=output_dir)

    try:
        report = asyncio.run(runner.execute_run(run_id=effective_run_id, prompt=prompt, seed=seed))
    except Exception as exc:
        typer.secho(f"Pipeline execution failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    status = report.get("status", "FAIL")
    video_path = report.get("video_path", "")
    spend = report.get("total_spend", 0.0)

    typer.echo("--------------------------------------------------")
    typer.echo(f"Run ID:         {effective_run_id}")
    typer.echo(f"QC Status:      {status}")
    typer.echo(f"Rendered Video: {video_path}")
    typer.echo(f"Total Spend:    {spend:.2f} cost units")
    typer.echo("--------------------------------------------------")

    if status != "PASS":
        typer.secho(f"QC Gate status {status} did not pass.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    typer.secho("Pipeline run completed successfully with QC PASS!", fg=typer.colors.GREEN)


@app.command()
def version() -> None:
    """Show version."""
    typer.echo("smartmech 0.1.0")


if __name__ == "__main__":
    app()
