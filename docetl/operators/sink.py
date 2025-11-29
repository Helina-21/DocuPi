import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterable

from .base import Operator


class JsonlSink(Operator):
    def process(self, records: Iterable[Dict]):
        run_dir = Path(self.config.get("run_dir", "."))
        output_path = Path(self.config.get("path", run_dir / "output.jsonl"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
                yield record


class SQLiteSink(Operator):
    def process(self, records: Iterable[Dict]):
        db_path = Path(self.config.get("path", "runs/output.db"))
        table = self.config.get("table", "records")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id TEXT, payload TEXT)"
        )
        for record in records:
            conn.execute(
                f"INSERT INTO {table} (doc_id, payload) VALUES (?, ?)",
                (record.get("doc_id"), json.dumps(record)),
            )
            yield record
        conn.commit()
        conn.close()
