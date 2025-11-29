import json
from pathlib import Path

from docetl.dsl_runner import DSLRunner
from docetl.logging_utils import get_logger
from docetl.operators.chunk import chunk_id
from docetl.operators.validate import ValidateOperator


def create_pipeline(tmp_path: Path, docs_dir: Path) -> Path:
    pipeline = {
        "name": "test",
        "steps": [
            {"name": "ingest", "type": "local_folder", "config": {"path": str(docs_dir)}},
            {"name": "sink", "type": "jsonl_sink", "config": {"path": str(tmp_path / "out.jsonl")}},
        ],
    }
    pipeline_path = tmp_path / "pipe.yaml"
    pipeline_path.write_text(json.dumps(pipeline))
    return pipeline_path


def test_fingerprint_checkpoint_resume(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    doc_path = docs_dir / "doc.txt"
    doc_path.write_text("hello world")

    monkeypatch.chdir(tmp_path)
    pipeline_path = create_pipeline(tmp_path, docs_dir)
    checkpoint = tmp_path / "state.json"

    runner1 = DSLRunner.from_yaml(pipeline_path, checkpoint=checkpoint)
    run1 = runner1.load_run_save()
    checkpoint_data = json.loads(checkpoint.read_text())
    processed = checkpoint_data.get("processed", {})
    assert len(processed) == 1
    assert (Path(run1) / "metrics.json").exists()

    runner2 = DSLRunner.from_yaml(pipeline_path, checkpoint=checkpoint)
    run2 = runner2.load_run_save()
    metrics2 = json.loads((Path(run2) / "metrics.json").read_text())
    assert metrics2.get("num_docs_processed") == 0


def test_chunk_id_deterministic():
    first = chunk_id("doc", "fp", "cfg", 0)
    second = chunk_id("doc", "fp", "cfg", 0)
    assert first == second


def test_redaction():
    logger = get_logger("redaction-test", debug_content=False)
    record = logger.makeRecord(
        name="redaction-test",
        level=20,
        fn="x",
        lno=1,
        msg="contact me at person@example.com",
        args=(),
        exc_info=None,
    )
    out = logger.handlers[0].format(record)
    assert "[REDACTED]" in out


def test_lineage_written(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs2"
    docs_dir.mkdir()
    (docs_dir / "doc.txt").write_text("hello")
    monkeypatch.chdir(tmp_path)
    pipeline_path = create_pipeline(tmp_path, docs_dir)
    runner = DSLRunner.from_yaml(pipeline_path)
    run_dir = runner.load_run_save()
    lineage_path = Path(run_dir) / "lineage.jsonl"
    assert lineage_path.exists()
    lines = lineage_path.read_text().splitlines()
    assert lines
    rec = json.loads(lines[0])
    assert rec["run_id"] == Path(run_dir).name
    assert rec["operator_name"]


def test_validate_operator_creates_review_queue(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs3"
    docs_dir.mkdir()
    (docs_dir / "doc.txt").write_text("hello")
    monkeypatch.chdir(tmp_path)
    pipeline = {
        "name": "review",
        "steps": [
            {"name": "ingest", "type": "local_folder", "config": {"path": str(docs_dir)}},
            {
                "name": "validate",
                "type": "validate",
                "config": {"required_fields": ["extracted"], "min_confidence": 0.8, "confidence_field": "score"},
            },
            {"name": "sink", "type": "jsonl_sink", "config": {"path": str(tmp_path / "out.jsonl")}},
        ],
    }
    pipeline_path = tmp_path / "pipe_review.yaml"
    pipeline_path.write_text(json.dumps(pipeline))
    runner = DSLRunner.from_yaml(pipeline_path)
    run_dir = runner.load_run_save()
    queue_path = Path(run_dir) / "needs_review.jsonl"
    assert queue_path.exists()
    lines = queue_path.read_text().splitlines()
    assert lines
    record = json.loads(lines[0])
    assert record.get("needs_review") is True
