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
          "agent_config", "log", "goals", "calendar")
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


def _stored() -> list[dict]:
    data = _read_json(_registry_path(), {"objects": []})
    return [_complete(o) for o in (data.get("objects") or []) if isinstance(o, dict)]


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


def archive_write(o: dict, item: dict, occurrence: dict | None = None) -> str:
    """Write one entry into an archive-store object under its identity rule, and clear one
    pending marker for it. Shared by write_data_object and write_archive (registered
    categories), so the two doors cannot disagree."""
    item = dict(item or {})
    today = date.today().isoformat()
    with _locked():
        path = _archive_file(o["id"])
        rows = _rows(o["id"])
        key = _identity_key(item)
        if occurrence is not None:
            row = next((r for r in rows if isinstance(r, dict) and key
                        and _identity_key(r) == key), None)
            if row is None:
                row = {**item, "date_added": item.get("date_added") or today}
                rows.append(row)
            occ = {"at": str(occurrence.get("at") or today),
                   "notes": str(occurrence.get("notes") or "")}
            row.setdefault("occurrences", []).append(occ)
            row["date_updated"] = today
            msg = f"Recorded another occurrence in {o['name']}."
        elif o.get("identity") == "occurrence":
            item["date_added"] = item.get("date_added") or today
            item.setdefault("recorded_at", datetime.now().isoformat(timespec="seconds"))
            rows.append(item)
            msg = f"Added an entry to {o['name']} (entry {len(rows)})."
        else:
            row = next((r for r in rows if isinstance(r, dict) and key
                        and _identity_key(r) == key), None)
            if row is not None:
                for k, v in item.items():
                    if v not in (None, "", [], {}):
                        row[k] = v
                row["date_updated"] = today
                msg = (f"Updated the existing {key.split(':', 1)[0]}-matched entry in "
                       f"{o['name']} — fields merged, no duplicate added.")
            else:
                item["date_added"] = item.get("date_added") or today
                rows.append(item)
                msg = f"Added an entry to {o['name']} (entry {len(rows)})."
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(rows, f, indent=2)
        os.chmod(path, 0o600)
        if not o.get("created") and str(o.get("origin", "")).startswith("template:"):
            objs, _ = _materialise(o["id"], _stored())
            _save(objs)
        _clear_one_pending(o["id"])
    return msg


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
                 count_only: bool = False, limit: int = 0) -> dict:
    rows = _rows(o["id"])
    numbered = [{"n": i + 1, **r} if isinstance(r, dict) else {"n": i + 1, "value": r}
                for i, r in enumerate(rows)]
    if since or until:
        # Compared at the entry's own precision: an `at` of "2024" (a year, as the relative-
        # reference rule records "two years ago") falls inside 2024-01-01..2024-12-31.
        numbered = [r for r in numbered if any(
            (not since or d >= since[:len(d)]) and (not until or d <= until[:len(d)])
            for d in _dates_of(r))]
    if contains:
        needle = contains.casefold()
        numbered = [r for r in numbered if needle in json.dumps(r, ensure_ascii=False).casefold()]
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
    out["entries"] = numbered[-cap:]
    if _is_location(o):
        out = _strip_coordinates(out)
    return out


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


def _simple(module: str, fn: str, **kw) -> Callable[[dict, str, dict], Any]:
    def run(o: dict, agent: str, f: dict) -> Any:
        mod = __import__(module, fromlist=[fn])
        return getattr(mod, fn)(**kw)
    return run


_NATIVE_READERS: dict[str, Callable[[dict, str, dict], Any]] = {
    "log": _read_log_object,
    "calendar": _read_calendar_object,
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
                            count_only=count_only, limit=limit)
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
            row["entries"] = len(_rows(o["id"]))
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
    if o.get("status") == "archived":
        return f"Not recorded: {o['name']} is archived. Unarchive it first."
    if action == "add_field":
        if not field:
            return "Not recorded: name the field to add."
        with _locked():
            objs, s = _materialise(o["id"], _stored())
            s["fields"].setdefault(field, "text")
            _save(objs)
        return f"{o['name']} now has a '{field}' field. Earlier entries are unchanged."
    if not isinstance(entry, dict) or not entry:
        return "Not recorded: the entry is empty."
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
                      into: str = "") -> str:
    """Change an entry (keeping history), rename, add an alias, archive or unarchive, mark
    private or not, or merge into another log. Nothing is deleted."""
    agent = _caller()
    o = resolve(object, follow=(action != "unarchive"))
    if o is None:
        return f"Not changed: no log called '{object}'."
    ok, why = may_read(agent, o)
    if not ok:
        return f"Not changed: {why}."
    now = datetime.now().isoformat(timespec="seconds")
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
            prev = {k: row.get(k) for k in changes}
            row.update(changes)
            row.setdefault("previous", []).append({"value": prev, "changed_at": now})
            row["date_updated"] = now[:10]
            with open(_archive_file(o["id"]), "w") as f:
                json.dump(rows, f, indent=2)
            os.chmod(_archive_file(o["id"]), 0o600)
        return f"Changed entry {entry} in {o['name']}; the earlier value is kept."
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
    return msg


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
        "read_data_object) with `changes` — the old value is kept; 'rename' (`new_name`); "
        "'add_alias' (`alias`); 'archive' takes it out of the lists without deleting "
        "anything, 'unarchive' brings it back; 'private' keeps it out of every list; "
        "'merge' moves its entries into another log (`into`). Nothing is ever deleted."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "object": {"type": "string"},
            "action": {"type": "string",
                       "enum": ["change_entry", "rename", "add_alias", "archive",
                                "unarchive", "private", "public", "merge"]},
            "entry": {"type": "integer", "description": "change_entry: the entry number."},
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
