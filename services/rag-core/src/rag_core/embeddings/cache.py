"""Caching wrapper for embedding models."""

import hashlib
import json
import logging
from collections import OrderedDict
from typing import Any

import numpy as np

from .base import EmbeddingModel

logger = logging.getLogger(__name__)


class LRUCache:
    """Simple in-memory LRU cache."""

    def __init__(self, maxsize: int = 10000) -> None:
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.maxsize = maxsize

    def get(self, key: str) -> Any | None:
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key: str, value: Any) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.maxsize:
                self.cache.popitem(last=False)
        self.cache[key] = value


class CachedEmbedder(EmbeddingModel):
    """Wraps any EmbeddingModel with an LRU cache."""

    def __init__(
        self,
        model: EmbeddingModel,
        maxsize: int = 10000,
        redis_url: str | None = None,
    ) -> None:
        self._model = model
        self._cache = LRUCache(maxsize=maxsize)
        self._redis_url = redis_url
        self._redis = None

        if redis_url:
            try:
                import redis  # type: ignore[import]
                self._redis = redis.from_url(redis_url, decode_responses=False)
                logger.info("Redis cache enabled for embeddings")
            except Exception as exc:
                logger.warning("Redis unavailable, using in-memory cache: %s", exc)

    def _cache_key(self, text: str) -> str:
        return hashlib.sha256(
            f"{self._model.model_name}:{text}".encode()
        ).hexdigest()

    def embed(self, texts: list[str]) -> np.ndarray:
        """Embed texts with caching.

        Checks cache for each text, only calls model for cache misses.

        Args:
            texts: List of texts to embed.

        Returns:
            numpy array of shape (n, embedding_dim).
        """
        if not texts:
            return np.empty((0, self._model.embedding_dim), dtype=np.float32)

        results: list[np.ndarray | None] = [None] * len(texts)
        miss_indices: list[int] = []
        miss_texts: list[str] = []

        for i, text in enumerate(texts):
            key = self._cache_key(text)
            cached = self._get_from_cache(key)
            if cached is not None:
                results[i] = cached
            else:
                miss_indices.append(i)
                miss_texts.append(text)

        if miss_texts:
            embeddings = self._model.embed(miss_texts)
            for j, idx in enumerate(miss_indices):
                embedding = embeddings[j]
                results[idx] = embedding
                key = self._cache_key(miss_texts[j])
                self._put_to_cache(key, embedding)

        return np.vstack([r for r in results if r is not None])

    def _get_from_cache(self, key: str) -> np.ndarray | None:
        if self._redis is not None:
            try:
                data = self._redis.get(f"emb:{key}")
                if data is not None:
                    return np.frombuffer(data, dtype=np.float32)
            except Exception:
                pass
        return self._cache.get(key)

    def _put_to_cache(self, key: str, embedding: np.ndarray) -> None:
        self._cache.put(key, embedding)
        if self._redis is not None:
            try:
                self._redis.setex(f"emb:{key}", 86400, embedding.tobytes())
            except Exception:
                pass

    @property
    def embedding_dim(self) -> int:
        return self._model.embedding_dim

    @property
    def model_name(self) -> str:
        return self._model.model_name
