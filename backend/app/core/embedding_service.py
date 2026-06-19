"""
embedding_service.py — Sentence-Transformers embedding service (offline-capable).

Loads a local sentence-transformers model and provides vectorisation helpers
for both job descriptions and candidate resume text. Designed to run without
internet access after the initial model download.

Implementation: Issue 006
"""

from __future__ import annotations

import numpy as np


class EmbeddingService:
    """Wrap a sentence-transformers model for offline text embedding."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = None  # lazy-loaded

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an (N, D) embedding matrix for *texts*.

        Args:
            texts: List of N strings to encode.

        Returns:
            NumPy array of shape (N, D).
        """
        raise NotImplementedError("EmbeddingService.embed() — implementation pending (Issue 006)")
