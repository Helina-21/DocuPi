import hashlib
import os
from typing import List

try:  # pragma: no cover - optional dependency
    import openai
except ImportError:  # pragma: no cover
    openai = None


def deterministic_vector(text: str, dim: int = 1536) -> List[float]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    nums = [b for b in h]
    vec = (nums * (dim // len(nums) + 1))[:dim]
    return [v / 255.0 for v in vec]


class EmbeddingProvider:
    def __init__(self, dry_run: bool = False):
        self.model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.dry_run = dry_run
        self.name = "deterministic-local" if dry_run or not os.getenv("OPENAI_API_KEY") else "openai"

    def embed(self, texts: List[str]) -> List[List[float]]:
        if openai and os.getenv("OPENAI_API_KEY") and not self.dry_run:
            client = openai.OpenAI()
            response = client.embeddings.create(model=self.model, input=texts)
            return [item.embedding for item in response.data]
        return [deterministic_vector(text) for text in texts]
