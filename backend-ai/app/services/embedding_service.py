"""Lazy singleton SentenceTransformer for all-MiniLM-L6-v2."""

from __future__ import annotations

from typing import Sequence

import numpy as np

_encoder = None


def get_sentence_transformer():  # noqa: ANN201
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer

        _encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _encoder


def encode_texts(texts: Sequence[str]) -> np.ndarray:
    """L2-normalized rows suitable for cosine dot product."""
    model = get_sentence_transformer()
    vecs = model.encode(
        list(texts),
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(vecs, dtype=np.float64)


def cosine_vec(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-12:
        return 0.0
    return float(np.dot(a, b) / denom)


def chunked_windows(text: str, size: int = 280, step: int = 140) -> list[str]:
    t = text.replace("\n", " ").strip()
    if len(t) <= size:
        return [t] if t else []
    out = []
    for i in range(0, len(t), step):
        chunk = t[i : i + size].strip()
        if len(chunk) > 40:
            out.append(chunk)
    return out[:25]
