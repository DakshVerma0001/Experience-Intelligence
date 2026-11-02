"""
Local embedding generation + local vector storage. No external embedding API
is ever called. The embedding backend is intentionally pluggable (per spec):
sentence-transformers is the default, with a deterministic local hashing
fallback if sentence-transformers/torch are unavailable in the environment,
so the rest of the pipeline (search, duplicate detection) keeps working.
"""
from __future__ import annotations

import hashlib
import struct
from functools import lru_cache

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingBackend:
    dimensions: int
    model_name: str

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class SentenceTransformerBackend(EmbeddingBackend):
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self.dimensions = self._model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> list[float]:
        vector = self._model.encode(text, normalize_embeddings=True)
        return vector.tolist()


class HashingFallbackBackend(EmbeddingBackend):
    """Deterministic, fully local, dependency-free embedding used only if
    sentence-transformers is unavailable. Not semantically rich, but keeps
    hybrid/keyword search functional end-to-end."""

    def __init__(self, dimensions: int = 256):
        self.model_name = "local-hashing-fallback"
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        for token in text.lower().split():
            h = hashlib.sha256(token.encode("utf-8")).digest()
            idx = struct.unpack("I", h[:4])[0] % self.dimensions
            sign = 1.0 if h[4] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]


@lru_cache
def get_embedding_backend() -> EmbeddingBackend:
    settings = get_settings()
    try:
        return SentenceTransformerBackend(settings.embedding_model)
    except Exception as exc:
        logger.warning("sentence-transformers unavailable (%s); using local hashing fallback embedding.", exc)
        return HashingFallbackBackend()


def build_embedding_input(project: dict) -> str:
    """Combines the fields the spec calls out into one embedding input string."""
    parts = [
        project.get("project_name"),
        project.get("client_name"),
        project.get("project_description"),
        project.get("actual_services"),
        " ".join(project.get("keywords", [])),
        " ".join(project.get("keyword_descriptions", [])),
        project.get("ai_search_summary"),
        project.get("country"),
        project.get("state_ut"),
    ]
    return "\n".join(p for p in parts if p)


class VectorStore:
    """Wraps ChromaDB (persistent, local-only). Falls back to an in-memory
    cosine-similarity index if ChromaDB cannot be initialized, so search still
    works without an extra service running."""

    _COLLECTION = "project_embeddings"

    def __init__(self):
        settings = get_settings()
        self._memory_store: dict[str, tuple[list[float], dict]] = {}
        self._collection = None
        try:
            import chromadb

            client = chromadb.PersistentClient(path=settings.vector_store_dir)
            self._collection = client.get_or_create_collection(self._COLLECTION)
        except Exception as exc:
            logger.warning("ChromaDB unavailable (%s); using in-memory vector store fallback.", exc)

    def upsert(self, project_id: str, vector: list[float], metadata: dict, document_text: str) -> None:
        if self._collection is not None:
            self._collection.upsert(
                ids=[project_id], embeddings=[vector], metadatas=[metadata], documents=[document_text]
            )
        else:
            self._memory_store[project_id] = (vector, metadata)

    def delete(self, project_id: str) -> None:
        if self._collection is not None:
            try:
                self._collection.delete(ids=[project_id])
            except Exception:
                pass
        self._memory_store.pop(project_id, None)

    def query(self, vector: list[float], n_results: int = 20) -> list[tuple[str, float]]:
        """Returns list of (project_id, similarity_score) descending."""
        if self._collection is not None:
            res = self._collection.query(query_embeddings=[vector], n_results=n_results)
            ids = res.get("ids", [[]])[0]
            distances = res.get("distances", [[]])[0]
            return [(i, max(0.0, 1.0 - d)) for i, d in zip(ids, distances)]

        def cosine(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            na = sum(x * x for x in a) ** 0.5 or 1.0
            nb = sum(x * x for x in b) ** 0.5 or 1.0
            return dot / (na * nb)

        scored = [(pid, cosine(vector, v)) for pid, (v, _) in self._memory_store.items()]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:n_results]


@lru_cache
def get_vector_store() -> VectorStore:
    return VectorStore()
