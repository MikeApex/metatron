"""
tools/crm_sweep.py — the nightly CRM capture sweep.

Design: `archive/plans/crm_sweep_plan_2026-08-27.md` (accepted by Mike 2026-08-27,
re-reviewed 2026-08-29 before this build). Backlog item `[DB-0827-03]`.

WHY THIS EXISTS
---------------
Measured over 200 traces on 2026-08-19 and re-measured over the 200 traces of
2026-08-22..29 at the start of this build: `write_log` 232, `write_journal` 52,
**`log_interaction` 0** — down from 1. Information about people is captured constantly
into prose nobody can query while the CRM starves beside it. The gap is capture, not
schema: 22 of 23 `write_contact` fields are already exposed.

The root cause is dispatch, not instruction. `write_contact`/`log_interaction` are
granted to `relationships` alone, and that specialist runs only when a turn is *about* a
person — but people are *mentioned* in turns about everything else. So this runs off the
critical path, once a night, over a whole day at a time, where recurrence is visible.

Inline capture was REJECTED (Mike, 2026-08-19): latency, plus a mid-answer judgement on
the class of decision that had failed twice that same week.

THE BINDING CONSTRAINT: THIS PROPOSES, IT NEVER WRITES
------------------------------------------------------
The review step is the feature, not a safety wrapper around it. The extractor emits
proposals; Python validates them into an append-only ledger; the user accepts or declines
conversationally; a Python apply step executes accepted proposals **from the ledger row,
by id**. The model relays ids and never re-keys content — the `WISDOM_PROPOSAL`
transferable principle, minus the part of it that made `_file_wisdom_proposals()` write
straight into the live store with no review queue.

Three more constraints ship with it, each closing a specific recorded failure:

- **Additive only.** A non-empty field is never overwritten. Where the sweep believes a
  stored value is wrong, that is information for the digest, never a proposal.
- **No merges, ever.** `merge_contacts` is confirm-gated and reversible now
  (`fd0aed1`/`158cebe`), and the sweep still stays additive: merging is a conversational
  act behind its own gate. The Steven incident (`[DB-0822-03]`) is what that costs when
  it is wrong.
- **Ambiguity is never resolved here.** A name matching two contacts is carried into the
  proposal as a question and cannot be applied at all. Silent resolution is the exact
  failure mode of the two-Stevens incident, and this pipeline would perform that
  operation class at volume.

IDENTITY FIELDS ARE NOT FILLABLE, AND THAT IS DELIBERATE
---------------------------------------------------------
`name`, `first_name`, `last_name`, `nickname` and `referred_to_as` are excluded from
`_FILLABLE_SCALARS`/`_FILLABLE_COLLECTIONS` even when empty. Two reasons, and the second
is the load-bearing one:

1. A sweep-inferred given name is the `Kathaleen → Kathleen` shape (`[DB-0818-08]`) —
   an unsourced value landing on top of a sourced one.
2. `tools/crm.py`'s update gate raises a confirmation card for any identity-field change.
   Reached from inside `apply_crm_proposals` — itself already behind a batch confirm —
   that would nest one card inside another and return a JSON payload where a result was
   expected. Excluding the fields keeps the two gates from meeting.

`notes` is excluded for a structural reason: `write_contact`'s `_str_fields` loop
overwrites it wholesale, so it is not an accumulator and a proposal against it could only
ever destroy prior text. `tone_shape` is excluded because `tools/tone.py` assembles it in
Python from a fixed key set and it is never free model text.

THE POSTURE OF THE MODEL CALL
------------------------------
`config/agents/crm_sweep.md`, dispatched `bare=True` with `allowed_tools: []` in both
routing files — the `intake_extractor`/`accountability_judge` pattern. Its whole input is
a day of recorded conversation, so it holds no tools and sees no constitution, goals or
profile; with no schemas advertised the Gemini path omits the `tools` param entirely
(`_to_gemini_tools` returns `[]`), so it cannot emit a tool call at all.

PRIVACY TIER. This reads a whole day of conversation and journal text — Sensitive tier,
the most personal thing this system stores — and on the cloud path that goes to Vertex.
That is the path `relationships` already reads this data on, and it is valid ONLY on the
basis recorded in `ROADMAP.md` § Section 0 (Amendment 2026-08-26/28: ZDR refused,
Google's verified defaults in force, single-user expiry). No open-tier cloud call exists
anywhere in this pipeline. Nothing new is ruled on here.

A DECLINED PROPOSAL STAYS DECLINED
-----------------------------------
Every proposal lives forever in `crm/proposals.jsonl` with a content fingerprint, and the
sweep suppresses anything matching a fingerprint already accepted or declined.
Permanently, in this build: a declined proposal that returns tomorrow is how a review
queue becomes noise and then gets rubber-stamped. That is the same reasoning
`tools/confirm.py`'s `_recently_declined` applies to a single card, held for the life of
the ledger rather than 24 hours, because here the user is reviewing a batch and cannot be
asked to refuse the same row nightly.

COST (CLAUDE.md § Costs)
------------------------
Run: one Flash-Lite call per day, input one day of conversation + journal, truncated at
`_MAX_EVIDENCE_CHARS`. Ancillary: local files only — the ledger grows by a few hundred
bytes per proposal and is never pruned, which is deliberate (it is the provenance record
and the acceptance-rate metric store; a pruned ledger would silently reset the metric).
Unseen: none — nothing bills by wall-clock, no cache is created, every call lands on the
existing Vertex per-call meter.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE_PATH = _ROOT / "config" / "templates" / "crm_sweep.yaml"

# One day of conversation plus journal, capped. A prolific day must not make one
# nightly call large — the same bound tools/accountability.py puts on its evidence.
_MAX_EVIDENCE_CHARS = 60_000

# How long a parked digest keeps being offered after its first read. One pipeline
# session loads context twice — coordinator and synthesizer, seconds apart — so
# pop-on-first-read feeds the digest to the routing layer and starves the agent that
# actually speaks to the user. Copied from tools/intake.py, where the 2026-08-19 review
# caught exactly that.
_DIGEST_DELIVERY_WINDOW_MIN = 30

# Serialises ledger appends and status writes. The sweep runs in the scheduler daemon
# while apply_crm_proposals runs on a request thread; both append to the same file.
_LEDGER_LOCK = threading.Lock()

_VALID_KINDS = frozenset({"interaction", "field_fill", "new_contact"})

# Fields a proposal may fill, and only when the stored value is empty. Identity fields,
# `notes` and `tone_shape` are excluded — see the module docstring for why each.
_FILLABLE_SCALARS = frozenset({
    "primary_contact_type", "relationship_type", "relationship_quality",
    "contact_frequency_preference", "spouse_name", "education", "occupation",
    "employer", "how_met", "timezone",
})
# Appended to, never replaced. `write_contact` REPLACES a collection it is given, so the
# apply step reads the stored list and passes the merged one — verified against
# tools/crm.py's `_collection_fields` loop, which assigns rather than extends.
_FILLABLE_COLLECTIONS = frozenset({"tags", "kids_names", "important_dates"})
# Merged per key, and only into keys that are absent or empty. write_contact's own
# guards (placeholder values, the user's own email/phone) backstop every value here.
_FILLABLE_DICTS = frozenset({"contact_info"})

_FILLABLE = _FILLABLE_SCALARS | _FILLABLE_COLLECTIONS | _FILLABLE_DICTS

_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _merge(base: dict, incoming: dict) -> dict:
    """Recursive dict merge — incoming wins at the leaves. tools/intake.py's `_merge`."""
    out = dict(base)
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _template_defaults() -> dict:
    if not _TEMPLATE_PATH.exists():
        return {}
    try:
        return yaml.safe_load(_TEMPLATE_PATH.read_text()) or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[crm_sweep] template unreadable: {exc}")
        return {}


def load_config(persona: str | None = None) -> dict:
    """Persona config layered over the template.

    The template is the DEFAULT SOURCE at runtime, not merely a provisioning copy — the
    reasoning tools/intake.py and tools/mail.py both record: a template is copied once at
    persona creation and nothing propagates a later change, so a default living only
    there would reach only personas created after it.
    """
    from core.persona import persona_config_dir

    path = persona_config_dir(persona) / "crm_sweep.yaml"
    persona_cfg: dict = {}
    if path.exists():
        try:
            persona_cfg = yaml.safe_load(path.read_text()) or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[crm_sweep] {path} unreadable: {exc}")
    return _merge(_template_defaults(), persona_cfg)


# ---------------------------------------------------------------------------
# Paths and stores
# ---------------------------------------------------------------------------

def _crm_dir(persona: str | None = None) -> Path:
    from core.persona import persona_data_dir

    path = persona_data_dir(persona) / "crm"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ledger_path(persona: str | None = None) -> Path:
    return _crm_dir(persona) / "proposals.jsonl"


def _state_path(persona: str | None = None) -> Path:
    return _crm_dir(persona) / "sweep_state.json"


def _digest_state_path(persona: str | None = None) -> Path:
    return _crm_dir(persona) / "sweep_digest.json"


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[crm_sweep] {path.name} unreadable, starting empty: {exc}")
        return default


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _append_row(row: dict, persona: str | None = None) -> None:
    """One line on the append-only ledger. Status transitions are appended, never edited.

    The intake `records.jsonl` idiom. Editing a row in place would destroy the record of
    what was proposed before the user answered, which is the provenance this ledger
    exists to hold.
    """
    path = _ledger_path(persona)
    with _LEDGER_LOCK:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        try:
            path.chmod(0o600)
        except OSError:
            pass


def read_rows(persona: str | None = None) -> list[dict]:
    """Every ledger line, in order. A malformed line is skipped, never fatal."""
    path = _ledger_path(persona)
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def proposal_states(persona: str | None = None) -> dict[str, dict]:
    """Current state per proposal id: the proposal row, plus the last status applied.

    Replays the append-only ledger rather than storing a second mutable copy — one
    source of truth, and a status file that disagreed with the ledger would be worse
    than no status file.
    """
    states: dict[str, dict] = {}
    for row in read_rows(persona):
        pid = row.get("id")
        if not pid:
            continue
        if row.get("row_type") == "status":
            if pid in states:
                states[pid]["status"] = row.get("status", "pending")
                states[pid]["resolved_at"] = row.get("at", "")
                if row.get("outcome"):
                    states[pid]["outcome"] = row["outcome"]
        else:
            states[pid] = {**row, "status": "pending"}
    return states


# ---------------------------------------------------------------------------
# Fingerprints — what makes a declined proposal stay declined
# ---------------------------------------------------------------------------

def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().casefold()


def fingerprint(prop: dict) -> str:
    """Contact plus normalized fact. Deliberately NOT date-bearing for field fills.

    A field fill is the same proposal whichever day it was noticed on, so including the
    date would let a declined fill return tomorrow under a new fingerprint — the exact
    re-proposal loop this suppression exists to prevent. An interaction IS date-bearing:
    the same call on two different days is two different events.
    """
    kind = prop.get("kind", "")
    who = _norm(prop.get("name"))
    if kind == "interaction":
        return f"interaction|{who}|{prop.get('date', '')}|{_norm(prop.get('summary'))}"
    if kind == "field_fill":
        return f"field_fill|{who}|{_norm(prop.get('field'))}|{_norm(prop.get('value'))}"
    return f"new_contact|{who}"


def _spent_fingerprints(persona: str | None = None) -> set[str]:
    """Fingerprints already accepted or declined — never proposed again.

    Pending proposals are NOT spent: an unreviewed proposal re-observed on a later day is
    the same row, and re-filing it would double it in the digest.
    """
    spent: set[str] = set()
    for state in proposal_states(persona).values():
        if state.get("status") in {"accepted", "declined"} and state.get("fingerprint"):
            spent.add(state["fingerprint"])
    return spent


def _pending_fingerprints(persona: str | None = None) -> set[str]:
    return {s["fingerprint"] for s in proposal_states(persona).values()
            if s.get("status") == "pending" and s.get("fingerprint")}


# ---------------------------------------------------------------------------
# Input — the window, and the day's text
# ---------------------------------------------------------------------------

def _window_days(persona: str, as_of: date, cfg: dict) -> list[str]:
    """Days to read: since the last successful run, normally just yesterday.

    A cursor rather than a fixed "yesterday" so a stopped VM does not silently lose the
    days it was down — the read-a-window shape of tools/pattern_miner.py. Capped at
    `max_catchup_days` so a month of downtime cannot produce one enormous call.
    """
    state = _read_json(_state_path(persona), {})
    cap = int(cfg.get("max_catchup_days", 7) or 7)
    yesterday = as_of - timedelta(days=1)

    last = state.get("last_day_read")
    start = yesterday
    if last:
        try:
            start = date.fromisoformat(last) + timedelta(days=1)
        except ValueError:
            start = yesterday
    if start > yesterday:
        return []
    if (yesterday - start).days + 1 > cap:
        start = yesterday - timedelta(days=cap - 1)

    days: list[str] = []
    day = start
    while day <= yesterday:
        days.append(day.isoformat())
        day += timedelta(days=1)
    return days


def day_evidence(persona: str, day: str) -> str:
    """One day's conversation exchanges and journal entries, as tagged text.

    `seq` is carried through because the extractor is required to quote evidence against
    it — a proposal whose quote cannot be located is a proposal with no provenance, and
    the ledger row is the provenance record.
    """
    from core.persona import persona_data_dir

    data_dir = persona_data_dir(persona)
    parts: list[str] = []

    conv = data_dir / "conversations" / f"{day}.jsonl"
    if conv.exists():
        try:
            for line in conv.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                seq = rec.get("seq", "?")
                user = str(rec.get("user") or "").strip()
                resp = str(rec.get("response") or "").strip()
                if user:
                    parts.append(f"[{day} seq {seq} user] {user}")
                if resp:
                    parts.append(f"[{day} seq {seq} assistant] {resp}")
        except OSError as exc:
            logger.warning(f"[crm_sweep] {conv} unreadable: {exc}")

    jrn = data_dir / "journal" / f"{day}.json"
    if jrn.exists():
        try:
            jdata = json.loads(jrn.read_text())
        except (OSError, ValueError):
            jdata = {}
        for entry in (jdata.get("entries") or []):
            if isinstance(entry, dict):
                text = str(entry.get("text") or "").strip()
                if text:
                    parts.append(f"[{day} journal] {text}")

    return "\n".join(parts)


def _build_input(days: list[str], evidence: str, contact_names: list[str]) -> str:
    """The framing is ours; every quoted word is the user's own record.

    Known contact names are supplied so the extractor can say "this is the Sarah already
    in the record" rather than proposing a duplicate — but resolution is still done in
    Python against the real store, never taken from the model's answer.
    """
    from tools.untrusted import UNTRUSTED_CONTENT_INSTRUCTION, wrap_untrusted

    roster = ", ".join(sorted(contact_names)[:200]) or "(no contacts recorded yet)"
    return (
        f"{UNTRUSTED_CONTENT_INSTRUCTION}\n\n"
        f"Extract CRM proposals from the record below, covering "
        f"{days[0]} to {days[-1]}. Return only the JSON array described in your "
        f"instructions.\n\n"
        f"[People already in the record]\n{roster}\n\n"
        f"{wrap_untrusted(evidence, source='conversation and journal text')}"
    )


# ---------------------------------------------------------------------------
# Parse and validate — the closed schema, enforced in Python
# ---------------------------------------------------------------------------

def parse_proposals(raw: str) -> list[dict]:
    """The model's array, or an empty list. Never raises.

    The floor here is "nothing proposed", which is the safe direction: junk, prose, or an
    echoed injection payload produces no proposals rather than malformed ones. Same
    posture as tools/intake_extract.py's `_parse` and tools/accountability.py's
    `parse_verdict`, both of which collapse to their least-consequential answer.
    """
    if not isinstance(raw, str) or not raw.strip():
        return []
    match = _JSON_ARRAY_RE.search(raw)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _clean_evidence(raw) -> list[dict]:
    """Evidence quotes, bounded. Attacker-writable text going into a stored record."""
    out: list[dict] = []
    for item in (raw or [])[:3]:
        if not isinstance(item, dict):
            continue
        quote = str(item.get("quote") or "").strip()[:400]
        if quote:
            out.append({"seq": str(item.get("seq") or "")[:16], "quote": quote})
    return out


def validate(props: list[dict], contacts: list[dict], days: list[str],
             cfg: dict) -> tuple[list[dict], list[str]]:
    """Turn model output into ledger-ready proposals. Returns (proposals, rejections).

    Every check here is a check the model is not trusted to have made. Contacts are
    resolved against the real store through tools/crm.py's own `_find_by_name`, so the
    sweep and the rest of the CRM agree on what a name matches; a name matching more than
    one contact produces an UNAPPLIABLE proposal carrying the question, never a guess.
    """
    from tools.crm import _find_by_name

    window = set(days)
    out: list[dict] = []
    rejected: list[str] = []

    for prop in props:
        kind = str(prop.get("kind") or "").strip().lower()
        name = str(prop.get("name") or "").strip()
        if kind not in _VALID_KINDS:
            rejected.append(f"unknown kind {kind!r}")
            continue
        if not name:
            rejected.append(f"{kind} with no name")
            continue

        matches = _find_by_name(contacts, name)
        row: dict = {
            "kind": kind,
            "name": name,
            "evidence": _clean_evidence(prop.get("evidence")),
        }

        if kind == "new_contact":
            if matches:
                # Never resolved here. A near-match is the two-Stevens shape: presented
                # as a question, and `write_contact`'s own near-match gate backstops it
                # if the user accepts anyway.
                row["ambiguity"] = (
                    f"'{name}' resembles "
                    + ", ".join(f"{m.get('name')} ({m.get('id')})" for m in matches[:4])
                    + " — is this the same person or someone new?"
                )
        else:
            if not matches:
                rejected.append(f"{kind}: no contact matching {name!r}")
                continue
            if len(matches) > 1:
                row["ambiguity"] = (
                    f"'{name}' matches "
                    + ", ".join(f"{m.get('name')} ({m.get('id')})" for m in matches[:4])
                    + " — which one?"
                )
            else:
                row["contact_id"] = matches[0].get("id")
                row["contact_name"] = matches[0].get("name")

        if kind == "interaction":
            when = str(prop.get("date") or "").strip()
            if when not in window:
                rejected.append(f"interaction for {name}: date {when!r} outside window")
                continue
            summary = str(prop.get("summary") or "").strip()
            if not summary:
                rejected.append(f"interaction for {name}: no summary")
                continue
            row.update({
                "date": when,
                "type": str(prop.get("type") or "").strip()[:60],
                "summary": summary[:600],
                "follow_up": str(prop.get("follow_up") or "").strip()[:400],
            })

        elif kind == "field_fill":
            field = str(prop.get("field") or "").strip()
            value = prop.get("value")
            if field not in _FILLABLE:
                rejected.append(f"field_fill for {name}: {field!r} is not fillable")
                continue
            if value in (None, "", [], {}):
                rejected.append(f"field_fill for {name}: empty value for {field}")
                continue
            target = matches[0] if len(matches) == 1 else None
            if target is not None:
                stored = target.get(field)
                if field in _FILLABLE_SCALARS and str(stored or "").strip():
                    # Additive only. What the sweep thinks is wrong is information for
                    # the digest, never a proposal that would overwrite it.
                    rejected.append(
                        f"field_fill for {name}: {field} already holds a value")
                    continue
                if field in _FILLABLE_COLLECTIONS:
                    value = _merge_collection(stored, value)
                    if value is None:
                        rejected.append(
                            f"field_fill for {name}: {field} already has this entry")
                        continue
                if field in _FILLABLE_DICTS:
                    value = _merge_contact_info(stored, value)
                    if value is None:
                        rejected.append(
                            f"field_fill for {name}: {field} keys already filled")
                        continue
            row.update({"field": field, "value": value})

        row["fingerprint"] = fingerprint(row)
        out.append(row)

    cap = int(cfg.get("daily_cap", 10) or 10)
    # Recurrence-weighted: a person mentioned across several days outranks a passing
    # reference, which is the whole reason a batch that sees a window beats inline
    # capture. Ties fall back to insertion order, so a run is deterministic.
    counts: dict[str, int] = {}
    for row in out:
        counts[_norm(row["name"])] = counts.get(_norm(row["name"]), 0) + 1
    ranked = sorted(enumerate(out), key=lambda p: (-counts[_norm(p[1]["name"])], p[0]))
    kept = [row for _, row in ranked[:cap]]
    overflow = [row for _, row in ranked[cap:]]
    if overflow:
        rejected.append(f"{len(overflow)} over the daily cap of {cap}, not filed")
    return kept, rejected


def _merge_collection(stored, value) -> list | None:
    """Stored list plus what is new, or None when nothing is new.

    Returned as the WHOLE merged list because `write_contact` assigns collections rather
    than extending them — passing only the addition would delete everything else.
    """
    existing = list(stored or [])
    incoming = value if isinstance(value, list) else [value]
    seen = {json.dumps(e, sort_keys=True) if isinstance(e, dict) else _norm(e)
            for e in existing}
    added = []
    for item in incoming:
        key = json.dumps(item, sort_keys=True) if isinstance(item, dict) else _norm(item)
        if key not in seen:
            seen.add(key)
            added.append(item)
    return existing + added if added else None


def _merge_contact_info(stored, value) -> dict | None:
    """Stored dict plus keys it does not already fill, or None when it fills them all."""
    if not isinstance(value, dict):
        return None
    existing = dict(stored or {})
    added = {k: v for k, v in value.items()
             if v not in (None, "", [], {}) and not str(existing.get(k) or "").strip()}
    if not added:
        return None
    return {**existing, **added}


# ---------------------------------------------------------------------------
# The nightly run
# ---------------------------------------------------------------------------

def _extract(days: list[str], evidence: str, contact_names: list[str],
             persona: str | None) -> str:
    """One bare Flash-Lite call — the tools/intake_extract.py dispatch.

    `bare=True` (agent file only: no constitution, goals, profile or recent context) and
    `complexity="quick"`. The empty tool grant lives in the routing files, not here, so
    the model cannot emit a tool call at all. A failed call returns "" and the run files
    nothing, which is the correct direction: no proposals is a fine night.
    """
    from core.orchestrator import run_session

    try:
        return run_session(
            "crm_sweep",
            user_input=_build_input(days, evidence, contact_names),
            persona=persona,
            complexity="quick",   # Flash-Lite tier — bounded, closed schema
            bare=True,            # agent file only; no personal context, by design
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[crm_sweep] extractor call failed: {exc}")
        return ""


def sweep(persona: str | None = None, as_of: date | None = None,
          *, extractor=None) -> str:
    """
    Scheduler entry point (05:50 daily, `core/scheduler.py` `_DEFAULT_JOBS`).

    Reads the window, calls the extractor once, validates in Python, files proposals to
    the ledger and parks a digest when anything new was filed.

    Always returns a plain string and never raises — `rollup_yesterday`'s contract. In
    the scheduler daemon an exception is a log line nobody reads, and a notify dict would
    put unreviewed model output in front of the user, which is the one thing this design
    forbids.

    `extractor` is injectable for tests: a callable `(days, evidence, names) -> str`.
    """
    try:
        if persona is None:
            from core.persona import resolve_persona
            persona = resolve_persona()
        cfg = load_config(persona)
        if not cfg.get("enabled"):
            return "crm sweep disabled"

        as_of = as_of or date.today()
        days = _window_days(persona, as_of, cfg)
        if not days:
            return "crm sweep: nothing new to read"

        evidence = "\n".join(day_evidence(persona, day) for day in days).strip()
        if not evidence:
            _write_json(_state_path(persona), {
                "last_day_read": days[-1],
                "last_run": datetime.now().isoformat(timespec="seconds"),
            })
            return f"crm sweep: no record for {days[0]}..{days[-1]}"
        if len(evidence) > _MAX_EVIDENCE_CHARS:
            evidence = evidence[:_MAX_EVIDENCE_CHARS] + "\n[…record truncated]"

        from tools.crm import _load_contacts
        contacts = _load_contacts()
        names = [str(c.get("name") or "") for c in contacts if c.get("name")]

        call = extractor or (lambda d, e, n: _extract(d, e, n, persona))
        raw = call(days, evidence, names)
        proposals, rejected = validate(parse_proposals(raw), contacts, days, cfg)

        spent = _spent_fingerprints(persona)
        pending = _pending_fingerprints(persona)
        filed = 0
        now = datetime.now().isoformat(timespec="seconds")
        for row in proposals:
            if row["fingerprint"] in spent or row["fingerprint"] in pending:
                continue
            pending.add(row["fingerprint"])
            _append_row({
                **row,
                "row_type": "proposal",
                "id": f"p{now.replace(':', '').replace('-', '')[:15]}-{filed:02d}",
                "proposed_at": now,
                "window": [days[0], days[-1]],
            }, persona)
            filed += 1

        _write_json(_state_path(persona), {
            "last_day_read": days[-1],
            "last_run": now,
            "last_filed": filed,
            "last_rejected": rejected[:20],
        })

        if filed:
            _park_digest(persona)

        note = f"crm sweep: {days[0]}..{days[-1]}, {filed} proposal(s) filed"
        if rejected:
            note += f", {len(rejected)} rejected"
        return note
    except Exception as exc:  # noqa: BLE001 — daemon context, see docstring
        logger.warning(f"[crm_sweep] sweep failed: {exc}")
        return f"crm sweep: failed ({type(exc).__name__}: {exc})"


# ---------------------------------------------------------------------------
# Review — parked for the morning brief, kept quiet
# ---------------------------------------------------------------------------

def build_digest(persona: str | None = None) -> str:
    """Every pending proposal, ranked, with its id. "" when there are none.

    ALL pending rows appear, not only tonight's — an unreviewed proposal from three days
    ago is still waiting and would otherwise be unreachable. What stops this nagging is
    that the digest is only PARKED on a run that filed something new (see `sweep`), so a
    quiet night says nothing at all.
    """
    states = proposal_states(persona)
    rows = [s for s in states.values() if s.get("status") == "pending"]
    if not rows:
        return ""

    rows.sort(key=lambda r: (r.get("kind", ""), r.get("proposed_at", "")))
    lines: list[str] = []
    for row in rows:
        who = row.get("contact_name") or row.get("name")
        if row["kind"] == "interaction":
            what = f"log a {row.get('type') or 'contact'} with {who}: {row.get('summary')}"
            if row.get("follow_up"):
                what += f" (follow-up: {row['follow_up']})"
        elif row["kind"] == "field_fill":
            what = f"record {who}'s {row.get('field')} as {row.get('value')!r}"
        else:
            what = f"add {who} as a new contact"
        line = f"- [{row['id']}] {what}"
        if row.get("ambiguity"):
            line += f"\n    ASK FIRST: {row['ambiguity']}"
        lines.append(line)
    return "\n".join(lines)


def _park_digest(persona: str | None = None) -> None:
    """REPLACE, never accumulate — the file holds at most one pending digest.

    The digest is rebuilt from the ledger on every park, so nothing is lost by
    overwriting: an uncollected digest and its replacement describe the same pending
    rows. The standing cost is one small file per persona, bounded and self-replacing.
    """
    _write_json(_digest_state_path(persona), {
        "pending": True,
        "built_at": datetime.now().isoformat(timespec="seconds"),
    })


def context_block(persona: str | None = None) -> str:
    """
    The quiet review line, for the head layer's context. "" when nothing is waiting.

    DELIVERY IS CODE-SIDE, NOT A `synthesizer.md` RULE — Mike's 2026-08-22 instruction
    that this be "part of the morning brief, kept quiet", implemented the way the
    `[DB-0822-05]`..`[DB-0822-09]` finding says it must be: the agent file's
    length-versus-adherence problem is the failure mode, so an instruction that must fire
    reliably is injected beside the data rather than added to a file the model is already
    failing to follow.

    The framing line is explicit that this is ONE line unless the user engages, because
    the first message of the day must not, in his words, jump down the user's throat.
    The full list rides along so that when he does engage, the ids are already in
    context — he never re-keys content and the model never re-keys it either.

    Offered to every context load inside a 30-minute window (coordinator and synthesizer
    of one session both see it), then cleared by the first load after it closes.

    Nothing here is wrapped as untrusted: an evidence quote could be, but the digest
    carries none — only the proposal, which is this system's own structured output. The
    quotes stay in the ledger, which is a file the user reads, not a prompt.
    """
    try:
        if persona is None:
            from core.persona import resolve_persona
            persona = resolve_persona()
        cfg = load_config(persona)
        if not cfg.get("enabled"):
            return ""

        state = _read_json(_digest_state_path(persona), {})
        if not state.get("pending"):
            return ""

        now = datetime.now()
        started = state.get("delivery_started")
        if started is None:
            state["delivery_started"] = now.isoformat(timespec="seconds")
            _write_json(_digest_state_path(persona), state)
        else:
            try:
                minutes = (now - datetime.fromisoformat(started)).total_seconds() / 60
            except (TypeError, ValueError):
                minutes = float("inf")
            if minutes > _DIGEST_DELIVERY_WINDOW_MIN:
                _write_json(_digest_state_path(persona), {
                    "pending": False,
                    "delivered_at": now.isoformat(timespec="seconds"),
                })
                return ""

        body = build_digest(persona)
        if not body:
            return ""
        count = len([ln for ln in body.splitlines() if ln.startswith("- [")])
        return (
            f"[Contact updates awaiting review — {count} waiting. Mention this ONCE, in "
            f"one short low-key line, and only if the conversation has room for it. Do "
            f"NOT read the list out unless the user asks for it. If the user accepts or "
            f"declines any of them, that turn belongs to the relationships specialist: "
            f"pass the ids on verbatim and let it apply them. Never re-type what a "
            f"suggestion says — the stored version is what gets written.]\n" + body
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[crm_sweep] context block failed: {exc}")
        return ""


# ---------------------------------------------------------------------------
# Apply — from the ledger, by id
# ---------------------------------------------------------------------------

def _describe(row: dict) -> str:
    who = row.get("contact_name") or row.get("name")
    if row.get("kind") == "interaction":
        return f"log a {row.get('type') or 'contact'} with {who} on {row.get('date')}"
    if row.get("kind") == "field_fill":
        return f"record {who}'s {row.get('field')} as {row.get('value')!r}"
    return f"add {who} as a new contact"


def _apply_one(row: dict) -> tuple[bool, str]:
    """Execute one accepted proposal from its ledger row. Returns (ok, detail).

    The row is replayed VERBATIM — `tools/confirm.py`'s replay principle. The model
    supplied an id and nothing else, so what is written is what the user read and
    approved, not a re-statement of it that drifted on the way through.
    """
    from tools.crm import log_interaction, write_contact

    kind = row.get("kind")
    if kind == "interaction":
        result = log_interaction(
            contact_id=row.get("contact_id", ""),
            interaction_type=row.get("type", ""),
            summary=row.get("summary", ""),
            follow_up=row.get("follow_up", ""),
            date=row.get("date", ""),
            source="sweep",
        )
    elif kind == "field_fill":
        result = write_contact(
            name=row.get("contact_name") or row.get("name"),
            contact_id=row.get("contact_id", ""),
            **{row["field"]: row["value"]},
        )
    elif kind == "new_contact":
        result = write_contact(name=row.get("name"))
    else:
        return False, f"unknown kind {kind!r}"

    text = result if isinstance(result, str) else json.dumps(result)
    if text.strip().startswith("{") and "PENDING_CONFIRMATION" in text:
        # write_contact raised its OWN card — a near-match on create. Reported as what it
        # is rather than as an application: the proposal stays pending, and the user
        # answers the more specific question the CRM asked.
        return False, "needs its own confirmation (near-match on an existing contact)"
    if text.startswith("Error"):
        return False, text
    return True, text.splitlines()[0]


def apply_crm_proposals(accept_ids: list[str] | None = None,
                        decline_ids: list[str] | None = None,
                        confirm_token: str = "") -> str:
    """
    Apply the user's answers to parked CRM proposals, by id.

    THE MODEL IS NOT IN THE WRITE PATH. It maps the user's words to ids; every value
    written comes from the ledger row the user reviewed. That is the whole reason the
    sweep is allowed to read a day of personal conversation with a small model: nothing
    it produced reaches the store without a human sentence in between.

    One batch confirmation, not one per item (Mike, 2026-08-22) — `apply_confirm: true`
    in the persona's crm_sweep.yaml, flippable conversationally through the existing
    gated `write_config` path if the tap becomes a nuisance.

    A proposal carrying an `ambiguity` question CANNOT be accepted. The sweep never
    resolves a near-match and neither does this; the user answers the question and the
    ordinary conversational CRM tools do the write, where the near-match gates apply.
    Declining an ambiguous proposal IS allowed — refusing is never ambiguous.
    """
    from tools.confirm import consume, request

    accept_ids = [str(i).strip() for i in (accept_ids or []) if str(i).strip()]
    decline_ids = [str(i).strip() for i in (decline_ids or []) if str(i).strip()]
    if not accept_ids and not decline_ids:
        return "Error: give at least one proposal id to accept or decline."

    persona = None
    states = proposal_states(persona)

    unknown = [i for i in accept_ids + decline_ids if i not in states]
    if unknown:
        return (f"Error: no proposal with id {', '.join(unknown)}. "
                f"Read the pending list again rather than guessing an id.")
    settled = [i for i in accept_ids + decline_ids
               if states[i].get("status") != "pending"]
    if settled:
        return (f"Error: {', '.join(settled)} has already been answered "
                f"— nothing was changed.")
    blocked = [i for i in accept_ids if states[i].get("ambiguity")]
    if blocked:
        return ("Error: " + "; ".join(
            f"{i} — {states[i]['ambiguity']}" for i in blocked)
            + ". Ask the user, then make the change directly; it cannot be accepted "
              "from the list while it is unclear who it is about.")

    cfg = load_config(persona)
    _gate_args = {"accept_ids": accept_ids, "decline_ids": decline_ids}
    if cfg.get("apply_confirm", True) and accept_ids:
        if confirm_token:
            ok, reason = consume(confirm_token, "apply_crm_proposals", _gate_args)
            if not ok:
                return f"Error: not applied. {reason}"
        else:
            description = ("Apply these contact updates?\n\n"
                           + "\n".join(f"  • {_describe(states[i])}" for i in accept_ids))
            if decline_ids:
                description += (f"\n\nAnd discard {len(decline_ids)} other "
                                f"suggestion(s), permanently.")
            return json.dumps(request("apply_crm_proposals", _gate_args,
                                      description=description))

    now = datetime.now().isoformat(timespec="seconds")
    applied, failed = [], []
    for pid in accept_ids:
        row = states[pid]
        try:
            ok, detail = _apply_one(row)
        except Exception as exc:  # noqa: BLE001 — one bad row must not lose the batch
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        if ok:
            applied.append(pid)
            _append_row({"row_type": "status", "id": pid, "status": "accepted",
                         "fingerprint": row.get("fingerprint"), "at": now,
                         "outcome": detail}, persona)
        else:
            failed.append((pid, detail))
            # NOT marked accepted — it did not happen, and a ledger that said otherwise
            # would suppress the proposal forever on a write that never landed.
            _append_row({"row_type": "status", "id": pid, "status": "pending",
                         "fingerprint": row.get("fingerprint"), "at": now,
                         "outcome": f"not applied: {detail}"}, persona)

    for pid in decline_ids:
        _append_row({"row_type": "status", "id": pid, "status": "declined",
                     "fingerprint": states[pid].get("fingerprint"), "at": now},
                    persona)

    parts = []
    if applied:
        parts.append(f"{len(applied)} applied")
    if decline_ids:
        parts.append(f"{len(decline_ids)} discarded")
    if failed:
        parts.append("could not be applied: "
                     + "; ".join(f"{pid} ({why})" for pid, why in failed))
    return "; ".join(parts) or "nothing to do"


APPLY_CRM_PROPOSALS_SCHEMA = {
    "name": "apply_crm_proposals",
    "description": (
        "Apply the user's decision on parked contact-update suggestions, by id. Pass the "
        "ids they accepted and the ids they turned down. Never re-type the content of a "
        "suggestion — the stored version is what gets written. A declined suggestion is "
        "gone for good and will not be raised again."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "accept_ids": {
                "type": "array", "items": {"type": "string"},
                "description": "Ids of suggestions the user accepted.",
            },
            "decline_ids": {
                "type": "array", "items": {"type": "string"},
                "description": "Ids the user turned down. Permanent.",
            },
            "confirm_token": {
                "type": "string",
                "description": "Token from the PENDING_CONFIRMATION step.",
            },
        },
        "required": [],
    },
}


# manual: python3 -m tools.crm_sweep --persona NAME [--digest]
# Run as a MODULE from the repo root, not as a file path — `python3 tools/crm_sweep.py`
# puts tools/ on sys.path instead of the root and dies on `import core`. Same invocation
# as tools/obligations.py, tools/accountability.py and tools/calendar_reconcile.py.
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="CRM sweep — run, or show what is pending.")
    ap.add_argument("--persona", default=None)
    ap.add_argument("--digest", action="store_true", help="show pending proposals only")
    args = ap.parse_args()

    if args.digest:
        print(build_digest(args.persona) or "(nothing pending)")
    else:
        print(sweep(args.persona))
