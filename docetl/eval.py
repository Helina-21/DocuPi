import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List

from .runner import run_pipeline
from .logging_utils import get_logger

logger = get_logger(__name__)


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_expected(dataset: Path) -> List[Dict]:
    expected_path = dataset / "expected.jsonl"
    if not expected_path.exists():
        return []
    return [json.loads(line) for line in expected_path.read_text().splitlines() if line.strip()]


def evaluate_run(run_dir: Path, expected: List[Dict]) -> Dict:
    output_path = run_dir / "output.jsonl"
    outputs = []
    if output_path.exists():
        outputs = [json.loads(line) for line in output_path.read_text().splitlines() if line.strip()]
    output_doc_ids = {rec.get("doc_id") for rec in outputs}
    expected_doc_ids = {rec.get("doc_id") for rec in expected}
    coverage = 0.0
    if expected_doc_ids:
        coverage = len(output_doc_ids & expected_doc_ids) / max(1, len(expected_doc_ids))
    cited = sum(1 for rec in outputs if rec.get("chunk_id") or rec.get("retrieved"))
    citation_rate = cited / max(1, len(outputs))
    return {
        "outputs": len(outputs),
        "expected": len(expected),
        "coverage": coverage,
        "citation_rate": citation_rate,
    }


def write_report(run_dir: Path, metrics: Dict):
    report = "# Evaluation Report\n"
    report += f"Outputs: {metrics['outputs']}\\n"
    report += f"Expected: {metrics['expected']}\\n"
    report += f"Coverage: {metrics['coverage']:.2f}\\n"
    report += f"Citation rate: {metrics['citation_rate']:.2f}\\n"
    (run_dir / "eval_report.md").write_text(report)
    (run_dir / "metrics_eval.json").write_text(json.dumps(metrics, indent=2))


def run_eval(pipeline: Path, dataset: Path):
    start = time.time()
    run_dir = run_pipeline(pipeline, dry_run=True)
    expected = load_expected(dataset)
    metrics = evaluate_run(run_dir, expected)
    metrics["runtime_sec"] = time.time() - start
    write_report(run_dir, metrics)
    logger.info("Evaluation complete", extra={"extra_data": metrics})
    return run_dir
