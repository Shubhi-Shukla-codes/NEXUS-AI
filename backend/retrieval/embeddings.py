"""
NEXUS Local Embedding Engine
Provides replaceable embedding provider interfaces, lazy model loading,
batch vector generation, and L2 vector normalization.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np
from backend.config import settings


class BaseEmbeddingProvider(ABC):
    """Abstract interface for replaceable local and offline embedding providers."""

    @abstractmethod
    def embed_texts(self, texts: List[str], batch_size: int = 16) -> List[List[float]]:
        """Generate normalized dense embeddings for a list of text passages."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Generate normalized dense embedding for a single search query."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimensionality."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the active model identifier."""
        pass


class SentenceTransformersProvider(BaseEmbeddingProvider):
    """
    Local lightweight Sentence Transformers embedding engine.
    Utilizes all-MiniLM-L6-v2 (384 dimensions) with lazy loading on CPU.
    """

    def __init__(self, model_name: Optional[str] = None, device: str = "cpu"):
        self._model_name = model_name or settings.models.embedding_model_name
        self._device = device
        self._dimension = settings.models.embedding_dimension
        self._model = None  # Lazy loaded

    def _load_model(self):
        """Lazy load SentenceTransformers model on first invocation to preserve memory."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name, device=self._device)

    def embed_texts(self, texts: List[str], batch_size: int = 16) -> List[List[float]]:
        """Generate normalized vector embeddings in memory-efficient batches."""
        if not texts:
            return []

        self._load_model()
        # Clean empty texts
        safe_texts = [t.strip() if t.strip() else "empty document chunk" for t in texts]

        embeddings = self._model.encode(
            safe_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """Generate normalized vector embedding for query."""
        clean_q = query.strip() if query.strip() else "query"
        self._load_model()
        embedding = self._model.encode(
            clean_q,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        return embedding.tolist()

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic pseudo-embedding provider for testing, air-gap fallback,
    and fast continuous integration without model weights.
    """

    def __init__(self, dimension: int = 384, model_name: str = "mock-minilm-384"):
        self._dimension = dimension
        self._model_name = model_name

    def _hash_to_vector(self, text: str) -> List[float]:
        """Generate deterministic normalized unit vector from string."""
        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Seed random generator with hash
        seed = int.from_bytes(h[:4], "big")
        rng = np.random.default_rng(seed)
        vec = rng.normal(0, 1, self._dimension)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_texts(self, texts: List[str], batch_size: int = 16) -> List[List[float]]:
        return [self._hash_to_vector(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        return self._hash_to_vector(query)

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name


# Default singleton provider instance
_embedding_provider_instance: Optional[BaseEmbeddingProvider] = None


def get_embedding_provider(mock: bool = False) -> BaseEmbeddingProvider:
    """Retrieve global embedding provider singleton."""
    global _embedding_provider_instance
    if mock:
        return MockEmbeddingProvider()
    if _embedding_provider_instance is None:
        _embedding_provider_instance = SentenceTransformersProvider()
    return _embedding_provider_instance
