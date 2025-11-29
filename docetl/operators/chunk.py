import hashlib
from typing import Dict, Iterable, List

from .base import Operator


def split_text(text: str, size: int = 800, overlap: int = 100) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(text[start:end])
        start = end - overlap if end - overlap > start else end
    return chunks


def chunk_id(doc_id: str, doc_fingerprint: str, config_hash: str, idx: int) -> str:
    """Deterministic chunk id that changes when content changes."""
    payload = f"{doc_id}:{doc_fingerprint}:{config_hash}:{idx}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ChunkOperator(Operator):
    def process(self, records: Iterable[Dict]):
        size = int(self.config.get("size", 800))
        overlap = int(self.config.get("overlap", 100))
        config_hash = hashlib.sha256(str({"size": size, "overlap": overlap}).encode("utf-8")).hexdigest()
        for record in records:
            text = record.get("text", "")
            fp = record.get("doc_fingerprint", "")
            for idx, chunk in enumerate(split_text(text, size=size, overlap=overlap)):
                new_rec = dict(record)
                new_rec["chunk_id"] = chunk_id(record.get("doc_id", ""), fp, config_hash, idx)
                new_rec["chunk"] = chunk
                yield new_rec
