import json
import os
import time
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import hashlib

from .artifacts import (
    detect_git_sha,
    ensure_run_dir,
    finalize_run_metadata,
    snapshot_config,
    snapshot_operator_configs,
    store_error,
    write_metrics,
    write_run_metadata,
)
from .config import OperatorConfig, PipelineConfig, load_pipeline
from .lineage import LineageRecord, lineage_writer
from .logging_utils import get_logger
from .operators.base import Operator, PassthroughOperator
from .operators.ingest import LocalFolderIngest
from .operators.chunk import ChunkOperator
from .operators.embed import EmbedOperator
from .operators.retrieve import RetrieveOperator
from .operators.sink import JsonlSink, SQLiteSink
from .operators.validate import ValidateOperator

logger = get_logger(__name__)


OPERATOR_REGISTRY = {
    "local_folder": LocalFolderIngest,
    "passthrough": PassthroughOperator,
    "chunk": ChunkOperator,
    "embed": EmbedOperator,
    "retrieve": RetrieveOperator,
    "jsonl_sink": JsonlSink,
    "sqlite_sink": SQLiteSink,
    "validate": ValidateOperator,
}


class DSLRunner:
    def __init__(
        self,
        pipeline_path: Path,
        pipeline: PipelineConfig,
        stream: bool = False,
        watch_dir: Path = Path("."),
        checkpoint: Path = None,
        debug_content: bool = False,
        dry_run: bool = False,
        max_loops: int = None,
    ):
        self.pipeline_path = pipeline_path
        self.pipeline = pipeline
        self.stream = stream
        self.watch_dir = watch_dir
        self.checkpoint_path = checkpoint
        self.debug_content = debug_content
        self.dry_run = dry_run
        self.max_loops = max_loops
        # doc_id -> fingerprint
        self.processed_docs: Dict[str, str] = {}
        self.poll_interval_sec = float(os.getenv("DOCETL_POLL_INTERVAL_SEC", "1.0"))
        self.metrics: Dict[str, any] = {
            "num_docs_seen": 0,
            "num_docs_processed": 0,
            "num_docs_skipped": 0,
            "num_errors": 0,
            "retries": 0,
            "latency_ms": [],
        }

    @classmethod
    def from_yaml(
        cls,
        path: Path,
        stream: bool = False,
        watch_dir: Path = Path("."),
        checkpoint: Path = None,
        debug_content: bool = False,
        dry_run: bool = False,
        max_loops: int = None,
    ) -> "DSLRunner":
        pipeline = load_pipeline(path)
        return cls(
            pipeline_path=path,
            pipeline=pipeline,
            stream=stream,
            watch_dir=watch_dir,
            checkpoint=checkpoint,
            debug_content=debug_content,
            dry_run=dry_run,
            max_loops=max_loops,
        )

    def _load_checkpoint(self):
        if not self.checkpoint_path or not self.checkpoint_path.exists():
            return
        try:
            data = json.loads(self.checkpoint_path.read_text())
            processed = data.get("processed", {})
            if isinstance(processed, list):
                self.processed_docs = {doc_id: "__unknown__" for doc_id in processed}
            else:
                self.processed_docs = dict(processed)
        except Exception:
            logger.warning("Failed to read checkpoint; starting fresh")

    def _write_checkpoint(self):
        if not self.checkpoint_path:
            return
        self.checkpoint_path.write_text(
            json.dumps({"processed": self.processed_docs}, indent=2, sort_keys=True)
        )

    def _create_operator(self, op_config: OperatorConfig, run_dir: Path) -> Operator:
        klass = OPERATOR_REGISTRY.get(op_config.type)
        if not klass:
            raise ValueError(f"Unknown operator type: {op_config.type}")
        cfg = dict(op_config.config)
        cfg.update({"run_dir": run_dir, "dry_run": self.dry_run, "watch_dir": self.watch_dir})
        return klass(op_config.name, cfg)

    def _execute_operator(self, op: Operator, records: Iterable[Dict]) -> List[Dict]:
        attempts = 0
        backoff = 0.5
        while True:
            try:
                output = list(op.process(records))
                return output
            except Exception as exc:  # pragma: no cover - fallback path
                attempts += 1
                self.metrics["retries"] += 1
                if attempts >= 3:
                    raise exc
                sleep_for = backoff * (2 ** (attempts - 1))
                time.sleep(sleep_for)

    def _record_lineage(
        self,
        lineage_cb,
        run_dir: Path,
        meta: Dict[str, any],
        op,
        duration_ms: float,
        records: List[Dict],
    ):
        for rec in records:
            lineage_cb(
                LineageRecord(
                    run_id=run_dir.name,
                    pipeline_hash=meta["pipeline_hash"],
                    git_sha=meta["git_sha"],
                    operator_name=op.name,
                    operator_config_hash=meta.get("operator_config_hash", {}).get(op.name, ""),
                    input_doc_id=str(rec.get("doc_id", "unknown")),
                    source_uri=str(rec.get("source_uri", "")),
                    chunk_id=rec.get("chunk_id"),
                    model=rec.get("model"),
                    provider=rec.get("provider"),
                    prompt_hash=rec.get("prompt_hash"),
                    output_schema_hash=rec.get("output_schema_hash"),
                    validation_result=str(rec.get("validation_result")) if rec.get("validation_result") else None,
                    latency_ms=duration_ms,
                )
            )

    def _execute_once(self, run_dir: Path, meta: Dict[str, any], lineage_cb):
        records: Iterable[Dict] = [{}]
        operators = [self._create_operator(step, run_dir) for step in self.pipeline.steps]
        for op in operators:
            start = time.time()
            try:
                next_records = self._execute_operator(op, records)
            except Exception as exc:
                self.metrics["num_errors"] += 1
                err_id = f"{op.name}-{int(time.time())}"
                store_error(run_dir, err_id, json.dumps({"error": str(exc)}))
                logger.error("Operator failed", extra={"extra_data": {"operator": op.name, "error": str(exc)}})
                continue
            duration_ms = (time.time() - start) * 1000
            self.metrics["latency_ms"].append(duration_ms)
            if op.__class__.__name__ == "LocalFolderIngest":
                filtered = []
                for rec in next_records:
                    self.metrics["num_docs_seen"] += 1
                    doc_id = rec.get("doc_id")
                    fp = rec.get("doc_fingerprint", "__unknown__")
                    if doc_id in self.processed_docs and self.processed_docs.get(doc_id) == fp:
                        self.metrics["num_docs_skipped"] += 1
                        continue
                    self.processed_docs[doc_id] = fp
                    filtered.append(rec)
                next_records = filtered
                self.metrics["num_docs_processed"] += len(next_records)
            self._record_lineage(lineage_cb, run_dir, meta, op, duration_ms, next_records)
            records = next_records
        return records

    def _dir_snapshot(self, root: Path) -> Tuple[Tuple[str, int, int], ...]:
        """Deterministic snapshot of directory contents (relpath, mtime, size)."""
        root = root.resolve()
        items: List[Tuple[str, int, int]] = []
        for p in root.glob("**/*"):
            if p.is_dir():
                continue
            try:
                st = p.stat()
                rel = p.resolve().relative_to(root).as_posix()
                items.append((rel, int(st.st_mtime_ns), int(st.st_size)))
            except Exception:
                continue
        return tuple(sorted(items))

    def load_run_save(self) -> Path:
        self._load_checkpoint()
        pipeline_content = self.pipeline_path.read_text()
        run_dir = ensure_run_dir()
        snapshot_config(run_dir, pipeline_content)
        snapshot_operator_configs(
            run_dir,
            {step.name: step.config for step in self.pipeline.steps},
        )
        git_sha = detect_git_sha()
        meta = write_run_metadata(
            run_dir,
            self.pipeline_path,
            pipeline_content,
            git_sha,
            {
                "stream": self.stream,
                "watch": str(self.watch_dir),
                "checkpoint": str(self.checkpoint_path) if self.checkpoint_path else None,
            },
        )
        # add operator config hashes for lineage
        meta["operator_config_hash"] = {
            step.name: detect_hash(step.config) for step in self.pipeline.steps
        }
        lineage_cb = lineage_writer(run_dir)

        loops = 0
        if self.stream:
            logger.info("Starting streaming run", extra={"extra_data": {"watch": str(self.watch_dir)}})
            last = self._dir_snapshot(self.watch_dir)
            while True:
                self._execute_once(run_dir, meta, lineage_cb)
                self._write_checkpoint()
                loops += 1
                if self.max_loops and loops >= self.max_loops:
                    break
                while True:
                    time.sleep(self.poll_interval_sec)
                    cur = self._dir_snapshot(self.watch_dir)
                    if cur != last:
                        last = cur
                        break
        else:
            self._execute_once(run_dir, meta, lineage_cb)
            self._write_checkpoint()

        self.metrics["latency_ms_p50"] = _percentile(self.metrics["latency_ms"], 50)
        self.metrics["latency_ms_p95"] = _percentile(self.metrics["latency_ms"], 95)
        write_metrics(run_dir, self.metrics)
        finalize_run_metadata(run_dir)
        logger.info("Run complete", extra={"extra_data": {"run_dir": str(run_dir)}})
        return run_dir


def detect_hash(obj: Dict[str, any]) -> str:
    payload = json.dumps(obj, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _percentile(values: List[float], pct: int) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * pct / 100
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return float(sorted_vals[int(k)])
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return float(d0 + d1)
