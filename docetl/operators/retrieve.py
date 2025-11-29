from pathlib import Path
from typing import Dict, Iterable, List

from ..providers.embeddings import EmbeddingProvider
from ..vector_store import FaissStore
from .base import Operator


class RetrieveOperator(Operator):
    def __init__(self, name: str, config: Dict):
        super().__init__(name, config)
        run_dir = Path(self.config.get("run_dir", "."))
        default_index = run_dir / "artifacts" / "index.faiss"
        self.index_path = Path(self.config.get("index_path", default_index))
        self.top_k = int(self.config.get("top_k", 3))
        self.provider = EmbeddingProvider(dry_run=self.config.get("dry_run", False))
        self.store = FaissStore.load(self.index_path) if self.index_path.exists() else None

    def process(self, records: Iterable[Dict]):
        recs: List[Dict] = list(records)
        if not recs:
            return
        if not self.store:
            for rec in recs:
                rec["retrieved"] = []
                yield rec
            return

        queries: List[str] = []
        for rec in recs:
            queries.append((rec.get("chunk") or rec.get("text") or "").strip())
        vectors = self.provider.embed(queries)
        for rec, vec in zip(recs, vectors):
            results = self.store.search(vec, top_k=self.top_k)
            rec["retrieved"] = [
                {
                    "chunk_id": meta.get("chunk_id"),
                    "doc_id": meta.get("doc_id"),
                    "score": score,
                    "source_uri": meta.get("source_uri"),
                }
                for idx, score, meta in results
            ]
            yield rec
