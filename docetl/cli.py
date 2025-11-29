import json
from pathlib import Path

import typer

from . import __version__
from .artifacts import detect_git_sha, ensure_run_dir, finalize_run_metadata, snapshot_config, write_metrics, write_run_metadata
from .logging_utils import get_logger
from .runner import run_pipeline
from .review_app import launch_review
from .eval import run_eval

app = typer.Typer(help="DocETL CLI for document processing pipelines")
logger = get_logger(__name__)


@app.command()
def init_run(pipeline: Path = typer.Argument(..., exists=True, readable=True)):
    """Initialize run metadata and write artifacts snapshot."""
    run_dir = ensure_run_dir()
    content = pipeline.read_text()
    snapshot_config(run_dir, content)
    meta = write_run_metadata(run_dir, pipeline, content, detect_git_sha())
    metrics = {"records": 0, "errors": 0}
    write_metrics(run_dir, metrics)
    finalize_run_metadata(run_dir)
    typer.echo(json.dumps({"run_dir": str(run_dir), "metadata": meta}, indent=2))


@app.command()
def run(
    pipeline: Path = typer.Argument(..., exists=True, readable=True),
    stream: bool = typer.Option(False, help="Enable streaming mode"),
    watch: Path = typer.Option(Path("."), help="Folder to watch for streaming"),
    checkpoint: Path = typer.Option(None, help="Checkpoint file path"),
    debug_content: bool = typer.Option(False, help="Include content in logs"),
    dry_run: bool = typer.Option(False, help="Disable external calls and use deterministic mocks"),
    max_loops: int = typer.Option(None, help="Max streaming loops (for tests)"),
):
    """Execute a pipeline once or in streaming mode."""
    run_dir = run_pipeline(
        pipeline,
        stream=stream,
        watch=watch,
        checkpoint=checkpoint,
        debug_content=debug_content,
        dry_run=dry_run,
        max_loops=max_loops,
    )
    typer.echo(f"Run stored in {run_dir}")


@app.command()
def review(run: Path = typer.Argument(..., exists=True, readable=True), port: int = typer.Option(8787, help="Port to serve review UI")):
    """Launch the review application for a run."""
    launch_review(run, port=port)


@app.command()
def eval(
    pipeline: Path = typer.Argument(..., exists=True, readable=True),
    dataset: Path = typer.Argument(..., exists=True, readable=True),
):
    """Run evaluation harness."""
    run_dir = run_eval(pipeline, dataset)
    typer.echo(f"Evaluation written to {run_dir / 'eval_report.md'}")


def main():
    app()


if __name__ == "__main__":
    main()
