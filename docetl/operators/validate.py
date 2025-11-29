import json
from pathlib import Path
from typing import Dict, Iterable, List

from .base import Operator


class ValidateOperator(Operator):
    """Flags records needing review and appends them to a queue file."""

    def __init__(self, name: str, config: Dict):
        super().__init__(name, config)
        self.required_fields: List[str] = self.config.get("required_fields", [])
        self.confidence_field = self.config.get("confidence_field")
        self.min_confidence = float(self.config.get("min_confidence", 0.0))
        self.queue_path = Path(self.config.get("run_dir", ".")) / "needs_review.jsonl"

    def _needs_review(self, record: Dict) -> List[str]:
        reasons: List[str] = []
        for field in self.required_fields:
            if record.get(field) in (None, ""):
                reasons.append(f"missing_field:{field}")
        if self.confidence_field:
            try:
                score = float(record.get(self.confidence_field, 0.0))
            except (TypeError, ValueError):
                score = 0.0
            if score < self.min_confidence:
                reasons.append("low_confidence")
        return reasons

    def _append_queue(self, record: Dict):
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        with self.queue_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def process(self, records: Iterable[Dict]):
        for record in records:
            rec = dict(record)
            reasons = self._needs_review(rec)
            rec["needs_review"] = bool(reasons)
            if reasons:
                rec["review_reasons"] = reasons
                self._append_queue(rec)
            yield rec
