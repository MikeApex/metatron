"""
core/memory.py — FAISS vector memory layer.

Embeds log and journal entries using a local sentence-transformers model
(all-MiniLM-L6-v2, ~80MB, no API call, runs on-device). Persists a FAISS
index alongside a metadata JSON file so past entries survive across sessions.

Persona-scoped when AI_TEST_PERSONA is set:
  Real user:  data/memory/
  Persona:    data/personas/{persona}/memory/

Public API:
  index_entry(text, source, entry_date)  — embed and store one entry
  search_memory(query, k)                — return k most relevant past entries
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

_ROOT = Path(__file__).parent.parent
_MODEL_NAME = "all-MiniLM-L6-v2"

# Lazy-loaded singletons — imported once per process.
_model = None
_faiss = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def _get_faiss():
    global _faiss
    if _faiss is None:
        import faiss as _faiss_module
        _faiss = _faiss_module
    return _faiss


def _memory_dir() -> Path:
    persona = os.environ.get("AI_TEST_PERSONA")
    if persona:
        return _ROOT / "data" / "personas" / persona / "memory"
    return _ROOT / "data" / "memory"


def _index_path() -> Path:
    return _memory_dir() / "index.faiss"


def _meta_path() -> Path:
    return _memory_dir() / "metadata.json"


def _embed(text: str) -> np.ndarray:
    model = _get_model()
    vec = model.encode([text], convert_to_numpy=True, normalize_embeddings=True)
    return vec.astype("float32")


def _load_index() -> tuple[Any, list[dict]]:
    """Load (or create) the FAISS index and metadata list."""
    faiss = _get_faiss()
    dim = 384  # all-MiniLM-L6-v2 output dimension

    meta_path = _meta_path()
    index_path = _index_path()

    if index_path.exists() and meta_path.exists():
        index = faiss.read_index(str(index_path))
        with open(meta_path) as f:
            metadata = json.load(f)
    else:
        index = faiss.IndexFlatIP(dim)  # Inner product on normalized vectors = cosine similarity
        metadata = []

    return index, metadata


def _save_index(index: Any, metadata: list[dict]) -> None:
    faiss = _get_faiss()
    memory_dir = _memory_dir()
    memory_dir.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(_index_path()))

    with open(_meta_path(), "w") as f:
        json.dump(metadata, f, indent=2)

    os.chmod(_meta_path(), 0o600)


def index_entry(text: str, source: str, entry_date: str = "") -> None:
    """
    Embed a text entry and add it to the FAISS index.

    Args:
        text: The text to embed (log content, journal entry, etc.)
        source: Origin label, e.g. "log", "journal", "archive".
        entry_date: ISO date string. Defaults to today if empty.
    """
    if not text or not text.strip():
        return

    if not entry_date:
        entry_date = date.today().isoformat()

    vec = _embed(text)
    index, metadata = _load_index()

    index.add(vec)
    metadata.append({
        "text": text,
        "source": source,
        "date": entry_date,
    })

    _save_index(index, metadata)


def search_memory(query: str, k: int = 5) -> list[dict]:
    """
    Retrieve the k most semantically relevant past entries for a query.

    Args:
        query: Natural language search query.
        k: Number of results to return (default 5).

    Returns:
        List of dicts with 'text', 'source', 'date', and 'score' keys,
        sorted by relevance descending. Empty list if index has no entries.
    """
    index, metadata = _load_index()

    if index.ntotal == 0:
        return []

    k = min(k, index.ntotal)
    vec = _embed(query)
    scores, indices = index.search(vec, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        entry = dict(metadata[idx])
        entry["score"] = float(score)
        results.append(entry)

    return results
