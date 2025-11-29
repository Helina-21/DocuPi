import hashlib
import json
import os
import platform
import socket
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .logging_utils import get_logger

logger = get_logger(__name__)


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def ensure_run_dir(base: Path = Path("runs"), run_id: Optional[str] = None) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    rid = run_id or datetime.utcnow().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8]
    run_dir = base / rid
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_dir / "errors").mkdir(parents=True, exist_ok=True)
    return run_dir


def write_run_metadata(
    run_dir: Path,
    pipeline_path: Path,
    pipeline_content: str,
    git_sha: str,
    cli_args: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    run_id = run_dir.name
    metadata = {
        "run_id": run_id,
        "start_time": datetime.utcnow().isoformat() + "Z",
        "pipeline_path": str(pipeline_path),
        "pipeline_hash": compute_hash(pipeline_content),
        "git_sha": git_sha,
        "cli_args": cli_args or {},
        "host": socket.gethostname(),
        "python_version": platform.python_version(),
    }
    (run_dir / "run.json").write_text(json.dumps(metadata, indent=2))
    return metadata


def finalize_run_metadata(run_dir: Path):
    run_path = run_dir / "run.json"
    if not run_path.exists():
        return
    data = json.loads(run_path.read_text())
    data["end_time"] = datetime.utcnow().isoformat() + "Z"
    run_path.write_text(json.dumps(data, indent=2))


def write_metrics(run_dir: Path, metrics: Dict[str, Any]):
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))


def snapshot_config(run_dir: Path, pipeline_content: str):
    (run_dir / "artifacts" / "pipeline.yaml").write_text(pipeline_content)


def snapshot_operator_configs(run_dir: Path, steps: Dict[str, Dict[str, Any]]):
    (run_dir / "artifacts" / "operators.json").write_text(json.dumps(steps, indent=2))


def store_error(run_dir: Path, record_id: str, content: str):
    error_file = run_dir / "errors" / f"{record_id}.json"
    error_file.write_text(content)


def detect_git_sha() -> str:
    try:
        import subprocess

        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
        )
    except Exception:
        logger.warning("Unable to read git sha", exc_info=True)
        return "unknown"
