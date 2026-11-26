"""
tools/data_objects.py — the user's logs and lists: one registry over every store.

archive/plans/custom_logs_and_places_plan_2026-11-21.md § 3.1–3.5 (phase 1). A "data object" is
anything the user keeps — a heart log, the films they've watched, a list of gift ideas — and
also every store that already exists (contacts, tasks, the daily log …), registered rather than
moved (R27). Each object has one entry in a per-user registry:

    data/personas/{p}/data_objects.json      ← OUTSIDE archive/ (review finding 10)

because every filename inside archive/ is an archive category, and anything that reads or
writes a category would otherwise reach the registry too.

WHAT LIVES WHERE
    store: archive    entries live in archive/{id}.json, written here (identity rules below)
    any other store   entries live in that store; reads and writes are HANDED to its own tool,
                      which keeps its own protections (contacts' placeholder refusal, the
                      medication guard, calendar wrapping) — this module adds none and
                      removes none.

IDENTITY (R20, § 3.2) — for store: archive
    thing               a repeat write of the same title/name/text/description merges (today's
                        write_archive behaviour, kept for every category — review finding 1)
    occurrence          every write is an entry; nothing merges (the cardiac log)
    thing+occurrences   one row per thing; an EXPLICIT occurrence write ("watched it again")
                        appends to that row's `occurrences`. Never inferred from a repeat.

NOTHING IS DELETED (R5, archive-on-merge). An amended entry keeps `previous`; an archived object
leaves the lists and stays readable by name; a merged object points at where its entries went
(`merged_into`) and its own file is left as it was.

THE READ RULE (§ 3.3, review finding 7, verify finding NEW 1)
    A store with its own model-callable read tool is served only to an agent that already
    holds that tool — checked here against the allowlist, independent of
    METATRON_TOOL_PERMISSIONS. A store with none (every archive object, places, day shape) is
    served to the object's `relevant_agents` and the standing readers, and nobody else. An
    unknown caller is refused: a model call is always bound to its agent (core/trace.py), so
    an unbound read is code — and code reads through `fetch()` naming the agent it serves.
    Location-tier stores never return a coordinate.

    The standing readers are the Synthesizer (it answers "read me the log" — Mike, decision 2,
    2026-11-22), the Diarist (the writer of every object) and Pattern Miner (R16 — its grant
    is phase 5, so until then it is listed and cannot call).

THE PENDING MARKER AND VERIFICATION (§ 3.4, review finding 3)
    The Diarist writes after the reply. A marker per write says "an entry for this object is
    on its way"; a write to that object — through write_data_object OR write_archive into the
    object's own category (Mike, decision 1) — clears it. When the Diarist's thread ends, code
    checks; one retry runs on the reasoning tier; a second failure is a push, a quality event
    and a note on the next reply. A marker that outlives `pending_expiry_seconds` (the process
    restarted mid-write) raises the same — never silence.

A8: `manifest_for()` is reached from core/orchestrator.py `_data_object_manifest()`, which moves
to core/config.py with `_knowledge_manifest()`; the resolver stays in the pipeline.
"""
from __future__ import annotations

import difflib
import fcntl
import json
import logging
import os
import re
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from core.persona import persona_data_dir, persona_scope, resolve_persona, current_persona
from tools.record_rules import RELATIVE_REFERENCES

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.parent
_TEMPLATE_DIR = _ROOT / "config" / "data_objects"
_LIMITS_PATH = _ROOT / "config" / "modules" / "data_objects.yaml"

STORES = ("archive", "wisdom", "contacts", "places", "day_shape", "tasks", "profile",
          "agent_config", "log", "goals", "calendar", "medication")
IDENTITIES = ("thing", "occurrence", "thing+occurrences")
STATUSES = ("active", "archived", "private")

STANDING_READERS = frozenset({"synthesizer", "diarist", "pattern_miner"})
HEALTH_AGENTS = ("physical_health", "mental_wellbeing")
# The agents relevance tagging chooses among (R26). The standing readers are added by rule,
# never by the model.
TAGGABLE_AGENTS = ("physical_health", "mental_wellbeing", "relationships", "finance",
                   "work_vocation", "learning_growth", "recreation_hobbies", "logistics")

# Each store's own read and write tools. A store absent from NATIVE_READ has no
# model-callable read tool and is served by relevance (the read rule above).
NATIVE_READ = {
    "wisdom": "read_wisdom", "contacts": "list_contacts", "tasks": "list_tasks",
    "profile": "read_profile", "agent_config": "read_agent_config", "log": "read_log",
    "goals": "read_goals", "calendar": "read_calendar",
}
NATIVE_WRITE = {
    "wisdom": "write_wisdom", "contacts": "write_contact", "tasks": "open_task",
    "profile": "write_profile", "agent_config": "write_agent_config", "log": "write_log",
    "calendar": "write_calendar_event", "day_shape": "set_day_shape",
}
LOCATION_STORES = frozenset({"places"})
# Stores that are a VIEW computed from other records: nothing is written into them, by any door
# (sweep ruling D11 — "medication taken today" reads the ledger's dose habits; a second record of
# a dose could disagree with the first, in a hard-fail domain). Keyed on the store, which only
# code sets, never on a field a registry copy could lose. Absent from NATIVE_READ, so the read
# rule is relevance: `class: health` adds both health agents to the standing readers.
READ_ONLY_STORES = frozenset({"medication"})

_DEFAULT_LIMITS = {
    "manifest_max_objects": 60,
    "manifest_includes_native_stores": False,
    "read_max_entries": 200,
    "pending_expiry_seconds": 120,
    "pending_wait_seconds": 8,
    "close_match_ratio": 0.85,
    "log_read_default_days": 14,
    "log_read_max_days": 92,
}

# Tests set this False so tagging runs inline against a stub.
TAG_IN_BACKGROUND = True


# ---------------------------------------------------------------------------
# Seams — each one a single place a test stubs a live dependency
# ---------------------------------------------------------------------------

def _user_dir() -> Path:
    return persona_data_dir()


def _caller() -> str:
    """The agent whose tool call this is, from the request trace; "" when none is bound.
    Read, never trusted from an argument a model fills in (tools/goals.py precedent)."""
    try:
        from core.trace import get_current_agent
        rec = get_current_agent()
        return str(getattr(rec, "agent", "") or "")
    except Exception:  # noqa: BLE001
        return ""


def _allowed_tools(agent: str) -> list[str] | None:
    from core.router import get_allowed_tools
    try:
        return get_allowed_tools(agent)
    except Exception:  # noqa: BLE001
        return None


def _call_tagger(payload: str, persona: str) -> str:
    from core.orchestrator import run_session
    return run_session("data_object_tagger", user_input=payload, persona=persona,
                       bare=True, proactive=True)


def _send_push(title: str, body: str, persona: str) -> None:
    from core.push import send_push
    send_push(title, body, persona=persona)


def _quality_event(**kw) -> None:
    from tools.logger import write_quality_event
    write_quality_event(**kw)


def limits() -> dict:
    """config/modules/data_objects.yaml over the defaults. Never raises."""
    out = dict(_DEFAULT_LIMITS)
    try:
        import yaml
        if _LIMITS_PATH.exists():
            out.update(yaml.safe_load(_LIMITS_PATH.read_text()) or {})
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[data_objects] limits unreadable, using defaults: {exc}")
    return out


# ---------------------------------------------------------------------------
# Files and the lock
# ---------------------------------------------------------------------------

def _registry_path() -> Path:
    return _user_dir() / "data_objects.json"


def _pending_path() -> Path:
    return _user_dir() / "data_object_pending.json"


def _archive_file(category: str) -> Path:
    from tools.diarist import _archive_dir
    return _archive_dir() / f"{category}.json"


_LOCK = threading.RLock()
_FLOCKS: dict[str, list] = {}


@contextmanager
def _locked():
    """`_LOCK`, plus an fcntl lock beside the registry — reentrant within a thread,
    exclusive across threads and processes. tools/obligations.py `_store_lock` pattern."""
    with _LOCK:
        path = _registry_path()
        key = str(path)
        held = _FLOCKS.get(key)
        if held:
            held[1] += 1
            try:
                yield
            finally:
                held[1] -= 1
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(path.with_name(path.name + ".lock"), "a+")
        try:
            fcntl.flock(fh, fcntl.LOCK_EX)
            _FLOCKS[key] = [fh, 1]
            try:
                yield
            finally:
                _FLOCKS.pop(key, None)
                fcntl.flock(fh, fcntl.LOCK_UN)
        finally:
            fh.close()


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(f"[data_objects] {path.name} unreadable: {exc}")
        return default


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------

def _templates() -> list[dict]:
    """config/data_objects/*.yaml — present by default for every user, empty (R6)."""
    out: list[dict] = []
    try:
        import yaml
        for f in sorted(_TEMPLATE_DIR.glob("*.yaml")):
            t = yaml.safe_load(f.read_text()) or {}
            if not t.get("id"):
                continue
            out.append(_complete({**t, "origin": f"template:{t['id']}", "created": ""}))
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[data_objects] templates unreadable: {exc}")
    return out


def _complete(o: dict) -> dict:
    o = dict(o)
    o.setdefault("name", o.get("id", ""))
    o["aliases"] = list(o.get("aliases") or [])
    o.setdefault("description", "")
    o.setdefault("store", "archive")
    o.setdefault("identity", "thing")
    o["fields"] = dict(o.get("fields") or {})
    o["fields"].setdefault("notes", "text")           # R2: notes always present
    o["relevant_agents"] = sorted(set(o.get("relevant_agents") or []))
    o.setdefault("class", None)
    o.setdefault("status", "active")
    o.setdefault("merged_into", None)
    o.setdefault("origin", "asked")
    o.setdefault("created", date.today().isoformat())
    return o


# Keys that are POLICY, not the user's description of their log: who may write it and which
# fields are reconciled by provenance. Config owns policy (D3), so a template's value wins over
# a registry copy made before the key existed — `mike`'s `places` entry was registered from the
# existing category on 11-22, before places had a writer rule (phase 3).
_POLICY_KEYS = ("writer", "guarded")


def _stored() -> list[dict]:
    data = _read_json(_registry_path(), {"objects": []})
    objs = [_complete(o) for o in (data.get("objects") or []) if isinstance(o, dict)]
    templates = {t["id"]: t for t in _templates()}
    for o in objs:
        t = templates.get(o["id"])
        if t:
            for k in _POLICY_KEYS:
                if k in t:
                    o[k] = t[k]
    return objs


def code_kept(o: dict | None) -> bool:
    """A log whose entries only code writes (`writer: code` in its template) — places, since
    phase 3: one writer per kind of change, so a verdict cannot be set by three agents at
    once (Mike, 2026-11-25, choice 5). Every model door refuses it; code passes `by_code`."""
    return bool(o) and o.get("writer") == "code"


def code_kept_refusal(o: dict) -> str:
    return (f"Not recorded: {o['name']} is kept by code from what the user says in "
            f"conversation — nothing needs writing here.")


def _save(objs: list[dict]) -> None:
    _write_json(_registry_path(), {"version": 1, "objects": objs})


def objects() -> list[dict]:
    """Every registered object, templates included (a template not yet written to is listed
    from its config file; the first write or amend copies it into the registry)."""
    stored = _stored()
    ids = {o["id"] for o in stored}
    return stored + [t for t in _templates() if t["id"] not in ids]


def _materialise(obj_id: str, objs: list[dict]) -> tuple[list[dict], dict]:
    """The stored list with `obj_id` in it (copying a template in if needed), and the entry."""
    for o in objs:
        if o["id"] == obj_id:
            return objs, o
    for t in _templates():
        if t["id"] == obj_id:
            objs.append(t)
            return objs, t
    raise KeyError(obj_id)


def get(obj_id: str) -> dict | None:
    for o in objects():
        if o["id"] == obj_id:
            return o
    return None


_GENERIC = {"log", "list", "the", "my", "a", "an", "of", "tracker", "record", "records"}


def _norm(s: str) -> str:
    s = str(s or "").casefold().replace("_", " ").replace("-", " ")
    s = re.sub(r"[^\w\s]", "", s)
    return " ".join(s.split())


def _core(s: str) -> str:
    """The distinguishing words: generic ones dropped, plurals folded."""
    toks = [t[:-1] if len(t) > 3 and t.endswith("s") else t
            for t in _norm(s).split() if t not in _GENERIC]
    return " ".join(toks) or _norm(s)


def _names(o: dict) -> list[str]:
    return [o["id"], o.get("name", ""), *o.get("aliases", [])]


def _follow(o: dict | None, objs: list[dict]) -> dict | None:
    seen = set()
    while o and o.get("merged_into") and o["id"] not in seen:
        seen.add(o["id"])
        nxt = next((x for x in objs if x["id"] == o["merged_into"]), None)
        if nxt is None:
            break
        o = nxt
    return o


def resolve(name: str, follow: bool = True) -> dict | None:
    """The object `name` means — id, name or alias, exact or by its distinguishing words
    (R18). Merged objects resolve to where their entries went."""
    if not name:
        return None
    objs = objects()
    n, c = _norm(name), _core(name)
    hit = next((o for o in objs if any(_norm(x) == n for x in _names(o))), None)
    if hit is None:
        hit = next((o for o in objs if any(_core(x) == c for x in _names(o))), None)
    return _follow(hit, objs) if follow else hit


def close_match(name: str) -> dict | None:
    """An existing object `name` is near enough to that creating it would make a duplicate."""
    hit = resolve(name)
    if hit:
        return hit
    ratio = float(limits()["close_match_ratio"])
    c = _core(name)
    best, best_r = None, 0.0
    for o in objects():
        for x in _names(o):
            r = difflib.SequenceMatcher(None, c, _core(x)).ratio()
            if r > best_r:
                best, best_r = o, r
    return _follow(best, objects()) if best is not None and best_r >= ratio else None


def public(o: dict) -> dict:
    keys = ("id", "name", "aliases", "description", "store", "identity", "fields", "class",
            "status", "merged_into")
    return {k: o.get(k) for k in keys}


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", _norm(name)).strip("_")[:40].strip("_")
    return s or "log"


def create_object(name: str, description: str = "", fields: dict | None = None,
                  store: str = "archive", identity: str = "occurrence",
                  class_: str | None = None, aliases: list[str] | None = None,
                  relevant_agents: list[str] | None = None, origin: str = "asked",
                  object_id: str = "", tag: bool = True,
                  persona: str | None = None) -> dict:
    """
    Create an object, or return the existing one it closely matches (R18).

    A plain function on purpose: the Coordinator's resolver calls it for "start a log of …",
    the seed script calls it, and phase 2's confirmation card (`POST /confirm`) will call it
    with `origin="noticed"` — none of them through a model.

    Returns {"created": True, "object": …} or {"created": False, "match": …}, or
    {"created": False, "error": …}.
    """
    name = str(name or "").strip()
    if not name:
        return {"created": False, "error": "a log needs a name"}
    if name.islower():
        name = name[0].upper() + name[1:]        # "migraines" from a model → "Migraines"
    if store not in STORES:
        return {"created": False, "error": f"unknown store {store!r}"}
    if identity not in IDENTITIES:
        identity = "occurrence"
    with _locked():
        match = close_match(name)
        if match is not None:
            return {"created": False, "match": public(match)}
        objs = _stored()
        taken = {o["id"] for o in objects()}
        oid = (object_id or _slug(name)).lstrip("_") or "log"
        base, i = oid, 2
        while oid in taken:
            oid, i = f"{base}_{i}", i + 1
        rel = set(relevant_agents or [])
        if class_ == "health":
            rel |= set(HEALTH_AGENTS)
        obj = _complete({
            "id": oid, "name": name, "aliases": aliases or [], "description": description,
            "store": store, "identity": identity, "fields": fields or {},
            "relevant_agents": sorted(rel), "class": class_, "origin": origin,
        })
        objs.append(obj)
        _save(objs)
    if tag:
        _tag_later(oid, persona)
    return {"created": True, "object": public(obj)}


def register_store(store: str, name: str = "", description: str = "",
                   aliases: list[str] | None = None, **extra) -> dict:
    """Register an existing store (R27) — entries stay where they are. Its origin is
    "existing", never "asked": phase 2 counts logs by origin, and nobody asked for these."""
    extra.setdefault("origin", "existing")
    return create_object(name or store, description=description, store=store,
                         identity="thing", aliases=aliases, object_id=store,
                         tag=False, **extra)


def repair_store_origins() -> list[str]:
    """Stores registered before 2026-11-22 carry origin "asked" (register_store's old
    default). Re-mark them "existing". Idempotent; returns the ids it changed."""
    changed = []
    with _locked():
        objs = _stored()
        for o in objs:
            if (o.get("store") != "archive" and o.get("id") == o.get("store")
                    and o.get("origin") == "asked"):
                o["origin"] = "existing"
                changed.append(o["id"])
        if changed:
            _save(objs)
    return changed


# ---------------------------------------------------------------------------
# Relevance tagging at creation (R26) — one bulk-tier call, never in the reply's path
# ---------------------------------------------------------------------------

def agent_remits() -> dict[str, str]:
    """Each taggable agent's one-line remit — the italic subtitle at the top of its agent
    file, so nothing is hand-copied (plan § 3.5)."""
    out: dict[str, str] = {}
    for a in TAGGABLE_AGENTS:
        try:
            for line in (_ROOT / "config" / "agents" / f"{a}.md").read_text().splitlines()[:8]:
                m = re.match(r"^\*(.+)\*\s*$", line.strip())
                if m:
                    out[a] = m.group(1).strip()
                    break
        except OSError:
            continue
    return out


def tag_relevance(obj_id: str, persona: str | None = None) -> list[str]:
    """Ask the tagger which agents an object concerns, and add them. Never raises; on any
    failure the object keeps the agents it was created with (its class rule included)."""
    try:
        obj = get(obj_id)
        if obj is None:
            return []
        payload = json.dumps({
            "object": {"name": obj["name"], "description": obj["description"],
                       "fields": sorted(obj["fields"])},
            "agents": agent_remits(),
        }, ensure_ascii=False)
        raw = _call_tagger(payload, resolve_persona(persona))
        m = re.search(r"\[.*?\]", raw or "", re.DOTALL)
        chosen = json.loads(m.group(0)) if m else []
        chosen = [a for a in chosen if isinstance(a, str) and a in TAGGABLE_AGENTS]
        with _locked():
            objs = _stored()
            objs, o = _materialise(obj_id, objs)
            rel = set(o["relevant_agents"]) | set(chosen)
            if o.get("class") == "health":
                rel |= set(HEALTH_AGENTS)
            o["relevant_agents"] = sorted(rel)
            _save(objs)
        return o["relevant_agents"]
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[data_objects] relevance tagging failed for {obj_id}: {exc}")
        return []


def _tag_later(obj_id: str, persona: str | None) -> None:
    p = persona or current_persona()
    if not TAG_IN_BACKGROUND:
        tag_relevance(obj_id, p)
        return

    def _run():
        try:
            with persona_scope(resolve_persona(p)):
                tag_relevance(obj_id, p)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[data_objects] background tagging failed: {exc}")
    threading.Thread(target=_run, daemon=True).start()


# ---------------------------------------------------------------------------
# The read rule
# ---------------------------------------------------------------------------

def readers(o: dict) -> set[str]:
    rel = set(o.get("relevant_agents") or []) | STANDING_READERS
    if o.get("class") == "health":
        rel |= set(HEALTH_AGENTS)
    return rel


def may_read(agent: str, o: dict) -> tuple[bool, str]:
    if not agent:
        return False, "no calling agent is bound to this read"
    store = o.get("store", "archive")
    if store in NATIVE_READ:
        tool = NATIVE_READ[store]
        allowed = _allowed_tools(agent)
        if allowed is not None and tool in allowed:
            return True, ""
        return False, (f"the {store} store is read only by agents holding {tool}, "
                       f"which this agent does not")
    if agent in readers(o):
        return True, ""
    return False, f"'{o.get('name')}' is not one of this agent's logs"


def _holds(agent: str, tool: str) -> bool:
    allowed = _allowed_tools(agent)
    return allowed is not None and tool in allowed


def read_only(o: dict | None) -> bool:
    """Is this object a computed view that takes no entries and no changes?"""
    return bool(o) and o.get("store") in READ_ONLY_STORES


def read_only_refusal(o: dict, verb: str = "Not recorded") -> str:
    # Its aliases ("medications", "meds taken") also catch "add X to my medications", which is
    # not a dose at all but a change to WHICH medicines the user takes — so the refusal says
    # where that goes (review 2026-11-23, item 9). The aliases stay: they are what stops a
    # second "medications" list being started beside the view, a second record of each dose.
    return (f"{verb}: {o.get('name')} is read-only — it shows the doses marked done on the "
            f"user's medication habits and keeps nothing of its own. A dose is recorded by "
            f"marking its habit done in the task ledger. Adding, removing or changing a "
            f"medication the user takes is a change to their medication profile, which "
            f"Physical Health keeps — with the user's approval.")


_COORD_KEY = re.compile(r"^(lat|lng|lon|long|latitude|longitude|coords?|coordinates|geo|"
                        r"latlng|lat_lng|latlon|lat_lon|lnglat|location_lat|location_lng|"
                        r"point|position)$", re.IGNORECASE)


def _is_location(o: dict) -> bool:
    """Location tier by store or by id: the existing places category is registered as
    `store: archive` by the seed, so the store alone would miss it."""
    return o.get("store") in LOCATION_STORES or o.get("id") in LOCATION_STORES


def _strip_coordinates(value: Any) -> Any:
    """Location tier: names, counts, times and computed distances only — never a coordinate."""
    if isinstance(value, dict):
        return {k: _strip_coordinates(v) for k, v in value.items() if not _COORD_KEY.match(str(k))}
    if isinstance(value, list):
        return [_strip_coordinates(v) for v in value]
    return value


# ---------------------------------------------------------------------------
# Archive-store entries
# ---------------------------------------------------------------------------

def _rows(obj_id: str) -> list:
    data = _read_json(_archive_file(obj_id), [])
    return data if isinstance(data, list) else []


def _identity_key(d: dict) -> str:
    """tools/diarist.py write_archive's natural key — kept identical, so a repeat means the
    same thing through either door."""
    for k in ("title", "name", "text", "description"):
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return f"{k}:{v.strip().casefold()}"
    return ""


_SOURCE_RANK = {"derived": 1, "stated": 2}


def _source_of(item: dict, field: str) -> str:
    s = str(item.get(f"{field}_source") or "").strip().lower()
    if s in _SOURCE_RANK:
        return s
    return "derived" if item.get("derived") else "stated"


def _reconcile_guarded(o: dict, row: dict, item: dict, now: str) -> dict:
    """Provenance reconciliation for a template's `guarded` fields, at the moment of the write
    (Mike's question on choice 5, 2026-11-26 — data_objects_phase3_build_plan § 4). Returns the
    item with every guarded value it may NOT apply taken out.

      same or higher source  → the newer value wins; the old one goes to `previous`, and the
                               change is queued to be said once, by code, on the next reply;
      lower over higher      → never overwrites: held as `pending_{field}`; the second time
                               the same lower value arrives, one question is queued instead.

    A row written before a field was guarded has no `{field}_source`: it reads as stated —
    the safe direction, since a derived guess then cannot replace it."""
    out = dict(item)
    for field in o.get("guarded") or ():
        if field not in item or item[field] in (None, "", [], {}):
            continue
        new, old = item[field], row.get(field)
        new_src = _source_of(item, field)
        out[f"{field}_source"] = new_src
        if old in (None, "", [], {}) or new == old:
            if new == old and new_src == "stated":
                row.pop(f"pending_{field}", None)      # the user re-said it: settled
            continue
        old_src = str(row.get(f"{field}_source") or "stated")
        if _SOURCE_RANK[new_src] >= _SOURCE_RANK.get(old_src, 2):
            row.setdefault("previous", []).append(
                {"value": {field: old, f"{field}_source": old_src}, "changed_at": now})
            row.pop(f"pending_{field}", None)
            _queue_note(o, row, "changed", field, old, new)
            continue
        out.pop(field, None)
        out.pop(f"{field}_source", None)
        held = row.get(f"pending_{field}") or {}
        count = int(held.get("count") or 0) + 1 if held.get("value") == new else 1
        row[f"pending_{field}"] = {"value": new, "source": new_src, "at": now, "count": count}
        if count == 2:
            _queue_note(o, row, "ask", field, old, new)
    return out


def _render_value(v: Any) -> str:
    if isinstance(v, dict):
        return ", ".join(f"{v[k]}" for k in ("kind", "what", "near") if v.get(k)) or "-"
    return str(v).replace("_", " ")


def _queue_note(o: dict, row: dict, kind: str, field: str, old: Any, new: Any) -> None:
    """A note for the next reply — said once, by code (take_change_notes). Never a
    coordinate: guarded fields are descriptions, and the row's name is a place's name."""
    label = str(row.get("name") or row.get("title") or row.get("text") or "an entry")[:80]
    if kind == "changed":
        text = (f"{label} ({o['name']}): {field} changed from \"{_render_value(old)}\" to "
                f"\"{_render_value(new)}\" — say so once, in passing.")
    else:
        text = (f"{label} ({o['name']}): the user said {field} \"{_render_value(old)}\"; "
                f"something said since suggests \"{_render_value(new)}\". Ask once which "
                f"holds — nothing was changed.")
    try:
        with _locked():
            d = _pending()
            d.setdefault("notes", []).append({"text": text, "noted": False,
                                              "at": datetime.now().isoformat(timespec="seconds")})
            _write_json(_pending_path(), d)
    except Exception as exc:  # noqa: BLE001 — the write itself stands
        logger.warning(f"[data_objects] change note not queued: {exc}")


def take_change_notes() -> list[str]:
    """Guarded-field changes and questions not yet said on a reply — each returned once."""
    with _locked():
        d = _pending()
        notes = [n["text"] for n in d.get("notes", []) if not n.get("noted")]
        if not notes:
            return []
        for n in d.get("notes", []):
            n["noted"] = True
        d["notes"] = d["notes"][-50:]
        _write_json(_pending_path(), d)
    return list(dict.fromkeys(notes))


def archive_write(o: dict, item: dict, occurrence: dict | None = None,
                  by_code: bool = False) -> str:
    """Write one entry into an archive-store object under its identity rule, and clear one
    pending marker for it. Shared by write_data_object and write_archive (registered
    categories), so the two doors cannot disagree. A code-kept log (places) is written only
    with `by_code` — its own module's writes; every model door, and the derived writer,
    are refused."""
    if read_only(o):
        return read_only_refusal(o)
    if code_kept(o) and not by_code:
        return code_kept_refusal(o)
    item = dict(item or {})
    today = date.today().isoformat()
    if o["id"] == "meals" and "time_from" not in item \
            and not re.search(r"\d{1,2}:\d{2}", str(item.get("at") or "")):
        # A meal written with no time — by the Diarist, which writes most of them — gets the same
        # rule the derived writer applies (Mike, 2026-11-23): the usual time for that meal, never
        # later than now. A time an agent wrote is kept. Live check: ramen filed "2026-11-23".
        try:
            from tools import noticed_logs
            text = " ".join(str(item.get(k) or "") for k in ("meal", "what", "notes", "at"))
            item.update(noticed_logs._meal_at(None, item, text, datetime.now()))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[data_objects] meal time not set: {exc}")
    if "for" in (o.get("fields") or {}) and item.get("for") and not item.get("for_contact"):
        cid = _contact_for(str(item["for"]))
        if cid:
            item["for_contact"] = cid
    has_for = "for" in (o.get("fields") or {})

    def _key(d: dict) -> str:
        # A gift for Mum and the same gift for Ida are two entries (review 2026-11-23 #7).
        k = _identity_key(d)
        return f"{k}|for:{str(d.get('for') or '').strip().casefold()}" if k and has_for else k
    with _locked():
        path = _archive_file(o["id"])
        rows = _rows(o["id"])
        key = _key(item)
        if occurrence is not None:
            row = next((r for r in rows if isinstance(r, dict) and key and not r.get("removed")
                        and _key(r) == key), None)
            if row is None:
                row = {**item, "date_added": item.get("date_added") or today}
                rows.append(row)
            occ = {"at": str(occurrence.get("at") or today),
                   "notes": str(occurrence.get("notes") or "")}
            if occurrence.get("kind"):
                occ["kind"] = str(occurrence["kind"])[:20]     # places: visit | mention
            row.setdefault("occurrences", []).append(occ)
            row["date_updated"] = today
            msg = f"Recorded another occurrence in {o['name']}."
        elif o.get("identity") == "occurrence":
            item["date_added"] = item.get("date_added") or today
            item.setdefault("recorded_at", datetime.now().isoformat(timespec="seconds"))
            # Meals only: every other event log keeps R20 — two identical cardiac readings in
            # half an hour can both be real, and a dropped health event is worse than a twin.
            twin = _recent_twin(rows, item) if o["id"] == "meals" else 0
            if twin:
                msg = f"Already recorded in {o['name']} (entry {twin}) — not added twice."
            else:
                rows.append(item)
                msg = f"Added an entry to {o['name']} (entry {len(rows)})."
        else:
            row = next((r for r in rows if isinstance(r, dict) and key and not r.get("removed")
                        and _key(r) == key), None)
            if row is not None:
                if o.get("guarded"):
                    item = _reconcile_guarded(o, row, item,
                                              datetime.now().isoformat(timespec="seconds"))
                if has_for and item.get("for") and not item.get("for_contact"):
                    row.pop("for_contact", None)    # a name that no longer links: no stale link
                for k, v in item.items():
                    if v in (None, "", [], {}):
                        continue
                    old = row.get(k)
                    # A second MENTION adds to the note — one entry per thing holds everything
                    # said about it (Mike, 2026-11-23). Only the derived writer's mentions: an
                    # agent writing a note means it as the note, and replaces it (review #6).
                    if k == "notes" and item.get("derived") and isinstance(old, str) \
                            and old.strip() and str(v).strip().casefold() not in old.casefold() \
                            and old.strip().casefold() not in str(v).casefold():
                        row[k] = f"{old.rstrip()}; {v}"
                    elif k in ("derived", "source_turn", "said_at"):
                        continue    # the row keeps when and how it was first written
                    else:
                        row[k] = v
                row["date_updated"] = today
                msg = (f"Updated the existing {key.split(':', 1)[0]}-matched entry in "
                       f"{o['name']} — fields merged, no duplicate added.")
            else:
                for field in o.get("guarded") or ():
                    if item.get(field) not in (None, "", [], {}):
                        item[f"{field}_source"] = _source_of(item, field)
                item["date_added"] = item.get("date_added") or today
                rows.append(item)
                msg = f"Added an entry to {o['name']} (entry {len(rows)})."
        # Atomic (tmp + replace): places.json is now read without the lock on every location
        # ping and turn, and a torn read would be "no places" — a false departure (review
        # 2026-11-26 #15h).
        _write_json(path, rows)
        if not o.get("created") and str(o.get("origin", "")).startswith("template:"):
            objs, _ = _materialise(o["id"], _stored())
            _save(objs)
        _clear_one_pending(o["id"])
    if msg.startswith("Added an entry") and o["id"] in (limits().get("dev_backlog_logs") or ()):
        _file_dev_request(o, item)
    return msg


# Fields that say when or how an entry was written, not what it says.
_BOOKKEEPING = {"date_added", "recorded_at", "said_at", "derived", "source_turn", "time_from",
                "previous", "date_updated", "removed"}
TWIN_MINUTES = 30


def _recent_twin(rows: list, item: dict) -> int:
    """The number of an entry saying exactly the same thing, written in the last half hour, or 0.
    MEALS ONLY (the caller). An occurrence never merges, so a turn that re-sends what the turn
    before it already logged (live check 2026-11-23: the Coordinator re-dispatched "ramen for
    lunch" on the next message) would file it twice. Two identical lunches within 30 minutes are
    a repeat, not two lunches."""
    def body(d: dict) -> dict:
        # `at` compared by day: the same lunch re-sent a minute later carries a later minute.
        return {k: (" ".join(str(v).split()).casefold()[:10] if k == "at"
                    else " ".join(str(v).split()).casefold())
                for k, v in d.items() if k not in _BOOKKEEPING and v not in (None, "", [], {})}
    want, now = body(item), datetime.now()
    if not want:
        return 0
    for i in range(len(rows) - 1, -1, -1):
        r = rows[i]
        if not isinstance(r, dict) or r.get("removed"):
            continue
        try:
            age = (now - datetime.fromisoformat(str(r.get("recorded_at") or ""))).total_seconds()
        except ValueError:
            continue
        if 0 <= age <= TWIN_MINUTES * 60 and body(r) == want:
            return i + 1
    return 0


def _contact_for(name: str) -> str:
    """The contact id a `for` name means — only when exactly one contact matches (Mike,
    2026-11-23: gift ideas tied to the person). Two matches or none → "" and the name stands."""
    try:
        from tools import crm
        want = " ".join(name.split()).casefold()
        if not want:
            return ""

        def _names(c: dict) -> set[str]:
            full = " ".join(str(c.get("name") or "").split()).casefold()
            out = {full, full.split(" ")[0] if full else ""}
            out |= {" ".join(str(c.get(k) or "").split()).casefold()
                    for k in ("first_name", "nickname", "preferred_name")}
            out |= {" ".join(str(x).split()).casefold() for x in c.get("referred_to_as") or []}
            return out - {""}
        # Whole names only — a substring match links "Dad" to "Vlad" and "me" to "James" (#7).
        hits = [c for c in crm._find_by_name(crm._load_contacts(), name) if want in _names(c)]
        return str(hits[0].get("id") or "") if len(hits) == 1 else ""
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[data_objects] contact link not made: {exc}")
        return ""


def entries_for_contact(contact: dict) -> list[dict]:
    """Every entry in a log with a `for` field that names this contact — linked by id, or by
    name when no link was made. Read by tools/crm.read_contact. Never raises."""
    try:
        cid = str(contact.get("id") or "")
        names = {str(contact.get(k) or "").strip().casefold()
                 for k in ("name", "first_name", "preferred_name", "nickname")}
        names |= {str(s).strip().casefold() for s in contact.get("referred_to_as") or []}
        names -= {""}
        out, agent = [], _caller()
        for o in objects():
            if o.get("store") != "archive" or "for" not in (o.get("fields") or {}) \
                    or o.get("status") != "active":
                continue
            if not may_read(agent, o)[0]:          # the read rule binds here too
                continue
            for r in _rows(o["id"]):
                if not isinstance(r, dict) or r.get("removed"):
                    continue
                if (cid and r.get("for_contact") == cid) or (
                        not r.get("for_contact")
                        and str(r.get("for") or "").strip().casefold() in names):
                    out.append({"list": o["name"], **{k: v for k, v in r.items()
                                if k not in ("for_contact", "derived", "source_turn")}})
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[data_objects] entries for contact not read: {exc}")
        return []


def _file_dev_request(o: dict, item: dict) -> None:
    """A new entry in a list named in `dev_backlog_logs` also reaches the development backlog
    as a FEATURE_REQUEST (Mike, 2026-11-23). The Synthesizer's own dev-request path usually
    files it too; the sync's similarity merge folds the two into one Inbox item."""
    text = " ".join(str(item.get(k) or "") for k in ("title", "text", "description", "notes"))
    text = " ".join(text.split())
    if not text:
        return
    try:
        from tools.logger import write_quality_event
        write_quality_event("FEATURE_REQUEST", source_agent="data_objects",
                            detail=f"From the user's {o['name']} list: {text[:400]}")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[data_objects] dev backlog entry not filed: {exc}")


def registered_category(category: str) -> dict | None:
    """The archive-store object whose category this is (following a merge), or None."""
    for o in objects():
        if o["id"] == category:
            o = _follow(o, objects())
            return o if o and o.get("store") == "archive" else None
    return None


def _dates_of(row: dict) -> list[str]:
    """The dates a filter reads an entry by: when it happened (`at`, `date`, its
    occurrences) if it says; only an entry that names no date of its own falls back to when
    it was recorded. Otherwise a frog caught in 2024 and logged today would also match
    "since 2025"."""
    own = [str(row.get(k, ""))[:10] for k in ("at", "date") if row.get(k)]
    own += [str(x.get("at", ""))[:10] for x in row.get("occurrences") or []
            if isinstance(x, dict) and x.get("at")]
    # Only a real date or year counts as the entry's own: an `at` of "15:00" or "3pm" (the
    # time of day the Diarist is told to give) says nothing about which day.
    own = [d for d in own if re.match(r"^\d{4}(-\d{2}(-\d{2})?)?(T|\s|$)", d)]
    if own:
        return own
    return [str(row.get(k, ""))[:10] for k in ("date_added", "recorded_at") if row.get(k)]


def read_entries(o: dict, since: str = "", until: str = "", contains: str = "",
                 count_only: bool = False, limit: int = 0, viewer: str = "") -> dict:
    rows = _rows(o["id"])
    # A removed entry keeps its number (so `change_entry` numbers stay true) and is never shown.
    numbered = [{"n": i + 1, **r} if isinstance(r, dict) else {"n": i + 1, "value": r}
                for i, r in enumerate(rows) if not (isinstance(r, dict) and r.get("removed"))]
    if code_kept(o):
        # Places (review 2026-11-26 #7): a name the user declined to save is hidden from every
        # reader; a private place is out of day-to-day mention (R24) — the Synthesizer, which
        # reads a list only when the user asks for it, and Pattern Miner still see it.
        numbered = [r for r in numbered if not r.get("hidden")
                    and (not r.get("private") or viewer in ("synthesizer", "pattern_miner"))]
    if since or until:
        # Compared at the entry's own precision: an `at` of "2024" (a year, as the relative-
        # reference rule records "two years ago") falls inside 2024-01-01..2024-12-31.
        numbered = [r for r in numbered if any(
            (not since or d >= since[:len(d)]) and (not until or d <= until[:len(d)])
            for d in _dates_of(r))]
    if contains:
        needle = contains.casefold()
        # Matched on what the reader may SEE: on the full row, `contains="51.502"` confirmed a
        # place's position digit by digit (review 2026-11-26, coordinates #1).
        view = _strip_coordinates if _is_location(o) else (lambda r: r)
        numbered = [r for r in numbered
                    if needle in json.dumps(view(r), ensure_ascii=False).casefold()]
    out: dict = {"object": public(o), "status": o.get("status")}
    if count_only:
        if o.get("identity") == "occurrence":
            out.update(things=len(numbered), occurrences=len(numbered))
        else:
            out.update(things=len(numbered),
                       occurrences=sum(len(r.get("occurrences") or []) for r in numbered))
        return out
    cap = int(limit or limits()["read_max_entries"])
    out["total"] = len(numbered)
    out["truncated"] = len(numbered) > cap
    out["entries"] = [_reader_view(r, o) for r in numbered[-cap:]]
    if _is_location(o):
        out = _strip_coordinates(out)
    return out


def _reader_view(r: dict, o: dict) -> dict:
    """An entry as an agent reads it: the provenance bookkeeping of the object's GUARDED fields
    (`{field}_source`, a held `pending_{field}`) stays in the file for Pattern Miner and the
    reconciler, and out of the prompt — a model told "derived" starts saying it. Only those
    keys: a user's own `protein_source` field is theirs (review 2026-11-26 #12)."""
    guarded = o.get("guarded") or ()
    if not isinstance(r, dict) or not (guarded or code_kept(o)):
        return r
    drop = {f"{g}_source" for g in guarded} | {f"pending_{g}" for g in guarded}
    if code_kept(o):
        # Code's own bookkeeping on a place: the raw opening periods (hundreds of characters a
        # place — code answers "open then?" from them), lookup and ambiguity state.
        drop |= {"hours", "hours_at", "lookup_failed_at", "ambiguity_said", "last_said_at"}
    return {k: v for k, v in r.items() if k not in drop}


# ---------------------------------------------------------------------------
# Native stores — handed to their own tools
# ---------------------------------------------------------------------------

def _get_path(d: dict, dotted: str) -> Any:
    cur: Any = d
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _read_log_object(o: dict, agent: str, f: dict) -> Any:
    from tools.logger import read_log
    lim = limits()
    days = max(1, min(int(f.get("days") or lim["log_read_default_days"]),
                      int(lim["log_read_max_days"])))
    paths = dict(o.get("log_fields") or {})
    out = []
    for i in range(days - 1, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        day = read_log(d) or {}
        vals = ({k: _get_path(day, p) for k, p in paths.items()} if paths else day)
        vals = {k: v for k, v in vals.items() if v not in (None, "", [], {})}
        if vals:
            out.append({"date": d, **vals})
    return out


def _read_calendar_object(o: dict, agent: str, f: dict) -> Any:
    from tools.caldav import read_calendar
    start = f.get("since") or date.today().isoformat()
    end = f.get("until") or (date.today() + timedelta(days=14)).isoformat()
    return read_calendar(start, end)


def _read_medication_object(o: dict, agent: str, f: dict) -> Any:
    """Medication taken on one day — today, or the day `since` names — read from the task
    ledger's dose habits (tools/obligations.medication_taken). Nothing is stored here."""
    from tools.obligations import medication_taken
    try:
        day = date.fromisoformat(str(f.get("since") or "")[:10])
    except ValueError:
        day = None
    return medication_taken(day=day)


def _simple(module: str, fn: str, **kw) -> Callable[[dict, str, dict], Any]:
    def run(o: dict, agent: str, f: dict) -> Any:
        mod = __import__(module, fromlist=[fn])
        return getattr(mod, fn)(**kw)
    return run


_NATIVE_READERS: dict[str, Callable[[dict, str, dict], Any]] = {
    "log": _read_log_object,
    "calendar": _read_calendar_object,
    "medication": _read_medication_object,
    "wisdom": lambda o, a, f: __import__("tools.wisdom", fromlist=["read_wisdom"]).read_wisdom(
        **({"domains": o["domains"]} if o.get("domains") else {})),
    "contacts": _simple("tools.crm", "list_contacts"),
    "tasks": _simple("tools.obligations", "list_tasks"),
    "profile": _simple("tools.profile", "read_profile"),
    "goals": _simple("tools.goals", "read_goals"),
    "agent_config": lambda o, a, f: __import__(
        "tools.agent_config", fromlist=["read_agent_config"]).read_agent_config(agent_name=a),
}


def _native_write_fn(store: str) -> Callable | None:
    table = {
        "contacts": ("tools.crm", "write_contact"),
        "tasks": ("tools.obligations", "open_task"),
        "wisdom": ("tools.wisdom", "write_wisdom"),
        "profile": ("tools.profile", "write_profile"),
        "agent_config": ("tools.agent_config", "write_agent_config"),
        "log": ("tools.logger", "write_log"),
        "calendar": ("tools.caldav", "write_calendar_event"),
        "day_shape": ("tools.day_shape", "set_day_shape"),
    }
    if store not in table:
        return None
    mod, fn = table[store]
    return getattr(__import__(mod, fromlist=[fn]), fn, None)


def _log_content(o: dict, entry: dict) -> dict:
    """An entry for a log-store object, nested at the object's own log paths."""
    paths = dict(o.get("log_fields") or {})
    content: dict = {}
    for k, v in entry.items():
        dotted = paths.get(k, k)
        cur = content
        parts = dotted.split(".")
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = v
    return content


# ---------------------------------------------------------------------------
# The pending marker
# ---------------------------------------------------------------------------

def _pending() -> dict:
    d = _read_json(_pending_path(), {})
    d.setdefault("pending", [])
    d.setdefault("failed", [])
    return d


def mark_pending(obj_id: str, set_at: float | None = None) -> str:
    tok = uuid.uuid4().hex[:12]
    with _locked():
        d = _pending()
        d["pending"].append({"token": tok, "object": obj_id,
                             "set_at": time.time() if set_at is None else set_at})
        _write_json(_pending_path(), d)
    return tok


def pending_tokens(obj_id: str = "") -> list[str]:
    return [p["token"] for p in _pending()["pending"] if not obj_id or p["object"] == obj_id]


# Tokens owned by a Diarist run alive in THIS process (run_verified_write adds them at its
# start, drops them at its end). Only these can be cleared by a write, and only by a write the
# Diarist makes (Mike, decision 1: a Diarist `write_archive` into the right category counts).
# So a specialist writing the same category cannot "verify" the Diarist, and a marker a restart
# orphaned is never cleared by the next turn's write — it expires and is reported instead.
# Kept per process, not per thread: the Diarist's parallel tool calls run on pool threads
# (core/orchestrator.py _make_gemini_dispatch) that inherit its trace, not its thread.
_LIVE: set[str] = set()


def _clear_one_pending(obj_id: str) -> None:
    if _caller() != "diarist":
        return
    with _locked():
        d = _pending()
        mine = [p for p in d["pending"] if p["object"] == obj_id and p["token"] in _LIVE]
        if not mine:
            return
        oldest = min(mine, key=lambda p: p["set_at"])
        d["pending"] = [p for p in d["pending"] if p is not oldest]
        _write_json(_pending_path(), d)


def _wait_pending(obj_id: str) -> None:
    """Wait out a write still on its way — only a marker younger than the expiry: an older
    one is a run that died, and waiting on it would only stall the reply."""
    exp = float(limits()["pending_expiry_seconds"])

    def _fresh() -> bool:
        return any(p["object"] == obj_id and time.time() - p["set_at"] <= exp
                   for p in _pending()["pending"])

    deadline = time.time() + float(limits()["pending_wait_seconds"])
    while _fresh() and time.time() < deadline:
        time.sleep(0.1)


def _fail(tokens: list[str], persona: str, reason: str) -> None:
    """Move markers to `failed`, push once per object, record a quality event."""
    with _locked():
        d = _pending()
        hit = [p for p in d["pending"] if p["token"] in tokens]
        if not hit:
            return
        d["pending"] = [p for p in d["pending"] if p["token"] not in tokens]
        names = []
        for p in hit:
            o = get(p["object"])
            name = o["name"] if o else p["object"]
            names.append(name)
            d["failed"].append({"object": p["object"], "name": name,
                                "at": datetime.now().isoformat(timespec="seconds"),
                                "noted": False})
        _write_json(_pending_path(), d)
    for name in dict.fromkeys(names):
        try:
            _send_push("Metatron", f"That entry for your {name} didn't save — want me to "
                                   f"try again?", persona)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[data_objects] failed-write push not sent: {exc}")
        try:
            _quality_event(event_type="DATA_OBJECT_WRITE_FAILED", source_agent="diarist",
                           detail=f"An entry the user asked to keep in '{name}' did not "
                                  f"land: {reason}.")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[data_objects] failed-write event not recorded: {exc}")


def run_verified_write(run: Callable[[str, str | None], Any], directive: str,
                       tokens: list[str], persona: str, retry_model: str | None,
                       retry_directive: str = "") -> bool:
    """
    The Diarist write, verified (§ 3.4). `run(directive, model)` runs the Diarist once;
    model None is its own. Each token is a pending marker this turn set. Returns True when
    every marker cleared.

    One retry, on `retry_model` — a different model from the one that just failed (verify
    finding 3). A run that raises counts as a run that wrote nothing. The retry is handed
    `retry_directive` — the user's words and the entry alone — so the journal and daily-log
    writes of the first run are not made twice.

    While this runs its tokens are live (see _LIVE) and their clock restarts now, so a slow
    run of blocking specialists before it cannot expire them unseen.
    """
    with _locked():
        d = _pending()
        for p in d["pending"]:
            if p["token"] in tokens:
                p["set_at"] = time.time()
        _write_json(_pending_path(), d)
    _LIVE.update(tokens)
    try:
        return _verified(run, directive, tokens, persona, retry_model, retry_directive)
    finally:
        _LIVE.difference_update(tokens)


def _verified(run: Callable[[str, str | None], Any], directive: str, tokens: list[str],
              persona: str, retry_model: str | None, retry_directive: str) -> bool:
    def _attempt(d: str, model: str | None) -> None:
        try:
            run(d, model)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[data_objects] Diarist write attempt failed: {exc}")

    _attempt(directive, None)
    left = [t for t in tokens if t in pending_tokens()]
    if not left:
        return True
    names = []
    for p in _pending()["pending"]:
        if p["token"] in left:
            o = get(p["object"])
            names.append(f"{o['name'] if o else p['object']} (object \"{p['object']}\")")
    retry = (f"{retry_directive or directive}\n\nRETRY — the entry for {', '.join(names)} "
             f"was NOT recorded on the first attempt. Record it now with write_data_object, "
             f"naming that object. Record nothing else: the rest of this turn is already "
             f"logged.")
    _attempt(retry, retry_model)
    left = [t for t in tokens if t in pending_tokens()]
    if not left:
        return True
    _fail(left, persona, "the Diarist did not record it, and one retry did not either")
    return False


def take_turn_notes() -> list[str]:
    """Names whose entry did not save and the user has not yet been told on a reply. Expires
    stale markers first (each raising the same push and event). Each name is returned once."""
    exp = float(limits()["pending_expiry_seconds"])
    stale = [p["token"] for p in _pending()["pending"]
             if time.time() - p["set_at"] > exp and p["token"] not in _LIVE]
    if stale:
        _fail(stale, current_persona() or "", "its pending marker expired unverified")
    with _locked():
        d = _pending()
        names = [f["name"] for f in d["failed"] if not f.get("noted")]
        if not names:
            return []
        for f in d["failed"]:
            f["noted"] = True
        _write_json(_pending_path(), d)
    return list(dict.fromkeys(names))


def retry_model_for(agent: str = "diarist") -> str | None:
    """The `retry_model` on an agent's routing entry — model ids live in routing only."""
    try:
        from core.router import _load_routing
        return (_load_routing().get("agents", {}).get(agent, {}) or {}).get("retry_model")
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Internal read, used by tools and by the pipeline's pre-fetch
# ---------------------------------------------------------------------------

def safe_category(cat: str) -> bool:
    """A category is a file stem in archive/: nothing that could name a path elsewhere."""
    return bool(cat) and not cat.startswith(("_", ".")) and not any(
        c in cat for c in ("/", "\\", "..", "\x00"))


def fetch(agent: str, name: str, since: str = "", until: str = "", contains: str = "",
          count_only: bool = False, days: int = 0, limit: int = 0,
          wait: bool = True) -> dict:
    o = resolve(name)
    if o is None:
        cat = str(name or "").lower().strip().replace(" ", "_")
        # An unregistered archive category reads raw, exactly as the archive reader did —
        # but only for an agent that holds write_archive, so no agent gains reach (Mike,
        # decision 6, 2026-11-22).
        if safe_category(cat) and _archive_file(cat).exists():
            if not _holds(agent, "write_archive"):
                return {"error": f"No log called '{name}' is available to this agent."}
            from tools.diarist import _read_archive_category
            rows = _read_archive_category(cat)
            out = {"object": {"id": cat, "name": cat, "store": "archive",
                              "registered": False},
                   "entries": [{"n": i + 1, **r} if isinstance(r, dict) else r
                               for i, r in enumerate(rows)]}
            return _strip_coordinates(out) if cat in LOCATION_STORES else out
        names = [x["name"] for x in objects()
                 if x.get("status") == "active" and not x.get("merged_into")
                 and may_read(agent, x)[0]]
        return {"error": f"No log called '{name}'.", "available": names}
    ok, why = may_read(agent, o)
    if not ok:
        return {"error": f"Not readable here: {why}."}
    if wait:
        _wait_pending(o["id"])
    if o.get("store") == "archive" or o.get("store") not in _NATIVE_READERS:
        if o.get("store") != "archive":
            return {"object": public(o), "entries": [],
                    "note": f"the {o['store']} store has no reader yet"}
        return read_entries(o, since=since, until=until, contains=contains,
                            count_only=count_only, limit=limit, viewer=agent)
    result = _NATIVE_READERS[o["store"]](o, agent, {"since": since, "until": until,
                                                    "days": days})
    if _is_location(o):
        result = _strip_coordinates(result)
    return {"object": public(o), "store": o["store"], "result": result}


# ---------------------------------------------------------------------------
# The four tools
# ---------------------------------------------------------------------------

def list_data_objects(with_entries: bool = False) -> list[dict]:
    """The user's active logs and lists this agent can read: names and one-line
    descriptions, never entries. An unbound caller is code (Build's presence check) and sees
    every active, non-private object."""
    agent = _caller()
    out = []
    for o in objects():
        if o.get("status") != "active" or o.get("merged_into"):
            continue
        if agent and agent != "coordinator" and not may_read(agent, o)[0]:
            continue
        row = {"name": o["name"], "description": o["description"]}
        if o.get("store") == "archive":
            row["entries"] = sum(1 for r in _rows(o["id"])
                                 if not (isinstance(r, dict) and r.get("removed")))
            if with_entries and not row["entries"]:
                continue
        elif with_entries:
            continue
        out.append(row)
    return out


def read_data_object(object: str, since: str = "", until: str = "", contains: str = "",
                     count_only: bool = False, days: int = 0, limit: int = 0) -> dict:
    """One log's entries, filtered, or a count (distinct things vs occurrences)."""
    agent = _caller()
    if not agent:
        return {"error": "Not readable here: no calling agent is bound to this read."}
    return fetch(agent, object, since=since, until=until, contains=contains,
                 count_only=count_only, days=days, limit=limit)


def write_data_object(object: str, entry: dict | None = None, action: str = "add",
                      occurrence: dict | None = None, description: str = "",
                      fields: dict | None = None, identity: str = "",
                      field: str = "") -> str:
    """Create a log, add an entry, record an occurrence, or add a field."""
    agent = _caller()
    if action == "create":
        # Starting a log is code's, on the Coordinator's "start" (core/orchestrator.py
        # _resolve_data_objects), and only when the user asked. A model creating one as well
        # duplicated the start and then filed the request itself as the first entry (live
        # check, 2026-11-22). An unbound caller is code.
        if agent:
            return ("Not created: a log is started for the user when they ask for one — "
                    "it already exists if they did. Record nothing in it unless a LOG ENTRY "
                    "TO RECORD block names it.")
        out = create_object(object, description=description, fields=fields,
                            identity=identity or "occurrence")
        if out.get("created"):
            return f"Started {out['object']['name']}."
        if out.get("match"):
            return (f"Not created: '{object}' is already kept as "
                    f"{out['match']['name']} — use that one.")
        return f"Not created: {out.get('error')}."
    o = resolve(object)
    if o is None:
        return f"Not recorded: no log called '{object}'."
    if read_only(o):
        return read_only_refusal(o)
    if code_kept(o):
        return code_kept_refusal(o)
    if o.get("status") == "archived":
        return f"Not recorded: {o['name']} is archived. Unarchive it first."
    if action == "add_field":
        if not field:
            return "Not recorded: name the field to add."
        with _locked():
            objs, s = _materialise(o["id"], _stored())
            if field not in s["fields"]:
                # Counted for the content-free analytics row (phase 2, plan § 3.6) — a count,
                # never the field's name.
                s["fields_added"] = int(s.get("fields_added") or 0) + 1
            s["fields"].setdefault(field, "text")
            _save(objs)
        return f"{o['name']} now has a '{field}' field. Earlier entries are unchanged."
    if not isinstance(entry, dict) or not entry:
        return "Not recorded: the entry is empty."
    # The Diarist adds to one of the user's logs only when this turn asked for an entry there
    # — a live marker for that log (run_verified_write). Instructions did not hold it: in the
    # 2026-11-22 live checks it wrote a correction, and the answer to "where was that?", as new
    # entries against an explicit "NOT A NEW ENTRY" hold. Phase 1 has no unasked log writes.
    is_log = o.get("store") == "archive" or o.get("id") != o.get("store")   # not a store itself
    if agent == "diarist" and is_log and not any(p["object"] == o["id"] and p["token"] in _LIVE
                                                 for p in _pending()["pending"]):
        return (f"Not recorded: nothing was asked to be added to {o['name']} this turn — a "
                f"correction is made by another agent, and a log takes entries only when the "
                f"user gives one.")
    store = o.get("store", "archive")
    if store != "archive":
        tool = NATIVE_WRITE.get(store)
        if not tool:
            return f"Not recorded: the {store} store cannot be written from here."
        if not _holds(agent, tool):
            return (f"Not recorded: {o['name']} is written through {tool}, which this agent "
                    f"does not hold.")
        paths = dict(o.get("log_fields") or {})
        if store == "log" and paths and not any(k in paths for k in entry):
            # The reader reads only these paths, so anything else would be written where no
            # read-back can find it — and reported as saved.
            return (f"Not recorded: {o['name']} keeps {', '.join(paths)} — give the entry "
                    f"under at least one of those.")
        fn = _native_write_fn(store)
        try:
            payload = ({"content": _log_content(o, {k: v for k, v in entry.items()
                                                    if not paths or k in paths})}
                       if store == "log" else entry)
            result = fn(**payload)
        except TypeError as exc:
            return f"Not recorded: the entry does not fit {tool}: {exc}"
        if _refused(result):
            return str(result)
        _clear_one_pending(o["id"])
        return str(result)
    if action == "add_occurrence":
        return archive_write(o, entry, occurrence=occurrence or {})
    return archive_write(o, entry)


def _refused(result: Any) -> bool:
    """A native tool's own refusal — it returns a string or an error dict, never raises."""
    if isinstance(result, dict):
        return bool(result.get("error"))
    text = str(result or "").lstrip()
    return text.startswith(("Not ", "Error", "Refused", "Could not", "Cannot", "Failed"))


def fields_of(o: dict) -> list[str]:
    """The field names an entry for this object is given under — what the Diarist is told."""
    if o.get("store") == "log":
        return list((o.get("log_fields") or {}).keys())
    return list((o.get("fields") or {}).keys())


def amend_data_object(object: str, action: str, entry: int = 0,
                      changes: dict | None = None, new_name: str = "", alias: str = "",
                      into: str = "", reason: str = "") -> str:
    """Change an entry (keeping history), remove one from view or restore it, rename, add an
    alias, archive or unarchive, mark private or not, or merge into another log. Nothing is
    deleted."""
    agent = _caller()
    o = resolve(object, follow=(action != "unarchive"))
    if o is None:
        return f"Not changed: no log called '{object}'."
    if read_only(o):
        return read_only_refusal(o, "Not changed")
    ok, why = may_read(agent, o)
    if not ok:
        return f"Not changed: {why}."
    now = datetime.now().isoformat(timespec="seconds")
    if code_kept(o) and action not in ("add_alias", "rename"):
        # Entry acts AND whole-log acts: "keep Rossi's private" said about one place would
        # otherwise make the user's whole Places list private through this door. One place's
        # privacy, forgetting or confirmation is the Coordinator's PLACES act, done by code.
        return (f"Not changed: {o['name']} is kept by code from what the user says — a "
                f"change they state this turn is recorded without a call here.")
    if action == "change_entry":
        if o.get("store") != "archive":
            return f"Not changed: {o['name']} is changed through its own tool."
        if not isinstance(changes, dict) or not changes:
            return "Not changed: say what to change."
        try:
            entry = int(entry)
        except (TypeError, ValueError):
            return f"Not changed: give the entry's number, as shown when the log was read."
        with _locked():
            rows = _rows(o["id"])
            if not 1 <= int(entry) <= len(rows) or not isinstance(rows[int(entry) - 1], dict):
                return f"Not changed: {o['name']} has no entry {entry}."
            row = rows[int(entry) - 1]
            if row.get("removed"):
                return (f"Not changed: entry {entry} in {o['name']} was removed — restore it "
                        f"first if it should be back.")
            prev = {k: row.get(k) for k in changes}
            row.update(changes)
            row.setdefault("previous", []).append({"value": prev, "changed_at": now})
            row["date_updated"] = now[:10]
            with open(_archive_file(o["id"]), "w") as f:
                json.dump(rows, f, indent=2)
            os.chmod(_archive_file(o["id"]), 0o600)
        return f"Changed entry {entry} in {o['name']}; the earlier value is kept."
    if action in ("remove_entry", "restore_entry"):
        # Out of view, never deleted (plan R19/R20; Mike, 2026-11-23 — "Pain was a duplicate",
        # "Troxy was a concert, not a film"). The row stays in the file, so entry numbers stay
        # put and Pattern Miner still sees it; every read skips it.
        if o.get("store") != "archive":
            return f"Not changed: {o['name']} is changed through its own tool."
        try:
            entry = int(entry)
        except (TypeError, ValueError):
            return "Not changed: give the entry's number, as shown when the log was read."
        with _locked():
            rows = _rows(o["id"])
            if not 1 <= entry <= len(rows) or not isinstance(rows[entry - 1], dict):
                return f"Not changed: {o['name']} has no entry {entry}."
            row = rows[entry - 1]
            if action == "remove_entry":
                if row.get("removed"):
                    return f"Entry {entry} was already removed from {o['name']}."
                row["removed"] = {"at": now, "reason": " ".join(str(reason or "").split())[:200]}
            else:
                if not row.get("removed"):
                    return f"Entry {entry} in {o['name']} is not removed."
                row.setdefault("previous", []).append({"value": {"removed": row.pop("removed")},
                                                       "changed_at": now})
            row["date_updated"] = now[:10]
            with open(_archive_file(o["id"]), "w") as f:
                json.dump(rows, f, indent=2)
            os.chmod(_archive_file(o["id"]), 0o600)
        return (f"Removed entry {entry} from {o['name']} — out of view, nothing deleted."
                if action == "remove_entry" else f"Restored entry {entry} to {o['name']}.")
    with _locked():
        objs, s = _materialise(o["id"], _stored())
        if action == "rename":
            other = resolve(new_name)
            if not new_name or (other and other["id"] != s["id"]):
                return f"Not changed: '{new_name}' is already another log's name."
            s["aliases"] = list(dict.fromkeys([*s["aliases"], s["name"]]))
            s["name"] = new_name
            msg = f"Renamed to {new_name}; the old name still finds it."
        elif action == "add_alias":
            other = resolve(alias)
            if not alias or (other and other["id"] != s["id"]):
                return f"Not changed: '{alias}' already means another log."
            s["aliases"] = list(dict.fromkeys([*s["aliases"], alias]))
            msg = f"'{alias}' now finds {s['name']}."
        elif action in ("archive", "unarchive", "private", "public"):
            s["status"] = {"archive": "archived", "unarchive": "active",
                           "private": "private", "public": "active"}[action]
            msg = {"archived": f"Archived {s['name']} — out of the lists, nothing deleted.",
                   "active": f"{s['name']} is back in the lists.",
                   "private": f"{s['name']} is private — it stays out of every list."}[s["status"]]
        elif action == "merge":
            target = resolve(into)
            if target is None or target["id"] == s["id"]:
                return f"Not merged: no other log called '{into}'."
            if s.get("store") != "archive" or target.get("store") != "archive":
                return "Not merged: only logs kept in the archive can be merged for now."
            if code_kept(target):
                # Review 2026-11-26 #1: a merge INTO places carried a model-written position
                # into the store zone_for reads. Only code writes a place.
                return code_kept_refusal(target).replace("Not recorded", "Not merged")
            moved = [{**r, "merged_from": s["id"]} for r in _rows(s["id"])
                     if isinstance(r, dict)]
            trows = _rows(target["id"]) + moved
            tpath = _archive_file(target["id"])
            tpath.parent.mkdir(parents=True, exist_ok=True)
            with open(tpath, "w") as f:
                json.dump(trows, f, indent=2)
            os.chmod(tpath, 0o600)
            s["merged_into"] = target["id"]
            s["status"] = "archived"
            msg = (f"Merged {s['name']} into {target['name']} ({len(moved)} entries); "
                   f"the original is kept.")
        else:
            return f"Not changed: unknown action '{action}'."
        _save(objs)
    if action == "add_alias" and agent == "synthesizer":
        # "That belongs in my X list" (phase 2 plan § 3.4, review R4/R5). The Synthesizer adds
        # the user's name for it; CODE then turns an open offer to start a new list into an
        # offer to keep those facts in this one — a second card. Nothing is filed and nothing
        # is declined by this call: the facts move only on the user's tap.
        try:
            from tools import noticed_logs
            noticed_logs.on_alias(s["id"])
        except Exception as exc:  # noqa: BLE001 — the alias itself has landed
            logger.warning(f"[data_objects] noticed-log alias hook failed: {exc}")
    return msg


def add_alias(obj_id: str, alias: str) -> bool:
    """Add a name to a log, as CODE — the noticed-log alias card's executor
    (tools/noticed_logs.alias_noticed_log) and the yes path's category alias. `amend_data_object`
    refuses an unbound caller by design (its read rule), so code has this door instead. Refuses
    a name that already finds a different log. Returns True when the name now finds it."""
    alias = str(alias or "").strip()
    if not alias or read_only(get(obj_id)):
        return False
    with _locked():
        other = resolve(alias, follow=False)
        if other is not None and other["id"] != obj_id:
            return False
        objs, s = _materialise(obj_id, _stored())
        if alias not in s["aliases"]:
            s["aliases"] = list(dict.fromkeys([*s["aliases"], alias]))
            _save(objs)
    return True


# ---------------------------------------------------------------------------
# The manifest (R30) — rendered by core/orchestrator.py into the per-turn user message
# ---------------------------------------------------------------------------

def manifest_for(agent: str) -> str:
    """The logs and lists `agent` may read, names and one-line descriptions — never entries.
    The Coordinator sees every active, non-private object (it routes); any other agent sees
    only what it can read, and only if it holds read_data_object at all. Never raises."""
    try:
        lim = limits()
        if agent != "coordinator" and not _holds(agent, "read_data_object"):
            return ""
        shown = []
        for o in objects():
            if o.get("status") != "active" or o.get("merged_into"):
                continue
            # A registered store itself (contacts, tasks, the daily log …) is not listed
            # unless config says so: every agent that can read one holds its tool already.
            # A log KEPT IN a store (sleep, exercise — in the daily log) is listed.
            if o.get("store") != "archive" and o["id"] == o.get("store") \
                    and not lim["manifest_includes_native_stores"]:
                continue
            if agent != "coordinator" and not may_read(agent, o)[0]:
                continue
            shown.append(o)
        shown.sort(key=lambda o: (str(o.get("origin", "")).startswith("template:"),
                                  o["name"].casefold()))
        shown = shown[: int(lim["manifest_max_objects"])]
        if not shown:
            return ""
        lines = []
        for o in shown:
            aka = f" (also: {', '.join(o['aliases'])})" if o.get("aliases") else ""
            desc = f" — {o['description']}" if o.get("description") else ""
            lines.append(f"- {o['name']}{aka}{desc}")
        return ("## The user's logs and lists\n\nKept under these names. You are not shown "
                "the entries here.\n" + "\n".join(lines))
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[data_objects] manifest unavailable: {exc}")
        return ""


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

LIST_DATA_OBJECTS_SCHEMA = {
    "name": "list_data_objects",
    "description": "List the user's logs and lists you can read — names and one-line "
                   "descriptions, never entries.",
    "input_schema": {
        "type": "object",
        "properties": {
            "with_entries": {"type": "boolean",
                             "description": "Only logs that hold at least one entry."},
        },
        "required": [],
    },
}

READ_DATA_OBJECT_SCHEMA = {
    "name": "read_data_object",
    "description": (
        "Read one of the user's logs or lists by the name the user uses for it (any of its "
        "names works). Returns its entries, numbered — the number is how an entry is "
        "changed later — or, with count_only, how many distinct things and how many "
        "occurrences it holds. Nothing on file means ask the user; it never means invent."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "object": {"type": "string", "description": "The log's name, e.g. 'heart log'."},
            "since": {"type": "string", "description": "YYYY-MM-DD — entries on or after."},
            "until": {"type": "string", "description": "YYYY-MM-DD — entries on or before."},
            "contains": {"type": "string", "description": "Only entries mentioning this."},
            "count_only": {"type": "boolean", "description": "Counts instead of entries."},
            "days": {"type": "integer", "description": "Daily-log objects: days back."},
            "limit": {"type": "integer", "description": "Most recent N entries."},
        },
        "required": ["object"],
    },
}

WRITE_DATA_OBJECT_SCHEMA = {
    "name": "write_data_object",
    "description": (
        "Record in one of the user's logs or lists. action 'add' (default) records an "
        "entry; 'add_occurrence' records another time something already listed happened "
        "('watched it again') — give the thing in `entry` and {at, notes} in `occurrence`; "
        "'create' starts a new log named `object`; 'add_field' adds a field. Record only "
        "what the user said — never a value they did not give."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "object": {"type": "string", "description": "The log's name."},
            "action": {"type": "string",
                       "enum": ["add", "add_occurrence", "create", "add_field"]},
            "entry": {"type": "object", "additionalProperties": True,
                      "description": "The entry's fields, e.g. {\"text\": …, \"at\": …, "
                                     "\"notes\": …}. `at` is a date or a year. "
                                     + RELATIVE_REFERENCES},
            "occurrence": {"type": "object", "additionalProperties": True,
                           "description": "{at: YYYY-MM-DD, notes} for add_occurrence."},
            "description": {"type": "string", "description": "create: one line."},
            "fields": {"type": "object", "additionalProperties": True,
                       "description": "create: field names → kinds."},
            "identity": {"type": "string",
                         "enum": ["thing", "occurrence", "thing+occurrences"]},
            "field": {"type": "string", "description": "add_field: the new field's name."},
        },
        "required": ["object"],
    },
}

AMEND_DATA_OBJECT_SCHEMA = {
    "name": "amend_data_object",
    "description": (
        "Change one of the user's logs. 'change_entry' changes entry number `entry` (from "
        "read_data_object) with `changes` — the old value is kept; 'remove_entry' takes entry "
        "`entry` off the list (out of view, kept — give `reason`), 'restore_entry' puts it "
        "back; 'rename' (`new_name`); "
        "'add_alias' (`alias`); 'archive' takes it out of the lists without deleting "
        "anything, 'unarchive' brings it back; 'private' keeps it out of every list; "
        "'merge' moves its entries into another log (`into`). Nothing is ever deleted."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "object": {"type": "string"},
            "action": {"type": "string",
                       "enum": ["change_entry", "remove_entry", "restore_entry", "rename",
                                "add_alias", "archive", "unarchive", "private", "public",
                                "merge"]},
            "entry": {"type": "integer",
                      "description": "change_entry / remove_entry / restore_entry: the entry "
                                     "number."},
            "reason": {"type": "string",
                       "description": "remove_entry: why, in a few words (\"a duplicate\", "
                                      "\"a concert, not a film\")."},
            "changes": {"type": "object", "additionalProperties": True,
                        "description": "change_entry: the fields to change. Each field you "
                                       "name is replaced whole — give the full corrected "
                                       "text, keeping everything still true about the "
                                       "entry; never a note about the correction. "
                                       + RELATIVE_REFERENCES},
            "new_name": {"type": "string"},
            "alias": {"type": "string"},
            "into": {"type": "string", "description": "merge: the log to merge into."},
        },
        "required": ["object", "action"],
    },
}
