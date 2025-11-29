import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class LineageRecord:
    run_id: str
    pipeline_hash: str
    git_sha: str
    operator_name: str
    operator_config_hash: str
    input_doc_id: str
    source_uri: str
    chunk_id: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    prompt_hash: Optional[str] = None
    output_schema_hash: Optional[str] = None
    validation_result: Optional[str] = None
    latency_ms: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_json(self) -> str:
        return json.dumps(asdict(self))


def lineage_writer(run_dir: Path):
    path = run_dir / "lineage.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)

    def write(record: LineageRecord):
        with path.open("a", encoding="utf-8") as f:
            f.write(record.to_json() + "\n")
        logger.debug("Lineage recorded", extra={"extra_data": {"operator": record.operator_name}})

    return write
