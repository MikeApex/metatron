"""
tools/baselines.py — User-defined baseline periods and semantic state anchors.

Two complementary baseline systems:

1. Biographical periods (write_baseline_period / read_baseline_periods):
   Named life periods the user has identified as meaningful reference points.
   Stores the user's own narrative, fulfillment score, and retrospective layers.

2. Semantic anchors (create_semantic_anchor / score_against_anchors):
   Canonical human experiential states (burnout, deep_focus, etc.) embedded
   using all-MiniLM-L6-v2. Pattern Miner scores current log centroids against
   these anchors from day one — no months of accumulation required.

3. Aspirational baseline (write_aspirational_baseline):
   Goals-oriented self-report from the Goals Interview. Stores what good/hard
   weeks look like in the user's own words. Working draft at A3; re-run at A5b
   after the full Goals Interview.

4. Shuffled null score (shuffled_null_score):
   Permutation baseline for sparse data — establishes what random signal looks
   like for this user's log history before treating deviations as meaningful.

Biographical periods and aspirational baselines are persona-scoped when
AI_TEST_PERSONA is set. Semantic anchors are not persona-scoped (canonical).
Sensitive-tier, local-only.
"""

import json
import os
import random
from datetime import date, timedelta
from pathlib import Path

_ROOT = Path(__file__).parent.parent

# Lazy-loaded embedding model — same as core/memory.py (all-MiniLM-L6-v2, 384-dim).
# Do not introduce a second embedding model.
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _embed(text: str) -> list[float]:
    """Embed text and return as a plain list for JSON serialisation."""
    import numpy as np
    model = _get_model()
    vec = model.encode([text], convert_to_numpy=True, normalize_embeddings=True)
    return vec[0].astype("float32").tolist()


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two pre-normalised vectors (dot product)."""
    import numpy as np
    return float(np.dot(np.array(a, dtype="float32"), np.array(b, dtype="float32")))


def _baselines_dir() -> Path:
    """Directory for non-persona-scoped baseline data."""
    return _ROOT / "data" / "baselines"


def _baselines_path() -> Path:
    persona = os.environ.get("AI_TEST_PERSONA")
    if persona:
        return _ROOT / "data" / "personas" / persona / "baselines.json"
    return _ROOT / "data" / "baselines.json"


def _anchors_path() -> Path:
    return _baselines_dir() / "semantic_anchors.json"


def _aspirational_path(persona: str) -> Path:
    if persona:
        p = _ROOT / "data" / "personas" / persona / "aspirational_baseline.json"
    else:
        p = _baselines_dir() / "aspirational_baseline.json"
    return p


def _logs_dir(persona: str) -> Path:
    if persona:
        return _ROOT / "data" / "personas" / persona / "logs"
    return _ROOT / "data" / "logs"


def _load_anchors() -> list[dict]:
    p = _anchors_path()
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)


def _save_anchors(anchors: list[dict]) -> None:
    p = _anchors_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(anchors, f, indent=2)
    os.chmod(p, 0o600)


def _load() -> list[dict]:
    p = _baselines_path()
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)


def _save(periods: list[dict]) -> None:
    p = _baselines_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(periods, f, indent=2)
    os.chmod(p, 0o600)


def write_baseline_period(
    name: str,
    user_memory: str,
    fulfillment_score: int = 0,
    start_date: str = "",
    end_date: str = "",
    tags: list[str] | None = None,
) -> str:
    """
    Record a named baseline period.

    Args:
        name:              Short identifier (e.g. "summer_2022_flow_state",
                           "pre_kids_creative_peak", "year_of_the_column").
        user_memory:       The user's narrative about this period — what was
                           happening, why it felt significant. Captured verbatim;
                           the user's own vocabulary has higher salience than
                           a model paraphrase.
        fulfillment_score: User's assessment 1–10 (10 = deeply fulfilled).
                           0 means not yet scored.
        start_date:        ISO date, if the period can be placed in time.
        end_date:          ISO date. Leave empty if open-ended or undated.
        tags:              Optional labels (e.g. ["fulfilled", "creative",
                           "high_output", "difficult"]).

    Returns:
        Confirmation string.
    """
    periods = _load()
    existing = {p["name"]: i for i, p in enumerate(periods)}

    today = date.today().isoformat()
    entry = {
        "name": name,
        "user_memory": user_memory,
        "fulfillment_score": fulfillment_score,
        "start_date": start_date,
        "end_date": end_date,
        "tags": tags or [],
        "retrospectives": [],
        "created": today,
        "updated": today,
    }

    if name in existing:
        entry["retrospectives"] = periods[existing[name]].get("retrospectives", [])
        entry["created"] = periods[existing[name]].get("created", today)
        periods[existing[name]] = entry
        action = "updated"
    else:
        periods.append(entry)
        action = "created"

    _save(periods)
    return f"Baseline period '{name}' {action}."


def read_baseline_periods(tag: str = "") -> list[dict]:
    """
    Return all defined baseline periods, optionally filtered by tag.

    Args:
        tag: If given, return only periods with this tag. Leave empty for all.

    Returns:
        List of baseline period dicts.
    """
    periods = _load()
    if tag:
        periods = [p for p in periods if tag in p.get("tags", [])]
    return periods


def write_retrospective(
    period_name: str,
    assessment: str,
    revised_score: int = 0,
) -> str:
    """
    Add a retrospective assessment to a baseline period.

    Called when the user revisits how they remember a past period — days,
    months, or years later. Memory of a period changes over time; capturing
    multiple retrospectives creates a time-dilation layer that the Pattern
    Miner can use to distinguish in-the-moment assessments from longer-term
    pattern understanding.

    Args:
        period_name:    Name of the baseline period to annotate.
        assessment:     The user's current view of this period, in their words.
        revised_score:  Updated fulfillment score (1–10). 0 = not revised.

    Returns:
        Confirmation string.
    """
    periods = _load()
    today = date.today().isoformat()

    for period in periods:
        if period["name"] == period_name:
            period.setdefault("retrospectives", []).append({
                "date": today,
                "assessment": assessment,
                "revised_score": revised_score,
            })
            if revised_score:
                period["fulfillment_score"] = revised_score
            period["updated"] = today
            _save(periods)
            return f"Retrospective added to '{period_name}' ({today})."

    return f"Baseline period '{period_name}' not found."


def get_baseline_context(start_date: str, end_date: str) -> list[dict]:
    """
    Return any baseline periods that overlap with a date range.

    Used by the Pattern Miner to check whether the target analysis window
    coincides with a user-defined baseline period — which would make it
    a reference point rather than something to compare against one.

    Args:
        start_date: ISO date (YYYY-MM-DD).
        end_date:   ISO date (YYYY-MM-DD).

    Returns:
        List of matching baseline period dicts (may be empty).
    """
    periods = _load()
    if not periods:
        return []

    try:
        query_start = date.fromisoformat(start_date)
        query_end = date.fromisoformat(end_date)
    except ValueError:
        return []

    matches = []
    for period in periods:
        ps = period.get("start_date")
        pe = period.get("end_date")
        if not ps:
            continue
        try:
            p_start = date.fromisoformat(ps)
            p_end = date.fromisoformat(pe) if pe else date.today()
            if p_start <= query_end and p_end >= query_start:
                matches.append(period)
        except ValueError:
            continue

    return matches


# ---------------------------------------------------------------------------
# Semantic anchor functions
# ---------------------------------------------------------------------------


def create_semantic_anchor(label: str, description: str) -> str:
    """
    Embed a canonical state description and store it as a named anchor.

    Anchors are universal, not persona-scoped — they represent canonical human
    experiential states (burnout, deep_focus, etc.) that all analysis can score
    against regardless of which user or persona is active.

    Args:
        label:       Short slug (e.g. "burnout", "deep_focus").
        description: Prose description of what this state feels like. The richer
                     and more specific, the better the embedding quality.

    Returns:
        Confirmation string.
    """
    anchors = _load_anchors()
    existing = {a["label"]: i for i, a in enumerate(anchors)}

    today = date.today().isoformat()
    embedding = _embed(description)

    entry = {
        "label": label,
        "description": description,
        "embedding": embedding,
        "created": today,
    }

    if label in existing:
        entry["created"] = anchors[existing[label]].get("created", today)
        anchors[existing[label]] = entry
        action = "updated"
    else:
        anchors.append(entry)
        action = "created"

    _save_anchors(anchors)
    return f"Semantic anchor '{label}' {action}."


def write_aspirational_baseline(
    persona: str,
    good_week: str,
    hard_week: str,
    peak_days: str,
    floor_days: str,
) -> str:
    """
    Record the user's aspirational baseline from the Goals Interview.

    Stores what good/hard weeks and peak/floor days look like in the user's own
    words. This is a working draft at A3; re-run at A5b after the full Goals
    Interview to update with mission-level data.

    Args:
        persona:    Persona slug for test runs; empty string for the real user.
        good_week:  User's description of a recent week that felt genuinely good.
        hard_week:  User's description of a week that felt hard or depleted.
        peak_days:  What a peak day looks like — signals of the user's best days.
        floor_days: The floor — a day to avoid; signals of heading there.

    Returns:
        Confirmation string.
    """
    p = _aspirational_path(persona)
    p.parent.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    existing = {}
    if p.exists():
        with open(p) as f:
            existing = json.load(f)

    entry = {
        "persona": persona,
        "good_week": good_week,
        "hard_week": hard_week,
        "peak_days": peak_days,
        "floor_days": floor_days,
        "created": existing.get("created", today),
        "updated": today,
    }

    with open(p, "w") as f:
        json.dump(entry, f, indent=2)
    os.chmod(p, 0o600)

    action = "updated" if existing else "created"
    return f"Aspirational baseline {action} ({today})."


def shuffled_null_score(
    persona: str,
    window_days: int,
    n_permutations: int = 100,
) -> dict:
    """
    Build a null distribution of anchor similarity scores via random permutation.

    Takes the full log history for a persona, randomly samples `window_days`-sized
    windows `n_permutations` times, and records the anchor similarity scores for
    each draw. Returns mean ± std per anchor — the baseline against which actual
    window scores can be compared.

    Use this when you have sparse data (< 3 months) and want to distinguish real
    signal from random variation before reporting a pattern as meaningful.

    Args:
        persona:        Persona slug; empty string for the real user.
        window_days:    Size of the analysis window in days (e.g. 7, 30).
        n_permutations: Number of random draws (default 100).

    Returns:
        Dict of {anchor_label: {"mean": float, "std": float, "n": int}}.
        Empty dict if fewer log entries exist than window_days or no anchors set.
    """
    import numpy as np

    anchors = _load_anchors()
    if not anchors:
        return {}

    logs_dir = _logs_dir(persona)
    if not logs_dir.exists():
        return {}

    # Collect all available log entries as (date_str, text) pairs.
    entries: list[tuple[str, str]] = []
    for log_file in sorted(logs_dir.glob("*.json")):
        if log_file.name == "quality_events.json":
            continue
        try:
            with open(log_file) as f:
                data = json.load(f)
            entries.append((log_file.stem, json.dumps(data)))
        except (json.JSONDecodeError, OSError):
            continue

    if len(entries) < window_days:
        return {}

    # Precompute embeddings for all entries to avoid re-embedding each permutation.
    all_embeddings = [_embed(text) for _, text in entries]
    anchor_embeddings = [a["embedding"] for a in anchors]
    anchor_labels = [a["label"] for a in anchors]

    scores_by_anchor: dict[str, list[float]] = {label: [] for label in anchor_labels}

    for _ in range(n_permutations):
        sample_indices = random.sample(range(len(entries)), window_days)
        sample_vecs = [all_embeddings[i] for i in sample_indices]
        centroid = np.mean(np.array(sample_vecs, dtype="float32"), axis=0)
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm
        for label, anchor_vec in zip(anchor_labels, anchor_embeddings):
            scores_by_anchor[label].append(_cosine_sim(centroid.tolist(), anchor_vec))

    result = {}
    for label, scores in scores_by_anchor.items():
        arr = np.array(scores, dtype="float32")
        result[label] = {
            "mean": float(arr.mean()),
            "std": float(arr.std()),
            "n": n_permutations,
        }
    return result


def score_against_anchors(
    persona: str,
    date_range: dict,
) -> dict:
    """
    Score a date range's log entries against all semantic anchors.

    Embeds each log entry in the range, averages to a centroid, then computes
    cosine similarity to every semantic anchor. Higher similarity = current state
    resembles that anchor more closely.

    Args:
        persona:    Persona slug; empty string for the real user.
        date_range: Dict with "start" and "end" keys (ISO dates, YYYY-MM-DD).

    Returns:
        Dict of {anchor_label: cosine_similarity (0.0–1.0)}.
        Empty dict if no logs in range or no anchors exist.
    """
    import numpy as np

    anchors = _load_anchors()
    if not anchors:
        return {}

    start_str = date_range.get("start", "")
    end_str = date_range.get("end", "")
    if not start_str or not end_str:
        return {}

    try:
        start_dt = date.fromisoformat(start_str)
        end_dt = date.fromisoformat(end_str)
    except ValueError:
        return {}

    logs_dir = _logs_dir(persona)
    if not logs_dir.exists():
        return {}

    embeddings = []
    current = start_dt
    while current <= end_dt:
        log_file = logs_dir / f"{current.isoformat()}.json"
        if log_file.exists():
            try:
                with open(log_file) as f:
                    data = json.load(f)
                embeddings.append(_embed(json.dumps(data)))
            except (json.JSONDecodeError, OSError):
                pass
        current += timedelta(days=1)

    if not embeddings:
        return {}

    centroid = np.mean(np.array(embeddings, dtype="float32"), axis=0)
    norm = np.linalg.norm(centroid)
    if norm > 0:
        centroid = centroid / norm

    return {
        anchor["label"]: _cosine_sim(centroid.tolist(), anchor["embedding"])
        for anchor in anchors
    }


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

WRITE_BASELINE_PERIOD_SCHEMA = {
    "name": "write_baseline_period",
    "description": (
        "Record a named reference period that can serve as a baseline for pattern comparison. "
        "Use for periods the user identifies as meaningful: a time of genuine fulfillment, "
        "a difficult stretch, a creative peak, or a transitional phase. "
        "Capture the user's own words — their internal vocabulary carries more meaning "
        "than a paraphrase. The baseline interview should surface these memories."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Short slug identifier (e.g. 'summer_2022_flow_state').",
            },
            "user_memory": {
                "type": "string",
                "description": "The user's narrative about this period, in their own words.",
            },
            "fulfillment_score": {
                "type": "integer",
                "description": "User's assessment 1–10 (10 = deeply fulfilled). 0 if not scored.",
            },
            "start_date": {
                "type": "string",
                "description": "ISO date if the period can be placed in time (YYYY-MM-DD).",
            },
            "end_date": {
                "type": "string",
                "description": "ISO date. Leave empty if open-ended or the user can't place it.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Labels e.g. ['fulfilled', 'creative', 'high_output', 'difficult'].",
            },
        },
        "required": ["name", "user_memory"],
    },
}

READ_BASELINE_PERIODS_SCHEMA = {
    "name": "read_baseline_periods",
    "description": (
        "Retrieve user-defined baseline periods. Call at the start of a pattern analysis "
        "session to understand what reference points the user has already identified. "
        "If the analysis window overlaps with a baseline period, note it — that period "
        "may be the right comparison point rather than a generic trailing window."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "tag": {
                "type": "string",
                "description": "Filter by tag (e.g. 'fulfilled'). Leave empty to return all.",
            },
        },
        "required": [],
    },
}

WRITE_RETROSPECTIVE_SCHEMA = {
    "name": "write_retrospective",
    "description": (
        "Add a retrospective assessment to a baseline period. "
        "Memory of a past period changes over time — a stretch that felt great in the moment "
        "may be understood differently at 6 months or a year's distance. "
        "Capturing multiple retrospectives at different time distances creates a time-dilation "
        "layer the Pattern Miner can use to distinguish in-the-moment from long-term assessments."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "period_name": {
                "type": "string",
                "description": "Name of the baseline period to annotate.",
            },
            "assessment": {
                "type": "string",
                "description": "The user's current view of this period, in their own words.",
            },
            "revised_score": {
                "type": "integer",
                "description": "Updated fulfillment score 1–10. 0 if unchanged.",
            },
        },
        "required": ["period_name", "assessment"],
    },
}

GET_BASELINE_CONTEXT_SCHEMA = {
    "name": "get_baseline_context",
    "description": (
        "Check whether a date range overlaps with any user-defined baseline periods. "
        "Call before running pattern analysis to see if the target window is itself "
        "a reference period — which changes how findings should be framed."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "start_date": {"type": "string", "description": "ISO date (YYYY-MM-DD)."},
            "end_date": {"type": "string", "description": "ISO date (YYYY-MM-DD)."},
        },
        "required": ["start_date", "end_date"],
    },
}

CREATE_SEMANTIC_ANCHOR_SCHEMA = {
    "name": "create_semantic_anchor",
    "description": (
        "Embed a canonical experiential state and store it as a named anchor. "
        "Anchors are universal reference points (burnout, deep_focus, anxiety, etc.) "
        "that the Pattern Miner scores current log windows against. "
        "Not persona-scoped — anchors are shared across all analysis."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "label": {
                "type": "string",
                "description": "Short slug identifier (e.g. 'burnout', 'deep_focus').",
            },
            "description": {
                "type": "string",
                "description": (
                    "Prose description of what this state feels like — "
                    "the richer and more specific, the better the embedding quality."
                ),
            },
        },
        "required": ["label", "description"],
    },
}

WRITE_ASPIRATIONAL_BASELINE_SCHEMA = {
    "name": "write_aspirational_baseline",
    "description": (
        "Record the user's aspirational baseline from the Goals Interview. "
        "Stores what good/hard weeks and peak/floor days look like in the user's own words. "
        "Working draft at A3; re-run after the full Goals Interview (A5b) to update "
        "with mission-level data."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "persona": {
                "type": "string",
                "description": "Persona slug for test runs; empty string for the real user.",
            },
            "good_week": {
                "type": "string",
                "description": "User's description of a recent week that felt genuinely good.",
            },
            "hard_week": {
                "type": "string",
                "description": "User's description of a week that felt hard or depleted.",
            },
            "peak_days": {
                "type": "string",
                "description": "What a peak day looks like — signals of the user's best days.",
            },
            "floor_days": {
                "type": "string",
                "description": "The floor — a day to avoid; signals of heading there.",
            },
        },
        "required": ["persona", "good_week", "hard_week", "peak_days", "floor_days"],
    },
}

SHUFFLED_NULL_SCORE_SCHEMA = {
    "name": "shuffled_null_score",
    "description": (
        "Build a null distribution of anchor similarity scores via random permutation. "
        "Randomly samples window_days-sized windows from the full log history n_permutations times "
        "and returns mean ± std per anchor. "
        "Use when data is sparse (< 3 months) to distinguish real signal from random variation."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "persona": {
                "type": "string",
                "description": "Persona slug; empty string for the real user.",
            },
            "window_days": {
                "type": "integer",
                "description": "Analysis window size in days (e.g. 7, 30).",
            },
            "n_permutations": {
                "type": "integer",
                "description": "Number of random draws (default 100).",
            },
        },
        "required": ["persona", "window_days"],
    },
}

SCORE_AGAINST_ANCHORS_SCHEMA = {
    "name": "score_against_anchors",
    "description": (
        "Score a date range's log entries against all semantic anchors. "
        "Returns cosine similarity (0–1) for each anchor — higher means current state "
        "more closely resembles that canonical experiential state. "
        "Call at the start of every Pattern Miner session to orient the analysis."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "persona": {
                "type": "string",
                "description": "Persona slug; empty string for the real user.",
            },
            "date_range": {
                "type": "object",
                "description": "Dict with 'start' and 'end' keys (ISO dates YYYY-MM-DD).",
                "properties": {
                    "start": {"type": "string", "description": "Start date YYYY-MM-DD."},
                    "end": {"type": "string", "description": "End date YYYY-MM-DD."},
                },
                "required": ["start", "end"],
            },
        },
        "required": ["persona", "date_range"],
    },
}
