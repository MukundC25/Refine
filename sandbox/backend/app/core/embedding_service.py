"""
embedding_service.py — Sentence-Transformers embedding service (offline-capable).

Loads a local sentence-transformers model and provides vectorisation helpers
for both job descriptions and candidate resume text.  After the first run the
model weights live in the HuggingFace cache (~/.cache/huggingface/hub/), so
all subsequent calls need no network access.

Public API
----------
    EmbeddingService                          — main class
        .embed_text(text)                     → (384,) float32
        .embed_batch(texts)                   → (N, 384) float32
        .cosine_similarity_topk(q, C, k=2000) → (indices, scores)
        .embed(texts)                         → (N, 384) — backward-compat alias

    precompute_candidate_embeddings(...)      — stream + save to .npy
    load_embeddings(path)                     → (matrix, id_list)

Implementation: Issue 006
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "all-MiniLM-L6-v2"
_EMBEDDING_DIM = 384


# ---------------------------------------------------------------------------
# EmbeddingService
# ---------------------------------------------------------------------------


class EmbeddingService:
    """Wrap a sentence-transformers model for offline text embedding.

    The model is lazy-loaded on the first call to :meth:`embed_text` or
    :meth:`embed_batch`, so importing this module is cheap.

    Default model: ``all-MiniLM-L6-v2``
      • 22 MB weights, 384-dimensional output
      • CPU throughput: ~1 000 sentences / second
      • After first download the model is served from the local HF cache
    """

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self._model = None  # lazy-loaded on first encode call

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _load_model(self):
        """Return the SentenceTransformer model, loading it if needed."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415

            logger.info("Loading sentence-transformers model '%s' …", self.model_name)
            self._model = SentenceTransformer(self.model_name)
            logger.info("Model ready.")
        return self._model

    # ------------------------------------------------------------------
    # Public encoding methods
    # ------------------------------------------------------------------

    def embed_text(self, text: str) -> np.ndarray:
        """Encode a single string and return a (384,) float32 vector.

        Args:
            text: Input string to embed.

        Returns:
            1-D NumPy array, shape ``(384,)``, dtype ``float32``.
        """
        model = self._load_model()
        vec = model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        return np.asarray(vec, dtype=np.float32)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Encode a list of strings and return an (N, 384) float32 matrix.

        Substantially faster than calling :meth:`embed_text` N times: the
        underlying transformer processes all sentences in a single batched
        forward pass.

        Args:
            texts: List of N strings to encode.

        Returns:
            2-D NumPy array, shape ``(N, 384)``, dtype ``float32``.
            Returns an empty ``(0, 384)`` array for an empty input.
        """
        if not texts:
            return np.empty((0, _EMBEDDING_DIM), dtype=np.float32)

        model = self._load_model()
        vecs = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=False,
            show_progress_bar=False,
            batch_size=512,
        )
        return np.asarray(vecs, dtype=np.float32)

    # ------------------------------------------------------------------
    # Cosine similarity
    # ------------------------------------------------------------------

    def cosine_similarity_topk(
        self,
        query_vec: np.ndarray,
        corpus_vecs: np.ndarray,
        k: int = 2000,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return top-k corpus indices ranked by cosine similarity.

        Pure NumPy — no model call required.  Runs in < 1 s for a
        100 K × 384 corpus on a modern CPU.

        Algorithm
        ---------
        1. L2-normalise query and every corpus row.
        2. Matrix-multiply → cosine scores (N,).
        3. ``np.argpartition`` selects the k largest in O(N) time.
        4. The k candidates are sorted by descending score.

        Args:
            query_vec:   Query embedding, shape ``(384,)`` or ``(1, 384)``.
            corpus_vecs: Corpus matrix, shape ``(N, 384)``.
            k:           Number of top results.  Clamped to N when k > N.

        Returns:
            Tuple ``(indices, scores)`` where both arrays have length ``k``,
            ordered best-first.  Scores are cosine similarities in [-1, 1].
        """
        n = corpus_vecs.shape[0]
        k = min(k, n)

        q = query_vec.flatten().astype(np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm > 0:
            q = q / q_norm

        # Normalise corpus rows — guard against zero-magnitude rows
        row_norms = np.linalg.norm(corpus_vecs, axis=1, keepdims=True)
        row_norms = np.where(row_norms == 0, 1.0, row_norms)
        c_norm = (corpus_vecs / row_norms).astype(np.float32)

        scores = c_norm @ q  # (N,) cosine similarities

        # O(N) partial sort, then sort only the k candidates
        top_k_idx = np.argpartition(scores, -k)[-k:]
        top_k_idx = top_k_idx[np.argsort(scores[top_k_idx])[::-1]]

        return top_k_idx, scores[top_k_idx]

    # ------------------------------------------------------------------
    # Backward-compat alias (original stub had embed(texts) → (N, D))
    # ------------------------------------------------------------------

    def embed(self, texts: list[str]) -> np.ndarray:
        """Alias for :meth:`embed_batch`; kept for backward compatibility."""
        return self.embed_batch(texts)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def precompute_candidate_embeddings(
    candidates_path: str,
    output_path: str,
    batch_size: int = 512,
    ids_path: str | None = None,
    model_name: str = _DEFAULT_MODEL,
    show_progress: bool = True,
) -> None:
    """Stream all candidates, embed them, and persist the matrix to disk.

    Keeps memory usage constant regardless of dataset size by processing one
    batch at a time.  Writes two files:

    * ``output_path``  — float32 NumPy matrix, shape ``(N, 384)``.
    * ``ids_path``     — JSON array of N candidate IDs (row-aligned).

    Args:
        candidates_path: ``.jsonl`` or ``.jsonl.gz`` candidate file.
        output_path:     Destination ``.npy`` file for the embedding matrix.
        batch_size:      Candidates per embedding batch (default: 512).
        ids_path:        Companion ``_ids.json`` path.  Defaults to
                         ``<output_stem>_ids.json`` in the same directory.
        model_name:      sentence-transformers model identifier.
        show_progress:   Display a ``tqdm`` progress bar (default: True).
    """
    # Relative import — works when called as part of the backend package
    from .candidate_loader import (  # noqa: PLC0415
        build_candidate_text,
        load_candidates_batched,
    )

    # Resolve companion IDs path
    if ids_path is None:
        p = Path(output_path)
        ids_path = str(p.parent / (p.stem + "_ids.json"))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    service = EmbeddingService(model_name=model_name)
    all_embeddings: list[np.ndarray] = []
    all_ids: list[str] = []

    # Optional tqdm bar — silently falls back to plain logging if not installed
    _bar = None
    if show_progress:
        try:
            from tqdm import tqdm  # noqa: PLC0415

            _bar = tqdm(desc="Embedding candidates", unit="batch")
        except ImportError:
            pass

    for batch in load_candidates_batched(candidates_path, batch_size=batch_size):
        texts = [build_candidate_text(c) for c in batch]
        ids = [c.candidate_id for c in batch]

        vecs = service.embed_batch(texts)  # (batch_size, 384)
        all_embeddings.append(vecs)
        all_ids.extend(ids)

        if _bar is not None:
            _bar.update(1)
            _bar.set_postfix(total=len(all_ids))
        else:
            logger.info("Embedded %d candidates …", len(all_ids))

    if _bar is not None:
        _bar.close()

    if not all_embeddings:
        logger.warning("No candidates found in '%s'; nothing written.", candidates_path)
        return

    matrix = np.vstack(all_embeddings).astype(np.float32)

    np.save(output_path, matrix)
    logger.info("Saved embedding matrix %s → %s", matrix.shape, output_path)

    with open(ids_path, "w", encoding="utf-8") as fh:
        json.dump(all_ids, fh)
    logger.info("Saved candidate IDs → %s", ids_path)


def load_embeddings(path: str) -> tuple[np.ndarray, list[str]]:
    """Load a pre-computed embedding matrix and its companion candidate-ID list.

    Expects a companion ``<stem>_ids.json`` file co-located with *path* — the
    layout produced by :func:`precompute_candidate_embeddings`.

    Args:
        path: Path to a ``.npy`` embedding matrix.

    Returns:
        Tuple ``(matrix, ids)`` where *matrix* is shape ``(N, 384)``
        float32 and *ids* is a list of N candidate ID strings in the same
        row order as the matrix.

    Raises:
        FileNotFoundError: If *path* or the companion IDs file is missing.
        ValueError:        If matrix row count and IDs list length disagree.
    """
    p = Path(path)
    ids_file = p.parent / (p.stem + "_ids.json")

    matrix = np.load(str(p)).astype(np.float32)

    with open(str(ids_file), "r", encoding="utf-8") as fh:
        ids: list[str] = json.load(fh)

    if len(ids) != matrix.shape[0]:
        raise ValueError(
            f"Embedding matrix has {matrix.shape[0]} rows but "
            f"'{ids_file.name}' has {len(ids)} entries — files may be out of sync."
        )

    return matrix, ids
