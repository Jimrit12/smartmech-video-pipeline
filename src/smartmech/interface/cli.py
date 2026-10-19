"""Command-line interface for smartmech."""

import typer

app = typer.Typer(
    name="smartmech",
    help="Autonomous construction-timelapse YouTube Shorts pipeline",
    no_args_is_help=True,
)


@app.command()
def run(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Run pipeline end-to-end with local mock media generation",
    ),
    run_id: str | None = typer.Option(
        None,
        "--run-id",
        help="Custom run ID for resuming or identifying execution",
    ),
) -> None:
    """Execute the pipeline from plan to final video."""
    typer.echo(f"Starting pipeline run (dry_run={dry_run}, run_id={run_id})")


@app.command()
def version() -> None:
    """Show version."""
    typer.echo("smartmech 0.1.0")


if __name__ == "__main__":
    app()
