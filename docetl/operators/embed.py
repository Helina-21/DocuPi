from pathlib import Path
from typing import Dict, Iterable, List

from ..providers.embeddings import EmbeddingProvider
from ..vector_store import FaissStore
from .base import Operator


class EmbedOperator(Operator):
    def __init__(self, name: str, config: Dict):
        super().__init__(name, config)
        self.provider = EmbeddingProvider(dry_run=self.config.get("dry_run", False))
        run_dir = Path(self.config.get("run_dir", "."))
        default_index = run_dir / "artifacts" / "index.faiss"
        self.index_path = Path(self.config.get("index_path", default_index))
        if self.index_path.exists():
            self.store = FaissStore.load(self.index_path)
        else:
            self.store = FaissStore(dim=int(self.config.get("dim", 1536)))

    def process(self, records: Iterable[Dict]):
        recs: List[Dict] = list(records)
        chunks: List[str] = []
        metas: List[Dict] = []
        for record in recs:
            chunk_text = record.get("chunk") or record.get("text")
            if not chunk_text:
                continue
            chunks.append(chunk_text)
            metas.append(
                {
                    "doc_id": record.get("doc_id"),
                    "chunk_id": record.get("chunk_id"),
                    "source_uri": record.get("source_uri"),
                    "provider": self.provider.name,
                }
            )
        if chunks:
            vectors = self.provider.embed(chunks)
            self.store.add(vectors, metas)
            self.store.persist(self.index_path)
        for record in recs:
            record["embedded"] = True
            record["index_path"] = str(self.index_path)
            yield record
