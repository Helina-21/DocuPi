import hashlib
from pathlib import Path
from typing import Dict, Iterable

from .base import Operator

ALLOWED_EXTS = {".txt", ".md"}


def content_hash(path: Path) -> str:
    """Stable hash based only on bytes to remain portable."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LocalFolderIngest(Operator):
    def process(self, records: Iterable[Dict]):
        folder = Path(self.config.get("path") or self.config.get("watch_dir") or ".")
        folder = folder.resolve()
        for path in folder.glob("**/*"):
            if path.is_dir():
                continue
            if path.suffix.lower() not in ALLOWED_EXTS:
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            try:
                rel = path.resolve().relative_to(folder).as_posix()
            except Exception:
                rel = path.name
            yield {
                "doc_id": rel,
                "doc_fingerprint": content_hash(path),
                "source_uri": str(path.resolve()),
                "text": content,
            }
