"""
tools/wisdom.py — Life Wisdom Depot.

Stores persistent background knowledge about the user: standing facts and observed
patterns that stay true past today.

Separate from logs (episodic) and journal (narrative). Wisdom entries are
stable facts that accumulate over time and get surfaced proactively.

Sensitive-tier, local-only, 600 permissions enforced at write time.
Persona-scoped. Every session belongs to exactly one persona.

This is the knowledge layer: detail the tool learns about a user belongs at the level
that needs it, retrieved when relevant, not broadcast on every call. `load_profile()`
in core/orchestrator.py renders only a ~20-token *manifest* naming which domains exist;
the entries themselves arrive either by Coordinator pre-fetch or by an explicit
`read_wisdom` call at the point of use.
"""

import difflib
import json
import os
from datetime import date
from pathlib import Path

from filelock import FileLock

from core.persona import persona_data_dir

_ROOT = Path(__file__).parent.parent
_LOCK_TIMEOUT = 30  # seconds; a read-modify-write here is sub-millisecond

# ---------------------------------------------------------------------------
# The subject axis
# ---------------------------------------------------------------------------
#
# Two ORTHOGONAL fields replaced one incoherent `category` on 2026-08-15. The old list
# (patterns, seasonal, annual, preferences, health, quirks) mixed *kind* with *domain*, so
# one fact could be several at once and the axis was undecidable: a seasonal food
# preference was all three.
#
# WHY SUBJECT AND NOT AGENT. Mike's instinct was to mirror the specialist roster
# (physical_health/diet). Rejected on two arguments that carried, recorded here because the
# third and fourth were weaker and should not be cited as though they decided it:
#   1. A roster change must never become a user-data migration. `time_director` was folded
#      into the Synthesizer and `tone_profiler` added within a month; subjects do not move.
#   2. Facts are many-to-many with agents. `food` is read by physical_health (diet
#      tracking), relationships (cooking for someone) and logistics (shopping). Filing it
#      under one agent's name asserts an ownership that is not true, which is the exact
#      failure this layer exists to fix — the Synthesizer must reach it with no PH call.
# The agent coupling lives in config/modules/knowledge_domains.yaml instead, where a roster
# change edits a map rather than the data.
DOMAINS = [
    "food",          # what the user eats: standing compositions, restrictions, preferences
    "fitness",       # training, movement, exercise habits
    "health",        # symptoms, conditions, medical history, standing constraints
    "sleep",         # sleep habits, chronotype, what wrecks or restores it
    "work",          # professional domain, working style, employer context
    "money",         # spending, saving, financial structure and habits
    "relationships", # relational tendencies, social patterns, how the user connects
    "learning",      # study habits, skill acquisition, what makes something stick
    "recreation",    # hobbies, leisure, how the user recharges
    "home",          # household, admin, errands, domestic logistics
    "identity",      # values, personality profile, self-concept, disposition
]

# `seasonal` is DELIBERATELY ABSENT, having been a domain until 2026-08-15. Seasonality is a
# temporal attribute orthogonal to subject: "raspberry picking in late July" is recreation
# and "winter light sensitivity" is health, and both are seasonal. Keeping it would rebuild
# the very kind/domain collapse this re-cut removes. If real entries demand it, add a
# `recurrence` field — do not re-add the domain.

OVERFLOW_DOMAIN = "other"

# Provenance, NOT kind. An earlier draft used `kind: pattern|fact`; that asks a model a
# question it answers inconsistently mid-conversation, because "prefers oat milk" is a fact
# if the user said it and a pattern if the Diarist inferred it. "Did the user state this, or
# did we infer it?" is decidable from the model's own context. The two values carry the same
# load — they set the surfacing register, per the constitution's hypotheses-not-verdicts
# rule: `observed` is surfaced tentatively, `stated` is surfaced plainly.
# WHO MAY SET A TIER (Mike's ruling, 2026-09-03, [DB-0818-08]).
#
# These two are model-declared, and that is correct: "did the user say this, or did I
# infer it" is knowledge only the model in the turn has, and no Python caller can derive
# it. The default is the tentative one, so a writer that declares nothing understates
# rather than overstates.
#
# A THIRD TIER — `verified`, meaning Python read the value out of an artefact — MUST
# NEVER BE ADDED TO THIS TUPLE. It would land in WRITE_WISDOM_SCHEMA's enum and become a
# claim the model could assert about a check nothing performed, which is worse than
# having no tier at all. `verified` lives only where code sets it and no schema exposes
# it: `tools/crm.py`'s `_verified_source`, on the same rule as `log_interaction`'s
# `source`.
PROVENANCE = ("stated", "observed")
DEFAULT_PROVENANCE = "observed"

# What models actually say, mapped to what is stored. Modelled on `_LANGUAGE_NAMES` in
# tools/profile.py — a small explicit map, not exhaustive, extended when a real miss shows up.
#
# AN ALIAS MAP IS REQUIRED HERE AND FUZZY MATCHING IS NOT SUFFICIENT. The worked example is
# `diet` -> `food`: the two share no characters, so edit-distance scores them at zero and a
# purely fuzzy resolver would pass `diet` through as a genuinely novel subject into `other` —
# which is precisely the synonym landfill the overflow queue exists to prevent. Fuzzy
# matching below is for typos only.
_DOMAIN_ALIASES = {
    "diet": "food", "nutrition": "food", "eating": "food", "meals": "food",
    "breakfast": "food", "cooking": "food",
    "exercise": "fitness", "workout": "fitness", "workouts": "fitness",
    "training": "fitness", "gym": "fitness", "movement": "fitness",
    "medical": "health", "illness": "health", "symptoms": "health",
    "wellbeing": "health", "mental_health": "health", "physical_health": "health",
    "rest": "sleep", "insomnia": "sleep",
    "career": "work", "job": "work", "vocation": "work", "work_vocation": "work",
    "professional": "work",
    "finance": "money", "finances": "money", "budget": "money", "spending": "money",
    "saving": "money",
    "social": "relationships", "family": "relationships", "friends": "relationships",
    "people": "relationships",
    "study": "learning", "education": "learning", "skills": "learning",
    "learning_growth": "learning", "growth": "learning",
    "hobbies": "recreation", "leisure": "recreation", "recreation_hobbies": "recreation",
    "play": "recreation",
    "household": "home", "admin": "home", "chores": "home", "logistics": "home",
    "errands": "home",
    "personality": "identity", "personality_profile": "identity", "values": "identity",
    "traits": "identity", "character": "identity", "self": "identity",
}

# The six legacy categories are NOT aliased. They carry no domain signal at all — nothing
# derives `food` from `preferences` — so mapping them would be a silent wrong guess, which is
# the class of bug this whole re-cut removes. A live write naming one falls through to
# `other` with `proposed_domain` set, where the Pattern Miner sweep can see it. Historical
# entries are re-domained by the reviewed migration pass, not by this map.
_LEGACY_CATEGORIES = {"patterns", "seasonal", "annual", "preferences", "quirks"}


# Substrings that must not become a wisdom key. THIS IS THE ONE PLACE A REFUSAL IS TERMINAL,
# and the asymmetry with the domain overflow queue below is the whole design.
#
# The binding rule is that wisdom is never the SOLE home of a fact a safety flag classifies
# from. `MEDICATION_MISSED_CRITICAL` is required to classify from the stored
# `medication_profile` and "never from the agent's judgment" (physical_health.md) — that
# profile lives in agent_config.json behind `_GUARDED_KEYS`, where a write is
# confirmation-gated. A medication fact that landed here instead would sit in a store read at
# a model's discretion, and the flag would go on consulting a profile that never learned it:
# the flag stays green while the fact is on file, which is worse than not recording it.
#
# So this refuses rather than absorbing, and the return string names where the fact belongs.
# The cost is real and accepted: on the Diarist's fire-and-forget path nobody reads the
# refusal, so the wisdom write is lost. It is not the only record — the same session writes
# the content to the journal and the log — and the alternative is a safety-bearing fact whose
# only home is a discretionary read.
_RESERVED_KEY_TERMS = ("medication", "clinical", "crisis")


# ---------------------------------------------------------------------------
# The complaint guard (2026-09-04, Mike's instruction)
# ---------------------------------------------------------------------------
# THE STORE IS FOR FACTS ABOUT THE USER. A complaint is a fact about the TOOL, and the
# two are linguistically identical at the moment of capture: "the transcription keeps
# mangling my speech" is a durable-sounding observation, and an agent handed it has
# exactly one durable-storage verb to reach for. So it goes in the wrong drawer — not
# from carelessness, but because there was no other drawer.
#
# Measured 2026-09-04 on the live store: of 24 entries judged not to be facts about
# Mike, three were straight tool defects (`voice_transcription_issues`,
# `crm_update_friction`, `bulgarian_speech_to_text_issues`) already tracked properly in
# DEV_BACKLOG, and a fourth (`system_framing_preference`) was feedback about a feature's
# wording. They had been retrieved as though they were knowledge about him.
#
# WHY A CODE GUARD AND NOT AN INSTRUCTION. The same week, the intake extractor ignored an
# explicit, twice-sharpened instruction to answer `unclear`, and the fix there was also a
# code-side floor. A behaviour obtainable only by asking nicely is not a behaviour you
# have. This mirrors _RESERVED_KEY_TERMS exactly: refuse, and name the right destination
# in the refusal — a refusal that does not say where else to put it just loses the
# information, which is worse than misfiling it.
#
# DELIBERATELY NARROW. These fire on the KEY, not the value, and every term names the
# system or a malfunction rather than a life subject. A guard broad enough to catch every
# complaint would also catch real facts — "user finds mornings difficult" is not a bug
# report — and a false refusal silently discards a true fact on the Diarist's
# fire-and-forget path, where nobody reads the return string. Prefer misses to false
# positives here.
_COMPLAINT_KEY_TERMS = (
    "transcription", "mistranscri", "stt_", "_bug", "bug_", "_defect", "defect_",
    "_glitch", "glitch_", "_broken", "broken_", "_failure", "failure_", "_error",
    "error_", "friction", "not_working", "doesnt_work", "doesn_t_work",
    # Named in full rather than reaching for "issues", which would refuse `sleep_issues`
    # and other real facts about the user. Specific beats broad: this list is allowed to
    # miss, it is not allowed to eat a true fact.
    "speech_to_text", "speech_recognition", "text_to_speech",
)


def resolve_domain(raw: str) -> tuple[str, str]:
    """
    Resolve a caller-supplied domain to a stored one.

    Returns (domain, proposed_domain). `proposed_domain` is empty unless the value fell
    through to the overflow queue, in which case it carries the caller's original string so
    the entry stays reviewable rather than becoming anonymous.

    Resolution never fails and never discards. See `write_wisdom` for why.
    """
    key = (raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    if not key:
        return OVERFLOW_DOMAIN, "unspecified"
    if key in DOMAINS:
        return key, ""
    if key in _DOMAIN_ALIASES:
        return _DOMAIN_ALIASES[key], ""
    if key == OVERFLOW_DOMAIN:
        return OVERFLOW_DOMAIN, "unspecified"
    # Typos only. The cutoff is measured, not guessed: against 11 plausible typos of real
    # domains and 12 genuinely novel subjects, 0.75 resolves 11/11 typos and absorbs 0/12
    # novel ones, while 0.70 starts swallowing 'gardening' and 'politics' — a novel subject
    # absorbed into a wrong domain is invisible, where one left in the overflow queue is
    # reviewable. Do not loosen without re-running that comparison.
    candidates = list(DOMAINS) + list(_DOMAIN_ALIASES)
    close = difflib.get_close_matches(key, candidates, n=1, cutoff=0.75)
    if close and key not in _LEGACY_CATEGORIES:
        hit = close[0]
        return (_DOMAIN_ALIASES.get(hit, hit), "")
    return OVERFLOW_DOMAIN, key


def resolve_provenance(raw: str) -> str:
    """Normalise provenance, defaulting to `observed` — the safer surfacing register."""
    key = (raw or "").strip().lower()
    return key if key in PROVENANCE else DEFAULT_PROVENANCE


def _wisdom_path() -> Path:
    return persona_data_dir() / "wisdom" / "wisdom.json"


def _lock_path() -> Path:
    return _wisdom_path().parent / ".wisdom.lock"


def _wisdom_lock() -> FileLock:
    """
    Cross-process/thread lock guarding wisdom.json.

    WHY: `write_wisdom` and `merge_wisdom_entries` are read-modify-writes of a single JSON
    file, and from 2026-08-15 there are two writers *in the same exchange* — the Diarist runs
    in a fire-and-forget daemon thread (core/orchestrator.py `_dispatch_from_coordinator`)
    while the Synthesizer writes on the main path. Without this the last `json.dump` wins and
    the other entry is silently dropped. Same failure and same remedy as core/memory.py's
    `_memory_lock`, which was added after an interleaved write corrupted metadata.json.

    Scoped per persona via persona_data_dir(), so two personas never block each other.
    """
    _wisdom_path().parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(_lock_path()), timeout=_LOCK_TIMEOUT)


READ_CAP = 15


# ---------------------------------------------------------------------------
# The domain -> agent map
# ---------------------------------------------------------------------------

_DOMAIN_MAP_PATH = _ROOT / "config" / "modules" / "knowledge_domains.yaml"
_domain_map_cache: tuple[float, dict[str, list[str]]] | None = None


def domain_agent_map() -> dict[str, list[str]]:
    """
    Load config/modules/knowledge_domains.yaml — which agents read which subject domain.

    This is the ONLY coupling between subjects and the agent roster, which is the point:
    folding `time_director` into the Synthesizer edits this file, not 59 user-data entries.
    A domain absent from the file maps to no agent rather than raising — a missing line
    should degrade to "this domain reaches the Synthesizer only", never break a session.

    Cached on mtime, so an edit is picked up without a restart. The file is ~40 lines and
    this is called once per pipeline turn; the cache is politeness, not necessity.
    """
    global _domain_map_cache

    try:
        mtime = _DOMAIN_MAP_PATH.stat().st_mtime
    except OSError:
        return {}
    if _domain_map_cache and _domain_map_cache[0] == mtime:
        return _domain_map_cache[1]

    import yaml as _yaml

    try:
        raw = _yaml.safe_load(_DOMAIN_MAP_PATH.read_text()) or {}
    except Exception:
        return {}

    loaded = {
        str(domain): [str(a) for a in (agents or [])]
        for domain, agents in (raw.get("domains") or {}).items()
    }
    _domain_map_cache = (mtime, loaded)
    return loaded


def agents_for_domain(domain: str) -> list[str]:
    """Agents that read this subject domain. Empty for an unmapped or overflow domain."""
    return domain_agent_map().get(domain, [])


def _all_entries() -> list:
    wisdom_path = _wisdom_path()
    if not wisdom_path.exists():
        return []
    try:
        return json.load(open(wisdom_path))
    except json.JSONDecodeError:
        return []


def domains_present() -> list[str]:
    """
    Distinct domains that actually hold at least one entry, in DOMAINS order.

    This is what `load_profile()` renders as the manifest. It is DERIVED, never
    hand-maintained: a second hand-written list would drift from the store, which is exactly
    how `_PROMPT_EXCLUDED` came to promise an enforcement it did not provide (fixed 2026-08-15,
    `f9ffd2a`). `other` sorts last so the manifest reads as subjects first, queue second.
    """
    present = {e.get("domain") for e in _all_entries() if e.get("domain")}
    ordered = [d for d in DOMAINS if d in present]
    if OVERFLOW_DOMAIN in present:
        ordered.append(OVERFLOW_DOMAIN)
    return ordered


# Words too common to distinguish one standing fact from another. Deliberately short: this is
# not a stoplist for search, only for "does this key already name the same thing".
_COMMON_TOKENS = {
    "user", "users", "their", "them", "they", "when", "with", "from", "that", "this",
    "have", "has", "does", "daily", "usually", "tends", "prefers", "standard", "every",
    "most", "some", "about", "into", "over", "after", "before", "during", "notes", "note",
}

# A value a model wrote to itself instead of a fact. `oatmeal_formula` sat in mike's store for
# weeks reading "Oatmeal formula: [User needs to specify their formula details here]" — an
# empty entry, retrievable and surfaceable as though it were knowledge.
_PLACEHOLDER_MARKERS = ("needs to specify", "to be filled", "tbd", "todo", "placeholder",
                        "specify their", "details here")


def _tokens(text: str) -> set[str]:
    import re
    return {w for w in re.findall(r"[a-z]{4,}", (text or "").lower()) if w not in _COMMON_TOKENS}


def find_related_wisdom(value: str, domain: str) -> list[dict]:
    """
    Warn, before a write, that this domain may already hold this fact. NEVER decides anything.

    Returns [{key, value, reason}] for the caller to show a human. It does not merge, overwrite
    or rank — a near-duplicate and a genuine refinement look identical to any automatic test,
    and overwriting the refinement is the expensive direction.

    TWO SIGNALS, AND SEMANTIC SIMILARITY IS DELIBERATELY NOT ONE OF THEM. Measured 2026-08-18
    on the real case: the incoming "Standard oatmeal: 60g oats, 100g 2% milk..." scores 0.484
    against the placeholder it actually duplicated, and 0.479 against "adds 20g walnuts to
    porridge only on training days" — a distinct fact that must not be touched. The duplicate
    and the nuance are indistinguishable by embedding, so any threshold that catches one
    catches the other. `find_duplicate_wisdom`'s 0.85 default would have missed this entirely.

      1. A distinctive word in the incoming value also appears in an existing KEY. Exact token
         match, not substring — "nuts" must not match "walnuts", which is how a threshold-free
         check still avoids the nuance case above.
      2. The existing entry is a placeholder. Always worth seeing, whatever it is about.
    """
    incoming = _tokens(value)
    hits = []
    for entry in _all_entries():
        if entry.get("domain") != domain:
            continue
        key = entry.get("key", "")
        existing_value = str(entry.get("value", ""))
        reasons = []
        shared = incoming & _tokens(key.replace("_", " "))
        if shared:
            reasons.append(f"key shares '{', '.join(sorted(shared))}'")
        if any(m in existing_value.lower() for m in _PLACEHOLDER_MARKERS):
            reasons.append("existing entry looks like an unfilled placeholder")
        if reasons:
            hits.append({"key": key, "value": existing_value, "reason": "; ".join(reasons)})
    return hits


def read_wisdom(
    key: str = "",
    domains: list[str] | str = "",
    provenance: str = "",
    uncapped: bool = False,
) -> list | dict:
    """
    Read wisdom entries, by key or by subject domain.

    Args:
        key: A specific wisdom key. Returns that one entry; other arguments are ignored.
        domains: One domain or several. Adjacent body domains ("sleep", "fitness", "health",
                 "food") are commonly worth reading together, since which one a fact landed
                 in is partly the writer's judgement.
        provenance: Optionally limit to "stated" or "observed".
        uncapped: Return everything matched instead of the newest READ_CAP. For the
                  consolidation sweep only — see below.

    Returns:
        One entry dict for `key`, else a list of matching entries newest-first.
    """
    entries = _all_entries()
    if not entries:
        return {} if key else []

    if key:
        for entry in entries:
            if entry.get("key") == key:
                return entry
        return {}

    wanted: list[str] = []
    if domains:
        raw = [domains] if isinstance(domains, str) else list(domains)
        for d in raw:
            resolved, _ = resolve_domain(d)
            if resolved not in wanted:
                wanted.append(resolved)

    matched = [e for e in entries if not wanted or e.get("domain") in wanted]
    if provenance:
        want_prov = resolve_provenance(provenance)
        matched = [e for e in matched if e.get("provenance") == want_prov]

    # Newest first. The cap has to drop the OLDEST, and insertion order would drop the newest —
    # the most recently confirmed version of a standing fact is the one that matters most.
    matched.sort(key=lambda e: e.get("updated") or e.get("added") or "", reverse=True)

    # THE UNCAPPED PATH EXISTS FOR EXACTLY ONE CALLER. Consolidation has to see every entry to
    # find duplicates across the whole store; capping it would make the sweep silently partial.
    # Everything else is capped, including a bare `read_wisdom()`, because leaving read-all
    # uncapped would put the cap one omitted argument away from being bypassed.
    if uncapped:
        return matched

    if len(matched) > READ_CAP:
        head = matched[:READ_CAP]
        head.append({
            "key": "_truncated",
            "value": (
                f"{len(matched) - READ_CAP} older entries not shown "
                f"(showing the {READ_CAP} most recent). Narrow by domain to see more."
            ),
        })
        return head
    return matched


def write_wisdom(key: str, value: str, domain: str = "", provenance: str = "") -> str:
    """
    Write or update a wisdom entry.

    If an entry with the given key already exists, it is updated in place.
    Otherwise a new entry is appended.

    Args:
        key: Short identifier slug (e.g. "standard_oatmeal", "morning_creativity").
        value: The wisdom content — what to remember about this fact or pattern.
        domain: Subject area. See DOMAINS. Synonyms resolve ("diet" -> "food"); an
                unrecognised subject is kept under "other" with the original preserved.
        provenance: "stated" if the user said it, "observed" if it was inferred.
                    Defaults to "observed", the more tentative surfacing register.

    Returns:
        Confirmation string, naming the domain actually used whenever it differs from
        what was asked for.
    """
    reserved = next((t for t in _RESERVED_KEY_TERMS if t in (key or "").lower()), "")
    if reserved:
        return (
            f"Not recorded: '{key}' names {reserved}, which does not belong in standing "
            f"knowledge. This store is read at an agent's discretion, and a safety flag must "
            f"never depend on a fact that may or may not be looked up. Use "
            f"`write_agent_config` — a {reserved} fact belongs in the agent's own profile, "
            f"where the flag reads it every time."
        )

    complaint = next((t for t in _COMPLAINT_KEY_TERMS if t in (key or "").lower()), "")
    if complaint:
        return (
            f"Not recorded: '{key}' reads as a report about this system, not a standing "
            f"fact about the user — this store holds durable knowledge about them, and a "
            f"tool defect filed here is retrieved later as though it were something true "
            f"of the person. Record it with `log_quality_event` "
            f"(event_type=USER_CORRECTION), which reaches the development backlog where a "
            f"defect can actually be fixed. If this really is a fact about the user rather "
            f"than about the tool, keep the fact and rename the key without '{complaint}'."
        )

    resolved_domain, proposed = resolve_domain(domain)
    resolved_provenance = resolve_provenance(provenance)

    # A REFUSAL HERE IS NEVER TERMINAL, AND THAT IS DELIBERATE.
    #
    # The obvious design — refuse an unrecognised domain loudly, as tools/profile.py refuses an
    # unknown field — is wrong for this store, because the highest-volume writer is on a path
    # where nobody hears the refusal. The Diarist is dispatched fire-and-forget in "almost every
    # exchange" (coordinator.md), runs on Flash-Lite in a daemon thread, and its output is
    # discarded: `outputs[agent] = "dispatched (async)"`, with any exception logged as a warning
    # nobody reads. So a hard refusal there converts today's *silent misfiling* into *silent fact
    # loss*, which is strictly worse — the whole point of the store is that the user never has to
    # say something twice.
    #
    # Instead the fact always lands, and the return string reports what happened. That serves the
    # supervised caller too: `write_wisdom` updates in place by key, so a Synthesizer that reads
    # "filed under 'other'" can correct it in the same turn with an idempotent re-write.
    # profile.py's own strict schema does the same thing in the end — it refuses unknown *fields*
    # but provides `other` for "a stable fact that fits none of these".
    with _wisdom_lock():
        wisdom_path = _wisdom_path()
        wisdom_path.parent.mkdir(parents=True, exist_ok=True)

        entries: list = []
        if wisdom_path.exists():
            try:
                entries = json.load(open(wisdom_path))
            except json.JSONDecodeError:
                entries = []

        today = date.today().isoformat()
        record = {
            "domain": resolved_domain,
            "provenance": resolved_provenance,
            "value": value,
        }
        if proposed:
            record["proposed_domain"] = proposed

        action = "added"
        for entry in entries:
            if entry.get("key") == key:
                entry.update(record)
                entry["updated"] = today
                # A re-write that now resolves cleanly must clear the old marker, or the
                # overflow queue never drains and the ~15% health metric reads high forever.
                if not proposed:
                    entry.pop("proposed_domain", None)
                # Drop the dead axis. Rewriting a pre-2026-08-15 entry sets `domain` but left
                # `category` sitting beside it, so the store would carry both axes at once —
                # and the whole reason `category` was cut is that a fact filed on two axes is
                # a fact nobody can file consistently. Nothing reads it; nothing should see it.
                entry.pop("category", None)
                action = "updated"
                break
        else:
            entries.append({"key": key, **record, "added": today})

        with open(wisdom_path, "w") as f:
            json.dump(entries, f, indent=2)
        os.chmod(wisdom_path, 0o600)

    if proposed:
        return (
            f"Wisdom entry '{key}' {action} under '{OVERFLOW_DOMAIN}' — '{proposed}' is not a "
            f"known subject, so it is queued for review rather than dropped. If one of these "
            f"fits, write it again with that domain: {', '.join(DOMAINS)}."
        )
    if domain and resolved_domain != (domain or "").strip().lower():
        return f"Wisdom entry '{key}' {action} under '{resolved_domain}' (from '{domain}')."
    return f"Wisdom entry '{key}' {action} under '{resolved_domain}'."


def find_duplicate_wisdom(domain: str = "", threshold: float = 0.85) -> list[dict]:
    """
    Find potentially duplicate wisdom entries using semantic similarity.

    Embeds all entries (optionally filtered by domain) and returns groups
    of entries whose cosine similarity exceeds the threshold.

    Args:
        domain: If given, only check entries in this domain.
        threshold: Cosine similarity above which entries are flagged (default 0.85).

    Returns:
        List of duplicate groups. Each group is a dict:
        { "keys": [key1, key2, ...], "similarity": float, "values": [val1, val2, ...] }
    """
    import numpy as np

    entries = _all_entries()

    if domain:
        resolved, _ = resolve_domain(domain)
        entries = [e for e in entries if e.get("domain") == resolved]

    if len(entries) < 2:
        return []

    # core/memory.py caches this as a module-level singleton; this function used to construct
    # `SentenceTransformer("all-MiniLM-L6-v2")` inline, reloading ~80MB from disk on every call.
    # Same model, loaded once per process. (Noted as one strand of [DB-0810-11]; taken here
    # because this line had to change anyway.)
    from core.memory import _get_model

    model = _get_model()
    texts = [e.get("value", "") for e in entries]
    vecs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    groups = []
    seen = set()
    for i in range(len(entries)):
        if i in seen:
            continue
        cluster_keys = [entries[i]["key"]]
        cluster_vals = [entries[i]["value"]]
        cluster_sims = []
        for j in range(i + 1, len(entries)):
            if j in seen:
                continue
            sim = float(np.dot(vecs[i], vecs[j]))
            if sim >= threshold:
                cluster_keys.append(entries[j]["key"])
                cluster_vals.append(entries[j]["value"])
                cluster_sims.append(sim)
                seen.add(j)
        if len(cluster_keys) > 1:
            seen.add(i)
            groups.append({
                "keys": cluster_keys,
                "similarity": round(min(cluster_sims) if cluster_sims else threshold, 3),
                "values": cluster_vals,
            })

    return groups


def retire_wisdom_entries(keys: list[str], reason: str) -> str:
    """
    Archive entries that do not belong in the fact store, with the reason recorded.

    THE DIFFERENCE FROM merge_wisdom_entries, AND WHY BOTH EXIST. A merge says "this
    fact is a duplicate of that one" and leaves a `merged_into` pointer to the survivor.
    A retirement says "this was never a fact about the user at all" — a tool complaint,
    a dated observation, a content-free placeholder — and there is no survivor to point
    at. Forcing those through `merge_wisdom_entries` would write a `merged_into` naming
    an entry that does not contain the same fact, which is a lie in the archive.

    Nothing is deleted. Same destination and permissions as a merge: entries move to
    archive/wisdom/ with `retired` and `retired_reason` fields (data storage is cheap;
    fidelity loss is not — CLAUDE.md § Archive-on-merge).

    Added 2026-09-03 for `[DB-0818-06]`'s cleanup, which proposed "plain deletion" for
    eleven entries. Plain deletion is not available in this codebase by design, and the
    proposal's phrase should be read as "removed from the store", not "destroyed".

    Args:
        keys:   Keys to retire.
        reason: Why these do not belong in standing knowledge. Recorded on each entry.

    Returns:
        Confirmation string listing what was archived and what was not found.
    """
    wisdom_path = _wisdom_path()
    if not wisdom_path.exists():
        return "No wisdom file found."
    if not reason or not reason.strip():
        return "Not retired: a reason is required — an unexplained removal is unauditable."

    with _wisdom_lock():
        entries = _all_entries()
        archive_dir = persona_data_dir() / "archive" / "wisdom"
        archive_dir.mkdir(parents=True, exist_ok=True)

        today = date.today().isoformat()
        wanted = set(keys)
        archived, remaining = [], []

        for entry in entries:
            if entry.get("key") in wanted:
                entry["retired"] = today
                entry["retired_reason"] = reason.strip()
                archive_path = archive_dir / f"{entry['key']}_retired_{today}.json"
                with open(archive_path, "w") as f:
                    json.dump(entry, f, indent=2)
                os.chmod(archive_path, 0o600)
                archived.append(entry["key"])
            else:
                remaining.append(entry)

        with open(wisdom_path, "w") as f:
            json.dump(remaining, f, indent=2)
        os.chmod(wisdom_path, 0o600)

    missing = sorted(wanted - set(archived))
    out = f"Retired {len(archived)}: {', '.join(sorted(archived))}." if archived else "Retired nothing."
    if missing:
        out += f" Not found (already gone): {', '.join(missing)}."
    return out


def merge_wisdom_entries(keep_key: str, source_keys: list[str], merged_value: str = "") -> str:
    """
    Archive source entries and optionally update the kept entry.

    Source entries are moved to data/personas/{persona}/archive/wisdom/ (or
    data/archive/wisdom/ for the real user) with a 'merged_into' pointer.
    They are never deleted — data storage is cheap; fidelity loss is not.

    Args:
        keep_key:     Key of the entry to keep as the canonical version.
        source_keys:  Keys of duplicate entries to archive.
        merged_value: If given, replace the keep_key entry's value with this
                      consolidated text. Leave empty to keep it unchanged.

    Returns:
        Confirmation string listing what was archived.
    """
    wisdom_path = _wisdom_path()
    if not wisdom_path.exists():
        return "No wisdom file found."

    # Held for the whole read-modify-write, same reason as write_wisdom: the Diarist can be
    # writing from a background thread while this consolidation sweep rewrites the file.
    with _wisdom_lock():
        entries = _all_entries()

        # Resolve archive directory (parallel to wisdom/, under archive/)
        archive_dir = persona_data_dir() / "archive" / "wisdom"
        archive_dir.mkdir(parents=True, exist_ok=True)

        today = date.today().isoformat()
        archived = []
        remaining = []

        for entry in entries:
            if entry.get("key") in source_keys:
                entry["merged_into"] = keep_key
                entry["archived"] = today
                archive_path = archive_dir / f"{entry['key']}_{today}.json"
                with open(archive_path, "w") as f:
                    json.dump(entry, f, indent=2)
                os.chmod(archive_path, 0o600)
                archived.append(entry["key"])
            else:
                if entry.get("key") == keep_key and merged_value:
                    entry["value"] = merged_value
                    entry["updated"] = today
                remaining.append(entry)

        with open(wisdom_path, "w") as f:
            json.dump(remaining, f, indent=2)
        os.chmod(wisdom_path, 0o600)

    return f"Archived {len(archived)} entries → {archive_dir}: {archived}. Kept: '{keep_key}'."


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

READ_WISDOM_SCHEMA = {
    "name": "read_wisdom",
    "description": (
        "Look up standing knowledge about the user — facts and patterns that stay true past "
        "today, such as a usual breakfast, a training routine, or how they tend to work. "
        "Your context names which subjects are on file but never their contents, so call this "
        "when the conversation turns to one of them rather than guessing or asking the user to "
        "repeat something they have already told you. Read by domain; several may be given at "
        "once, and reading adjacent ones together ('sleep' with 'fitness' and 'health') is "
        "often worthwhile since a fact may have been filed under either. If nothing is "
        "recorded, ask the user rather than inventing it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "domains": {
                "type": "array",
                "items": {"type": "string", "enum": DOMAINS + [OVERFLOW_DOMAIN]},
                "description": "Subject areas to read. Omit to read across all of them.",
            },
            "provenance": {
                "type": "string",
                "enum": list(PROVENANCE),
                "description": (
                    "Optionally limit to what the user stated themselves, or to what was "
                    "inferred. Omit for both."
                ),
            },
            "key": {
                "type": "string",
                "description": (
                    "A specific entry's identifier, when you already know it. Overrides the "
                    "other arguments."
                ),
            },
        },
        "required": [],
    },
}

FIND_DUPLICATE_WISDOM_SCHEMA = {
    "name": "find_duplicate_wisdom",
    "description": (
        "Find potentially duplicate wisdom entries using semantic similarity. "
        "Run this during pattern analysis to surface near-identical entries that "
        "should be consolidated. Returns groups of entries above the similarity threshold."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "enum": DOMAINS + [OVERFLOW_DOMAIN],
                "description": "Limit search to this domain. Leave empty to check all.",
            },
            "threshold": {
                "type": "number",
                "description": "Cosine similarity threshold (0–1). Default 0.85.",
            },
        },
        "required": [],
    },
}

MERGE_WISDOM_ENTRIES_SCHEMA = {
    "name": "merge_wisdom_entries",
    "description": (
        "Archive duplicate wisdom entries and optionally update the canonical entry. "
        "Source entries are moved to the wisdom archive with a 'merged_into' pointer — "
        "they are never deleted. Call after find_duplicate_wisdom identifies a group."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "keep_key": {
                "type": "string",
                "description": "Key of the entry to keep as the canonical version.",
            },
            "source_keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Keys of the duplicate entries to archive.",
            },
            "merged_value": {
                "type": "string",
                "description": (
                    "Optional consolidated text to replace the keep_key entry's value. "
                    "Leave empty to keep the existing value unchanged."
                ),
            },
        },
        "required": ["keep_key", "source_keys"],
    },
}

WRITE_WISDOM_SCHEMA = {
    "name": "write_wisdom",
    "description": (
        "Record something about the user that will still be true next month — a standing "
        "habit, a preference, a constraint, or a pattern you have noticed. Use it so they "
        "never have to tell you the same thing twice. Examples: 'usual breakfast is 60g oats "
        "with 100g milk', 'more creative in the mornings', 'abandons non-fiction after about "
        "100 pages'. Writing an existing key again updates it, so this is also how you correct "
        "something that has changed.\n\n"
        "Do NOT record what the user is thinking about, considering, planning, interested in, "
        "or intending to change. An intention is not a habit — it is true this week and it is "
        "the thing most likely to be abandoned, so storing it as standing knowledge means "
        "being reminded of it as fact months after it stopped being true. 'Usually has eggs "
        "for breakfast' belongs here; 'wants to change up breakfast' belongs in the context "
        "tracker, and the change itself belongs here only once it is what they actually do. "
        "An event that happened belongs in a log. When unsure, do not write: a fact stated "
        "again next month is cheap, and a wrong one put back to the user as established is not."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": (
                    "Short identifier slug for this entry. Underscores, no spaces. Examples: "
                    "'standard_oatmeal', 'morning_creativity', 'winter_light_sensitivity'. "
                    "Reuse the existing key to update rather than duplicate. Medication, "
                    "clinical and crisis facts do not belong here — they go to "
                    "`write_agent_config`, where a safety check reads them every time."
                ),
            },
            "value": {
                "type": "string",
                "description": "What to remember, in one or two plain sentences.",
            },
            "domain": {
                "type": "string",
                "enum": DOMAINS,
                "description": (
                    "Which part of the user's life this belongs to. Pick by subject, not by "
                    "who asked: a breakfast composition is 'food' whether it came up in "
                    "training talk or in cooking for someone."
                ),
            },
            "provenance": {
                "type": "string",
                "enum": list(PROVENANCE),
                "description": (
                    "'stated' if the user told you this directly; 'observed' if you inferred "
                    "it from what they said or did. Defaults to 'observed'. Be accurate — it "
                    "governs how confidently this is put back to them later."
                ),
            },
        },
        "required": ["key", "value", "domain"],
    },
}
