import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

try:  # pragma: no cover
    import faiss  # type: ignore
    import numpy as np
except ImportError:  # pragma: no cover
    faiss = None
    np = None


class FaissStore:
    def __init__(self, dim: int = 1536, store_dir: Path = Path("runs")):
        self.dim = dim
        self.store_dir = store_dir
        self.meta: List[Dict] = []
        if faiss and np:
            self.index = faiss.IndexFlatL2(dim)
        else:
            self.index = None
            self.vectors: List[List[float]] = []

    def add(self, vectors: List[List[float]], metadatas: List[Dict]):
        if self.index is not None:
            self.index.add(np.array(vectors).astype("float32"))
        else:
            self.vectors.extend(vectors)
        self.meta.extend(metadatas)

    def search(self, vector: List[float], top_k: int = 3) -> List[Tuple[int, float, Dict]]:
        results: List[Tuple[int, float, Dict]] = []
        if self.index is not None:
            q = np.array([vector]).astype("float32")
            scores, idxs = self.index.search(q, top_k)
            for score, idx in zip(scores[0], idxs[0]):
                if idx == -1:
                    continue
                results.append((int(idx), float(score), self.meta[idx]))
            return results
        # fallback similarity
        for idx, vec in enumerate(self.vectors):
            dist = _l2(vec, vector)
            results.append((idx, dist, self.meta[idx]))
        results.sort(key=lambda x: x[1])
        return results[:top_k]

    def persist(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, str(path))
        else:
            (path.with_suffix(".json")).write_text(json.dumps(self.vectors))
        meta_path = path.with_suffix(".meta.json")
        meta_path.write_text(json.dumps(self.meta, indent=2))

    @classmethod
    def load(cls, path: Path):
        meta_path = path.with_suffix(".meta.json")
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else []
        if faiss and path.exists():
            index = faiss.read_index(str(path))
            store = cls(dim=index.d)
            store.index = index
            store.meta = meta
            return store
        # fallback load
        vectors_path = path.with_suffix(".json")
        vectors = json.loads(vectors_path.read_text()) if vectors_path.exists() else []
        store = cls(dim=len(vectors[0]) if vectors else 0)
        store.vectors = vectors
        store.meta = meta
        return store


def _l2(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
