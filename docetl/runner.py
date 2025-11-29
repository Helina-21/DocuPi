from pathlib import Path

from .dsl_runner import DSLRunner


def run_pipeline(
    pipeline_path: Path,
    stream: bool = False,
    watch: Path = Path("."),
    checkpoint: Path = None,
    debug_content: bool = False,
    dry_run: bool = False,
    max_loops: int = None,
):
    runner = DSLRunner.from_yaml(
        pipeline_path,
        stream=stream,
        watch_dir=watch,
        checkpoint=checkpoint,
        debug_content=debug_content,
        dry_run=dry_run,
        max_loops=max_loops,
    )
    return runner.load_run_save()
