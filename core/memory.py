"""
core/memory.py — FAISS vector memory layer.

Embeds log and journal entries using a local sentence-transformers model
(all-MiniLM-L6-v2, ~80MB, no API call, runs on-device). Persists a FAISS
index alongside a metadata JSON file so past entries survive across sessions.

Persona-scoped: data/personas/{persona}/memory/

Public API:
  index_entry(text, source, entry_date)  — embed and store one entry
  search_memory(query, k)                — return k most relevant past entries
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

from filelock import FileLock

from core.persona import persona_data_dir
from typing import Any

import numpy as np

_ROOT = Path(__file__).parent.parent
_MODEL_NAME = "all-MiniLM-L6-v2"
_LOCK_TIMEOUT = 30  # seconds; an embed + write is sub-second, so this only trips on a stuck holder

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
    return persona_data_dir() / "memory"


def _index_path() -> Path:
    return _memory_dir() / "index.faiss"


def _meta_path() -> Path:
    return _memory_dir() / "metadata.json"


def _lock_path() -> Path:
    return _memory_dir() / ".memory.lock"


def _memory_lock() -> FileLock:
    """
    Cross-process lock guarding the index + metadata pair.

    WHY: `index_entry()` is a read-modify-write of two files that must stay in step, and it
    runs in *two* processes — the server writes logs (tools/logger.py) while the scheduler
    writes journal entries (tools/diarist.py). The single-worker pool in core/background.py
    serialises within one process only, so nothing prevented the two interleaving. The symptom
    was `json.JSONDecodeError: Extra data` on metadata.json — one process truncating and
    rewriting while the other's buffer was still flushing — which took search_memory down for
    the whole persona until the file was repaired by hand.

    Scoped per persona: the path is derived from persona_data_dir(), so two personas never
    block each other.
    """
    _memory_dir().mkdir(parents=True, exist_ok=True)
    return FileLock(str(_lock_path()), timeout=_LOCK_TIMEOUT)


def _atomic_write_bytes(path: Path, write_fn) -> None:
    """
    Write via a temp file in the same directory, then rename over the target.

    os.replace is atomic on POSIX, so a reader either sees the whole old file or the whole new
    one — never a half-written prefix. The lock above prevents concurrent *writers*; this
    prevents a lock-free reader (search_memory in another process) from seeing a torn file.
    """
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        write_fn(tmp)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _embed(text: str) -> np.ndarray:
    model = _get_model()
    vec = model.encode([text], convert_to_numpy=True, normalize_embeddings=True)
    return vec.astype("float32")


def _read_metadata(meta_path: Path) -> list[dict]:
    """
    Read metadata.json, salvaging a file left corrupt by the pre-lock race.

    The historical corruption is always the same shape — a complete JSON array followed by
    trailing bytes from an interleaved write ("Extra data: line 557 column 2"). `raw_decode`
    parses the leading document and reports where it ended, so the good prefix is recoverable
    without hand-editing the file. Anything else is a genuine parse failure and raises.
    """
    raw = meta_path.read_text()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        if "Extra data" not in str(exc):
            raise
        salvaged, end = json.JSONDecoder().raw_decode(raw)
        if not isinstance(salvaged, list):
            raise
        print(
            f"[memory] repaired {meta_path}: dropped {len(raw) - end} trailing bytes "
            f"from an interleaved write, kept {len(salvaged)} entries",
            file=sys.stderr,
        )
        return salvaged


def _load_index() -> tuple[Any, list[dict]]:
    """Load (or create) the FAISS index and metadata list."""
    faiss = _get_faiss()
    dim = 384  # all-MiniLM-L6-v2 output dimension

    meta_path = _meta_path()
    index_path = _index_path()

    if index_path.exists() and meta_path.exists():
        index = faiss.read_index(str(index_path))
        metadata = _read_metadata(meta_path)
    else:
        index = faiss.IndexFlatIP(dim)  # Inner product on normalized vectors = cosine similarity
        metadata = []

    # A desynced pair returns the *wrong entry's* text for a query — worse than losing the tail.
    # Truncate to the shorter of the two; the next _save_index writes the repair back.
    if index.ntotal > len(metadata):
        keep = len(metadata)
        rebuilt = faiss.IndexFlatIP(dim)
        if keep:
            rebuilt.add(index.reconstruct_n(0, keep))
        print(
            f"[memory] index/metadata desync: {index.ntotal} vectors vs {keep} entries — "
            f"truncated index to {keep}",
            file=sys.stderr,
        )
        index = rebuilt
    elif len(metadata) > index.ntotal:
        print(
            f"[memory] index/metadata desync: {index.ntotal} vectors vs {len(metadata)} "
            f"entries — truncated metadata to {index.ntotal}",
            file=sys.stderr,
        )
        metadata = metadata[: index.ntotal]

    return index, metadata


def _save_index(index: Any, metadata: list[dict]) -> None:
    faiss = _get_faiss()
    memory_dir = _memory_dir()
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Order matters. These are two files with no shared transaction, so a lock-free reader can
    # always catch the moment between them. Writing metadata FIRST makes that window
    # index-old/metadata-new, where every index id still addresses a valid entry. The reverse
    # order gives index-new/metadata-old, where the newest id is out of range — an IndexError
    # in search_memory.
    _atomic_write_bytes(
        _meta_path(),
        lambda tmp: tmp.write_text(json.dumps(metadata, indent=2)),
    )
    _atomic_write_bytes(
        _index_path(),
        lambda tmp: faiss.write_index(index, str(tmp)),
    )


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

    # Embed outside the lock — it is the slow part (model inference) and touches no shared file.
    vec = _embed(text)

    with _memory_lock():
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
    # Reads take the lock too. Atomic renames make a torn *file* impossible, but the two files
    # are still written in sequence, and _load_index's desync repair must not run concurrently
    # with a writer or it would "repair" a pair that was mid-update and about to be consistent.
    with _memory_lock():
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
