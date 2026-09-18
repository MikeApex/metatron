"""
core/build/index.py — Build's OWN vector index, separate from search_memory.

Two uses: deduping Inquiry's questions against every question ever asked, and
letting the probe resolve a policy semantically rather than by exact key.

WHY NOT core/memory.py's INDEX. Encoding questions with FAISS is the right
idea; putting them in THAT index is not. `search_memory(query, k)` has no
source filter and is granted to eleven specialists, so a Build question stored
there would come back to an unrelated specialist as a RECALLED MEMORY — the
user's own remembered thought, except it was a question a build agent asked
itself. That index is also append-only with no rebuild path anywhere in the
repo, so the mistake would be permanent.

Same encoder (all-MiniLM-L6-v2, 384 dims), separate store, separate lock.

NOT BACKED UP, DELIBERATELY. scripts/metatron-backup.sh excludes *.faiss, and
this index is fully rebuildable from the job artifacts — every question in it
came from a question_set.json that IS backed up. `rebuild()` is that path, and
it exists from day one rather than being discovered as missing later, which is
core/memory.py's actual defect.

DEGRADES TO ABSENT. sentence-transformers and faiss are heavy optional
imports. Every function here returns an empty result rather than raising when
they are unavailable: without the index, question dedupe falls back to the
token-set check in schemas.py and policy resolution falls back to the exact
class path. Both are the correct-but-cruder outcome, not a failure.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

_DIM = 384
_MODEL_NAME = "all-MiniLM-L6-v2"
_LOCK_TIMEOUT = 30

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


def index_dir(persona: str | None = None) -> Path:
    from core.build.jobs import build_dir
    return build_dir(persona) / "index"


def _index_path(persona: str | None = None) -> Path:
    return index_dir(persona) / "build.faiss"


def _meta_path(persona: str | None = None) -> Path:
    return index_dir(persona) / "metadata.json"


def _lock(persona: str | None = None):
    from filelock import FileLock
    directory = index_dir(persona)
    directory.mkdir(parents=True, exist_ok=True)
    return FileLock(str(directory / ".build_index.lock"), timeout=_LOCK_TIMEOUT)


def available() -> bool:
    """True when both heavy dependencies import. Callers branch on this."""
    try:
        _get_model()
        _get_faiss()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

def _load(persona: str | None = None) -> tuple[Any, list[dict]]:
    faiss = _get_faiss()
    index_path, meta_path = _index_path(persona), _meta_path(persona)

    if index_path.exists() and meta_path.exists():
        index = faiss.read_index(str(index_path))
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except ValueError:
            metadata = []
        if not isinstance(metadata, list):
            metadata = []
    else:
        index = faiss.IndexFlatIP(_DIM)
        metadata = []

    # A desynced pair returns the WRONG entry's text for a query, which here
    # would mean deduping a question against a policy. Truncate to the shorter;
    # core/memory.py takes the same position for the same reason.
    if index.ntotal > len(metadata):
        keep = len(metadata)
        rebuilt = faiss.IndexFlatIP(_DIM)
        if keep:
            rebuilt.add(index.reconstruct_n(0, keep))
        index = rebuilt
    elif len(metadata) > index.ntotal:
        metadata = metadata[: index.ntotal]
    return index, metadata


def _save(index: Any, metadata: list[dict], persona: str | None = None) -> None:
    faiss = _get_faiss()
    index_dir(persona).mkdir(parents=True, exist_ok=True)
    # Metadata FIRST — the window between the two writes is then
    # index-old/metadata-new, where every index id still addresses a valid
    # entry. The reverse order puts the newest id out of range.
    _atomic(_meta_path(persona),
            lambda tmp: tmp.write_text(json.dumps(metadata, indent=2),
                                       encoding="utf-8"))
    _atomic(_index_path(persona),
            lambda tmp: faiss.write_index(index, str(tmp)))


def _atomic(path: Path, write_fn) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".",
                                    suffix=".tmp")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        write_fn(tmp)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _embed(text: str):
    model = _get_model()
    vec = model.encode([text], convert_to_numpy=True, normalize_embeddings=True)
    return vec.astype("float32")


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def add_question(text: str, job_id: str, question_id: str,
                 question_class: str = "", persona: str | None = None) -> bool:
    """Index one asked question. False when the index is unavailable."""
    return _add(text, {
        "entry_type": "question", "job_id": job_id,
        "question_id": question_id, "class": question_class, "text": text,
    }, persona)


def add_policy(policy: dict, persona: str | None = None) -> bool:
    """Index a policy's applies_to, which is what a question is matched against."""
    applies_to = str(policy.get("applies_to") or "").strip()
    if not applies_to:
        return False
    return _add(applies_to, {
        "entry_type": "policy", "policy_id": policy.get("id", ""),
        "domain": policy.get("domain", ""), "text": applies_to,
    }, persona)


def _add(text: str, meta: dict, persona: str | None) -> bool:
    text = str(text or "").strip()
    if not text or not available():
        return False
    with _lock(persona):
        index, metadata = _load(persona)
        index.add(_embed(text))
        metadata.append(meta)
        _save(index, metadata, persona)
    return True


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def search(query: str, k: int = 5, entry_type: str = "",
           persona: str | None = None) -> list[dict]:
    """
    Nearest entries with their cosine scores. [] when unavailable — never raises.

    Over-fetches when filtering by entry_type, because the filter is applied
    after the search: an index dominated by questions would otherwise return
    no policies at small k.
    """
    query = str(query or "").strip()
    if not query or not available():
        return []
    try:
        index, metadata = _load(persona)
        if index.ntotal == 0:
            return []
        want = min(index.ntotal, k * 8 if entry_type else k)
        scores, positions = index.search(_embed(query), want)
    except Exception:
        return []

    out: list[dict] = []
    for score, position in zip(scores[0], positions[0]):
        if position < 0 or position >= len(metadata):
            continue
        entry = metadata[position]
        if entry_type and entry.get("entry_type") != entry_type:
            continue
        out.append({**entry, "score": float(score)})
        if len(out) >= k:
            break
    return out


def nearest_question(text: str, persona: str | None = None) -> dict | None:
    hits = search(text, k=1, entry_type="question", persona=persona)
    return hits[0] if hits else None


def nearest_policy(text: str, persona: str | None = None) -> dict | None:
    hits = search(text, k=1, entry_type="policy", persona=persona)
    return hits[0] if hits else None


def duplicate_question(text: str, threshold: float = 0.93,
                       persona: str | None = None) -> dict | None:
    """
    A question already asked, near enough to be the same question.

    The threshold is deliberately high. A false positive here SILENTLY DROPS a
    question nobody then asks, which is the exact failure the compass rule
    exists to prevent; a false negative costs one duplicate adjudication. The
    asymmetry decides the number.
    """
    hit = nearest_question(text, persona)
    return hit if hit and hit.get("score", 0.0) >= threshold else None


# ---------------------------------------------------------------------------
# Rebuild — the path core/memory.py does not have
# ---------------------------------------------------------------------------

def rebuild(persona: str | None = None) -> dict:
    """
    Reconstruct the whole index from the job artifacts and the policy store.

    This is why the index is excluded from the backup rather than added to it:
    everything in it is derived, and the sources ARE backed up. Also the repair
    for the defect core/memory.py carries — re-embedding the same record on
    every write skews similarity toward heavily-edited entries — because a
    rebuild starts from one record per question.
    """
    from core.build.jobs import jobs_dir
    from core.build.policy import list_policies

    if not available():
        return {"rebuilt": False, "reason": "encoder or faiss unavailable"}

    faiss = _get_faiss()
    index = faiss.IndexFlatIP(_DIM)
    metadata: list[dict] = []
    seen: set[tuple[str, str]] = set()

    root = jobs_dir(persona)
    if root.is_dir():
        for path in sorted(root.glob("*/question_set.json")):
            try:
                artifact = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            job_id = artifact.get("job_id") or path.parent.name
            for question in artifact.get("spine") or []:
                text = str(question.get("text") or "").strip()
                key = (job_id, str(question.get("id") or ""))
                if not text or key in seen:
                    continue
                seen.add(key)
                index.add(_embed(text))
                metadata.append({
                    "entry_type": "question", "job_id": job_id,
                    "question_id": question.get("id", ""),
                    "class": question.get("class", ""), "text": text,
                })

    for policy in list_policies(persona):
        applies_to = str(policy.get("applies_to") or "").strip()
        if not applies_to:
            continue
        index.add(_embed(applies_to))
        metadata.append({
            "entry_type": "policy", "policy_id": policy.get("id", ""),
            "domain": policy.get("domain", ""), "text": applies_to,
        })

    with _lock(persona):
        _save(index, metadata, persona)
    return {
        "rebuilt": True,
        "questions": sum(1 for m in metadata if m["entry_type"] == "question"),
        "policies": sum(1 for m in metadata if m["entry_type"] == "policy"),
    }


def stats(persona: str | None = None) -> dict:
    if not available():
        return {"available": False, "entries": 0}
    try:
        index, metadata = _load(persona)
    except Exception:
        return {"available": False, "entries": 0}
    return {
        "available": True,
        "entries": len(metadata),
        "questions": sum(1 for m in metadata if m.get("entry_type") == "question"),
        "policies": sum(1 for m in metadata if m.get("entry_type") == "policy"),
        "vectors": int(index.ntotal),
    }
