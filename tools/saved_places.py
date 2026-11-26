"""
tools/saved_places.py — the user's places: what each is, what they think of it, what it is
for, where it is; and which of them to mention, when.

archive/plans/data_objects_phase3_build_plan_2026-11-25.md (phase 3 of
custom_logs_and_places_plan_2026-11-21.md, § 3.7). Rulings R7, R10, R11, R13, R15, R24, R25,
R27, R33 and Mike's eight choices of 2026-11-25/26.

WHAT THE USER SEES. "Bianco 43 — our go-to pizza" saves the place, with its public position,
the verdict and the occasion. Arriving there counts as arriving home does. When a meal, an
errand or a free slot comes up near a saved place that fits, the reply mentions it — and
mentions a place they said to avoid, to steer away (R10). A place they keep mentioning without
saving gets one question, on a card.

ONE WRITER (choice 5 — phase 1's lesson: an instruction does not hold a model). Every write to
the `places` object is made HERE, by code: from the Coordinator's PLACES directive (what the
user said, parsed in core/orchestrator.py `_resolve_places`), from an arrival
(tools/location.py), from capture's place facts (mentions), and from the save card. The
template says `writer: code`, so every model door refuses (tools/data_objects.py `code_kept`).

THE TIER (R24, R33). A saved place's coordinates are a PLACE's public position, not the
user's — but nothing here formats one for a prompt either. `places_near` returns names and
code-computed distances; `read_data_object` strips coordinate keys from the location tier;
the turn block below carries no number but metres. The user's rounded last position is read
from tools/location.py `last_position()` and never leaves this module except as a distance.

FILES (all under data/personas/{p}/, mode 600, sensitive tier)
    archive/places.json         the places — the data object's own rows
    place_mentions.jsonl        each raise (the reply named it) and the user's response
    place_unsaved.json          names mentioned but not saved, and the card's state

COST. Code only: $0 a turn. One Places Text Search per new name (price read at M3); none per
raise, none per arrival.

A8: no orchestrator code lives here; core/orchestrator.py `_resolve_places()` and
`_places_block()` stay in the pipeline beside `_resolve_data_objects()` / `_data_object_block()`.
"""
from __future__ import annotations

import difflib
import json
import logging
import math
import os
import re
import threading
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from core.persona import persona_data_dir, persona_scope, resolve_persona

logger = logging.getLogger(__name__)

OBJ = "places"
VERDICTS = ("go_to", "try", "avoid", "none")
SAVE_PLACE = "save_place"

_VERDICT_WORDS = {
    "go_to": "go_to", "go-to": "go_to", "goto": "go_to", "go to": "go_to",
    "favourite": "go_to", "favorite": "go_to", "regular": "go_to",
    "try": "try", "to try": "try", "want to try": "try", "try someday": "try",
    "avoid": "avoid", "not again": "avoid", "never again": "avoid",
    "none": "none", "": "none",
}

_DEFAULTS = {
    "default_radius_m": 75, "ambiguity_m": 300, "near_max_m": 1500, "errand_near_m": 1000,
    "last_position_fresh_hours": 3, "raise_cooldown_hours": 12, "lookup_budget_seconds": 1.5,
    "mention_threshold": 3, "mention_window_days": 30, "card_ttl_hours": 24,
}

# A save by the user, then capture reading the same turn's place fact a few seconds later,
# is one saying — not a mention to count (`record_mention`).
_SAID_GRACE_S = 180

_LOCK = threading.RLock()


# ---------------------------------------------------------------------------
# Seams and plumbing
# ---------------------------------------------------------------------------

def _DO():
    from tools import data_objects as DO
    return DO


def _limits() -> dict:
    out = dict(_DEFAULTS)
    try:
        out.update(_DO().limits().get("places") or {})
    except Exception:  # noqa: BLE001
        pass
    return out


def _now() -> datetime:
    return datetime.now()


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).isoformat(timespec="seconds")


def _dir(persona: str | None) -> Path:
    return persona_data_dir(resolve_persona(persona))


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6_371_008.8 * math.asin(min(1.0, math.sqrt(a)))


def _stat(persona: str | None, key: str, n: int = 1) -> None:
    """Per-day counts for the analytics row — counts only, never a name (Unseen cost 2:
    "never fires" must be told apart from "nothing nearby")."""
    try:
        path = _dir(persona) / "place_stats.json"
        with _LOCK:
            st = _read_json(path, {})
            day = st.setdefault(date.today().isoformat(), {})
            day[key] = int(day.get(key) or 0) + n
            for old in sorted(st)[:-60]:
                st.pop(old, None)
            _write_json(path, st)
    except Exception:  # noqa: BLE001
        pass


def day_stats(day: str, persona: str | None = None) -> dict:
    return dict((_read_json(_dir(persona) / "place_stats.json", {}) or {}).get(day) or {})


# ---------------------------------------------------------------------------
# The places object
# ---------------------------------------------------------------------------

def _obj() -> dict | None:
    return _DO().get(OBJ)


def _rows() -> list:
    return _DO()._rows(OBJ)


def _key(name: str) -> str:
    s = " ".join(str(name or "").casefold().replace("’", "'").split())
    return re.sub(r"^the\s+", "", s)


def _live(r: Any, include_hidden: bool = False) -> bool:
    return (isinstance(r, dict) and bool(r.get("name")) and not r.get("removed")
            and (include_hidden or not r.get("hidden")))


def find(name: str, include_hidden: bool = False, fuzzy: bool = False) -> dict | None:
    """The saved place this name means — its name or an alias; a close match (the
    data-objects ratio) only when a caller asks for one. Every WRITE resolves exactly: at 0.85,
    "Nando's Brighton" was Nando's Brixton, and saving it flipped Brixton's verdict (review
    2026-11-26 #5)."""
    k = _key(name)
    if not k:
        return None
    rows = [r for r in _rows() if _live(r, include_hidden)]
    for r in rows:
        if _key(r["name"]) == k or k in {_key(a) for a in r.get("aliases") or []}:
            return r
    if not fuzzy:
        return None
    ratio = float(_DO().limits().get("close_match_ratio") or 0.85)
    best, score = None, 0.0
    for r in rows:
        s = difflib.SequenceMatcher(None, k, _key(r["name"])).ratio()
        if s > score:
            best, score = r, s
    return best if score >= ratio else None


def occasion_kinds() -> list[str]:
    """Every user's base kinds (the template) plus this user's own (ruling 8)."""
    base: list[str] = []
    for t in _DO()._templates():
        if t["id"] == OBJ:
            base = [str(k) for k in t.get("occasion_kinds") or []]
    own = list((_obj() or {}).get("own_occasion_kinds") or [])
    return list(dict.fromkeys(base + own))


def _add_kind(kind: str) -> None:
    """A kind the user used that is not on their list joins it — never mapped onto the
    nearest base kind (Mike, ruling 8)."""
    DO = _DO()
    with DO._locked():
        objs, s = DO._materialise(OBJ, DO._stored())
        own = list(s.get("own_occasion_kinds") or [])
        if kind not in own:
            own.append(kind)
            s["own_occasion_kinds"] = own
            DO._save(objs)


def _slug(s: str, limit: int = 30) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s or "").casefold()).strip("_")[:limit]


# Other words for a base kind — the same kind, said another way. A meal is a meal whether the
# Coordinator writes "dinner" or "lunch"; without this, "dinner" became a kind of its own that
# no meal turn ever matched (review 2026-11-26 #4). The word is kept as the occasion's `what`.
# This is not ruling 8's "nearest kind": "climbing" is not a word for any base kind and is
# added as the user's own.
_SAME_KIND = {
    "dinner": "meal", "lunch": "meal", "breakfast": "meal", "brunch": "meal", "supper": "meal",
    "food": "meal", "eating": "meal", "eat": "meal", "restaurant": "meal", "takeaway": "meal",
    "cafe": "coffee", "café": "coffee", "tea": "coffee",
    "drink": "drinks", "pub": "drinks", "bar": "drinks",
    "shopping": "shop", "shops": "shop",
    "errands": "errand",
}
# A place's own kind says what it is for when the user gave no occasion ("Rossi's, never
# again" names a pizzeria, so it is avoided for meals).
_KIND_FROM_PLACE = {
    "restaurant": "meal", "pizzeria": "meal", "pizza": "meal", "bistro": "meal",
    "brasserie": "meal", "diner": "meal", "grill": "meal", "takeaway": "meal", "cafe": "coffee",
    "café": "coffee", "coffee": "coffee", "coffee shop": "coffee", "bakery": "coffee",
    "pub": "drinks", "bar": "drinks", "wine bar": "drinks", "shop": "shop", "supermarket": "shop",
    "pharmacy": "errand", "chemist": "errand", "post office": "errand", "bank": "errand",
}


def normalise_occasion(occ: Any) -> dict | None:
    """{kind, what?, near?} from a dict or a phrase. An unknown kind is ADDED to the user's
    kinds. "avoid" is a verdict, never an occasion (the plan's § 3.7 example corrected)."""
    if isinstance(occ, str):
        occ = {"kind": occ}
    if not isinstance(occ, dict):
        return None
    said = _slug(occ.get("kind") or "")
    kind = _SAME_KIND.get(said.replace("_", " "), said)
    if kind != said and not occ.get("what"):
        occ = {**occ, "what": said.replace("_", " ")}
    if not kind or kind in ("avoid", "none"):
        return None
    if kind not in occasion_kinds():
        _add_kind(kind)
    out = {"kind": kind}
    for k in ("what", "near"):
        v = " ".join(str(occ.get(k) or "").split())[:60]
        if v:
            out[k] = v
    return out


def normalise_verdict(v: Any) -> str | None:
    w = " ".join(str(v or "").casefold().replace("_", " ").split())
    hit = _VERDICT_WORDS.get(w) or _VERDICT_WORDS.get(w.replace(" ", "_"))
    return hit if hit in VERDICTS else None


def _write(item: dict, occurrence: dict | None = None) -> str:
    o = _obj()
    if o is None:
        return "Not recorded: no places object."
    return _DO().archive_write(o, item, occurrence=occurrence, by_code=True)


def positioned(persona: str | None = None) -> list[dict]:
    """Saved places that carry a public position, for tools/location.py `known_places()`:
    `{name, lat, lon, radius_m, source: "place", private}`. Hidden and removed never."""
    with persona_scope(resolve_persona(persona)):
        out = []
        dr = float(_limits()["default_radius_m"])
        for r in _rows():
            if not _live(r):
                continue
            try:
                lat, lon = float(r["lat"]), float(r["lon"])
            except (KeyError, TypeError, ValueError):
                continue
            out.append({"name": str(r["name"]), "lat": lat, "lon": lon,
                        "radius_m": float(r.get("radius_m") or dr), "source": "place",
                        "private": bool(r.get("private"))})
        return out


# ---------------------------------------------------------------------------
# Saving what the user said (the Coordinator's PLACES), and the lookup
# ---------------------------------------------------------------------------

def save(item: dict, source: str = "said", persona: str | None = None) -> dict:
    """Record a place the user named, synchronously and without a network call — the lookup
    is `locate()`, run beside the specialists. Returns {status, name, needs_lookup, changed?}.

    A name already saved updates that row (its stored name keeps the identity key). A hidden
    name the user now names is unhidden: they are saving it."""
    with persona_scope(resolve_persona(persona)):
        name = " ".join(str(item.get("name") or "").split())[:80]
        if not name:
            return {"status": "invalid", "error": "no name"}
        existing = find(name, include_hidden=True)
        entry: dict = {"name": existing["name"] if existing else name,
                       "last_said_at": _iso()}
        if not existing:
            entry["source"] = source
            entry["confirmed"] = False
        elif existing.get("hidden"):
            entry["hidden"] = False
        kind = " ".join(str(item.get("kind") or "").split())[:40]
        if kind:
            entry["kind"] = kind
        v = normalise_verdict(item.get("verdict")) if item.get("verdict") else None
        if v:
            entry["verdict"] = v
            entry["verdict_source"] = "stated"
        occ = normalise_occasion(item.get("occasion")) if item.get("occasion") else None
        if occ:
            entry["occasion"] = occ
            entry["occasion_source"] = "stated"
        notes = " ".join(str(item.get("notes") or "").split())[:300]
        if notes:
            entry["notes"] = notes
        before = dict(existing) if existing else {}
        msg = _write(entry)
        if msg.startswith("Not "):
            return {"status": "refused", "name": name, "error": msg}
        after = find(entry["name"], include_hidden=True) or {}
        _stat(persona, "places_saved" if not existing else "places_updated")
        changed = [f for f in ("verdict", "occasion")
                   if before and before.get(f) not in (None, "") and before.get(f) != after.get(f)]
        return {"status": "updated" if existing else "saved", "name": entry["name"],
                "needs_lookup": "lat" not in after, "changed": changed,
                "held": [f for f in ("verdict", "occasion") if after.get(f"pending_{f}")]}


def _home_point(persona: str | None) -> tuple[float, float] | None:
    try:
        from tools.location import place_named
        p = place_named("home", persona)
        return (float(p["lat"]), float(p["lon"])) if p else None
    except Exception:  # noqa: BLE001
        return None


def choose(candidates: list[dict], area: str, persona: str | None) -> dict:
    """The lookup's candidates → one, and whether it is ambiguous (Mike's choice 1): results
    more than `ambiguity_m` apart are different places with one name. Prefer the one whose
    address names the area the user said, else the one nearest home (computed here — no
    position is sent anywhere). Ambiguous → saved unconfirmed."""
    first = candidates[0]
    far = [c for c in candidates[1:]
           if _haversine_m(first["lat"], first["lon"], c["lat"], c["lon"])
           > float(_limits()["ambiguity_m"])]
    if not far:
        return {**first, "ambiguous": False}
    pool = [first] + far
    a = _key(area)
    if a:
        named = [c for c in pool if a in _key(c.get("address") or "")]
        if named:
            return {**named[0], "ambiguous": True}
    home = _home_point(persona)
    if home:
        pool.sort(key=lambda c: _haversine_m(home[0], home[1], c["lat"], c["lon"]))
    return {**pool[0], "ambiguous": True}


def locate(name: str, area: str = "", persona: str | None = None,
           relocate: bool = False) -> dict:
    """Look the place up by name (+ the area said) and store its public position on its row.
    Never overwrites a place that already has one. Returns {address, street?, ambiguous,
    confirmed} or {error}; never a coordinate."""
    persona = resolve_persona(persona)
    with persona_scope(persona):
        row = find(name, include_hidden=True)
        if row is None:
            return {"error": "not saved"}
        if "lat" in row and not relocate:
            return {"address": row.get("address"), "ambiguous": False,
                    "confirmed": bool(row.get("confirmed")), "already": True}
        from tools.places import geocode_candidates
        text = f"{row['name']} {area}".strip() if area and _key(area) not in _key(row["name"]) \
            else row["name"]
        res = geocode_candidates(text, 3)
        if res.get("no_key"):
            _stat(persona, "places_lookup_no_key")
        if "error" in res:
            # Remembered, so a later mention retries it (review 2026-11-26 #15b).
            _write({"name": row["name"], "lookup_failed_at": _iso()})
            return {"error": res["error"]}
        cands = res["candidates"]
        if relocate and "lat" in row:
            # "No, the one on Hill Street": never the branch it already was.
            cands = [c for c in cands if _haversine_m(c["lat"], c["lon"], float(row["lat"]),
                                                      float(row["lon"])) > 50] or cands
        pick = choose(cands, area, persona)
        history = {}
        if relocate and "lat" in row:
            # Edits never overwrite (plan § 3.2): the wrong branch stays in `previous`, which
            # every read strips of coordinates like the row itself.
            history = {"previous": list(row.get("previous") or []) + [
                {"value": {k: row[k] for k in ("lat", "lon", "radius_m", "address") if k in row},
                 "changed_at": _iso(), "reason": "the user said it was another one"}]}
        _write({"name": row["name"], **history, "lat": pick["lat"], "lon": pick["lon"],
                "radius_m": int(_limits()["default_radius_m"]),
                "address": pick.get("address") or "",
                "confirmed": not pick["ambiguous"] and not relocate,
                # Said once, on the turn the result is known or the next one (#15c).
                "ambiguous": bool(pick["ambiguous"]), "ambiguity_said": False,
                "lookup_failed_at": ""})
        _stat(persona, "places_located")
        return {"address": pick.get("address") or "", "ambiguous": pick["ambiguous"],
                "confirmed": not pick["ambiguous"]}


def unsaid_ambiguities(persona: str | None = None) -> list[dict]:
    """Places whose lookup found more than one by that name and the user has not yet been
    asked about — each returned once (marked said here)."""
    out = []
    with persona_scope(resolve_persona(persona)):
        for r in _rows():
            if _live(r) and r.get("ambiguous") and not r.get("confirmed") \
                    and not r.get("ambiguity_said") and "lat" in r:
                out.append({"name": r["name"], "address": r.get("address") or ""})
                _write({"name": r["name"], "ambiguity_said": True})
    return out


def set_flag(name: str, flag: str, value: bool = True, persona: str | None = None) -> str:
    """"Keep it private" / "forget that place" — by code, from the Coordinator's PLACES act.
    Forgetting is out of view, never deleted (R5, R20)."""
    with persona_scope(resolve_persona(persona)):
        row = find(name, include_hidden=True)
        if row is None:
            return "unknown"
        if flag == "removed":
            DO = _DO()
            with DO._locked():
                rows = _rows()
                for r in rows:
                    if r is not None and isinstance(r, dict) and r.get("name") == row["name"] \
                            and not r.get("removed"):
                        r["removed"] = {"at": _iso(), "reason": "the user asked"}
                path = DO._archive_file(OBJ)
                path.write_text(json.dumps(rows, indent=2))
                os.chmod(path, 0o600)
            return "removed"
        _write({"name": row["name"], flag: bool(value)})
        return flag


def confirm(name: str, persona: str | None = None) -> str:
    with persona_scope(resolve_persona(persona)):
        row = find(name, include_hidden=True)
        if row is None:
            return "unknown"
        _write({"name": row["name"], "confirmed": True, "ambiguous": False})
        return "confirmed"


# ---------------------------------------------------------------------------
# Occurrences — visits (an arrival) and mentions (capture's place facts)
# ---------------------------------------------------------------------------

def record_visit(name: str, at: str | None = None, persona: str | None = None) -> bool:
    """An arrival at a saved place: a visit occurrence, and an unconfirmed place confirmed —
    the user is where the saved position says. Zones have no row; nothing happens for them."""
    with persona_scope(resolve_persona(persona)):
        key = str(name or "").strip().casefold()
        # The stored name, exactly — never `find`'s normalised match: zone "home" is not the
        # saved place "The Home" 3 km away (review 2026-11-26 #6).
        row = next((r for r in _rows() if _live(r) and str(r["name"]).casefold() == key), None)
        if row is None or "lat" not in row:
            return False
        _write({"name": row["name"]}, occurrence={"at": at or _iso(), "kind": "visit"})
        if not row.get("confirmed"):
            _write({"name": row["name"], "confirmed": True})
        return True


def _recently_said(row: dict) -> bool:
    try:
        said = datetime.fromisoformat(str(row.get("last_said_at") or ""))
    except ValueError:
        return False
    return (_now() - said).total_seconds() < _SAID_GRACE_S


def on_place_fact(persona: str, name: str, quote: str = "") -> str:
    """Capture's `place` fact with a name (tools/capture.py). A saved place gets a mention
    occurrence; an unsaved name is counted toward the one question. Returns a content-free
    outcome. Never raises."""
    try:
        persona = resolve_persona(persona)
        with persona_scope(persona):
            name = " ".join(str(name or "").split())[:80]
            if not name or _obj() is None:
                return "place_unnamed"
            row = find(name, include_hidden=True)
            if row is not None and row.get("hidden"):
                # A declined name keeps counting, so it can be asked again once its count
                # doubles (choice 3); its mentions are carried over only if it is saved.
                return _count_unsaved(persona, row["name"], quote)
            if row is not None:
                if _recently_said(row):
                    return "place_just_saved"
                _write({"name": row["name"]}, occurrence={"at": _iso(), "kind": "mention"})
                _retry_lookup(persona, row)
                return "place_mentioned"
            return _count_unsaved(persona, name, quote)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[places] place fact not handled: {exc}")
        return "place_failed"


def _retry_lookup(persona: str, row: dict) -> None:
    """A saved place with no position whose last lookup failed over a day ago is looked up
    again, off the reply path. Never raises."""
    if "lat" in row:
        return
    try:
        failed = datetime.fromisoformat(str(row.get("lookup_failed_at") or ""))
    except ValueError:
        failed = None
    if failed is not None and _now() - failed < timedelta(days=1):
        return
    threading.Thread(target=lambda: _safe(locate, row["name"], persona=persona),
                     daemon=True, name="place_relookup").start()


def _safe(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[places] {getattr(fn, '__name__', 'call')} failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# "Keeps coming up" — an unsaved name mentioned 3 times in 30 days (Mike, choice 3)
# ---------------------------------------------------------------------------
#
#   counting ─ threshold ─▶ held ─ next user turn ─▶ open (a card) ─▶ yes | no (hidden) | expired
#   no / expired wait until the count doubles; nothing is deleted.

def _unsaved_path(persona: str) -> Path:
    return _dir(persona) / "place_unsaved.json"


def _load_unsaved(persona: str) -> dict:
    st = _read_json(_unsaved_path(persona), {})
    st.setdefault("names", {})
    return st


def _count_unsaved(persona: str, name: str, quote: str) -> str:
    lim = _limits()
    with _LOCK:
        st = _load_unsaved(persona)
        k = _key(name)
        rec = st["names"].setdefault(k, {"name": name, "mentions": [], "status": "counting",
                                         "id": uuid.uuid4().hex[:10]})
        rec["mentions"].append({"at": _iso(), "quote": " ".join(str(quote).split())[:160]})
        rec["mentions"] = rec["mentions"][-50:]
        since = (_now() - timedelta(days=float(lim["mention_window_days"]))).isoformat()
        n = sum(1 for m in rec["mentions"] if m["at"] >= since)
        threshold = int(lim["mention_threshold"])
        status = rec.get("status")
        if status == "counting" and n >= threshold:
            rec["status"] = "held"
        elif status in ("no", "expired") and n >= 2 * int(rec.get("count_at") or threshold):
            # A new offer, with its own id: the card layer refuses the identical refused
            # request (tools/confirm.py "a refusal stands"), and this is a new question —
            # asked because the count doubled, as phase 2's offers are.
            rec.update(status="held", id=uuid.uuid4().hex[:10])
        _write_json(_unsaved_path(persona), st)
        return "place_counted" if rec["status"] != "held" else "place_offer_held"


def _reconcile(persona: str, st: dict) -> None:
    """An open card's outcome from server state only, like the noticed-log offers: still
    pending → open; declined → no (the name is kept as a hidden place); otherwise expired."""
    from tools.confirm import declined, pending
    open_ = [r for r in st["names"].values() if r.get("status") == "open"]
    if not open_:
        return
    live = {p.get("token") for p in pending(persona)}
    refused = {(r.get("args") or {}).get("offer_id") for r in declined(None, persona)
               if r.get("action") == SAVE_PLACE}
    for r in open_:
        if r.get("token") in live:
            continue
        if r["id"] in refused:
            r["status"] = "no"
            with persona_scope(persona):
                if find(r["name"], include_hidden=True, fuzzy=False) is None:
                    _write({"name": r["name"], "hidden": True, "source": "said",
                            "confirmed": False})
        else:
            r["status"] = "expired"


def take_offer(persona: str | None, user_turn: bool) -> dict | None:
    """At the start of a real user turn's Synthesizer pass: raise the oldest held name's card
    and return what the reply should ask. One place card at a time, and none while another
    code-raised offer (a noticed list) is on screen — the app shows one card. Never raises."""
    if not user_turn:
        return None
    try:
        from tools import confirm as C
        persona = resolve_persona(persona)
        with _LOCK:
            st = _load_unsaved(persona)
            if not any(r.get("status") in ("held", "open") for r in st["names"].values()):
                return None           # nothing to ask or reconcile: no write on every turn
            _reconcile(persona, st)
            still = next((r for r in st["names"].values() if r.get("status") == "open"), None)
            if still is not None:
                _write_json(_unsaved_path(persona), st)
                return {"question": still.get("question", ""), "still_open": True}
            held = [r for r in st["names"].values() if r.get("status") == "held"]
            if not held or any(p.get("action") in C.OFFER_ACTIONS for p in C.pending(persona)):
                _write_json(_unsaved_path(persona), st)
                return None
            r = held[0]
            with persona_scope(persona):
                if find(r["name"], include_hidden=False, fuzzy=False) is not None:
                    r["status"] = "yes"          # saved meanwhile, in words
                    _write_json(_unsaved_path(persona), st)
                    return None
            n = len(r["mentions"])
            ttl = int(float(_limits()["card_ttl_hours"]) * 3600)
            card = C.request(SAVE_PLACE, {"offer_id": r["id"], "name": r["name"]},
                             f"Save “{r['name']}” as one of your places ({n} mentions)",
                             persona=persona, ttl_seconds=ttl)
            if card.get("status") != "PENDING_CONFIRMATION":
                _write_json(_unsaved_path(persona), st)
                return None
            r.update(status="open", token=card["confirm_token"], count_at=n,
                     question=(f"You've mentioned {r['name']} a few times — want me to save "
                               f"it as one of your places?"),
                     raised_at=_iso())
            _write_json(_unsaved_path(persona), st)
            return {"question": r["question"]}
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[places] place offer not raised: {exc}")
        return None


def save_offered_place(offer_id: str, name: str, persona: str | None = None,
                       confirm_token: str = ""):
    """The user tapped Yes on "Save X as one of your places": save it with its mentions
    carried over, and look it up. Spends the approval through `consume()`."""
    from tools.confirm import consume
    persona = resolve_persona(persona)
    ok, reason = consume(confirm_token, SAVE_PLACE, {"offer_id": offer_id, "name": name},
                         persona=persona)
    if not ok:
        return {"error": f"Place not saved: {reason}"}
    with _LOCK:
        st = _load_unsaved(persona)
        rec = next((r for r in st["names"].values() if r.get("id") == offer_id), None)
        if rec is None:
            return {"error": "Place not saved: that offer is no longer on record."}
        with persona_scope(persona):
            out = save({"name": name}, source="said", persona=persona)
            if out.get("status") not in ("saved", "updated"):
                return {"error": f"Place not saved: {out.get('error')}"}
            for m in rec.get("mentions", []):
                _write({"name": out["name"]}, occurrence={"at": m["at"], "kind": "mention"})
        rec["status"] = "yes"
        _write_json(_unsaved_path(persona), st)
    # Looked up off the /confirm request (review 2026-11-26 #15g); its address reaches the
    # user on a later turn, or the "which one?" question if there is more than one.
    threading.Thread(target=lambda: _safe(locate, out["name"], persona=persona),
                     daemon=True, name="place_lookup").start()
    return f"Saved {out['name']} as one of your places."


# ---------------------------------------------------------------------------
# Where the user is, or will be (R33: the last position is read here and nowhere else)
# ---------------------------------------------------------------------------

def _stamp(v: Any) -> datetime | None:
    try:
        from tools.day_plan import _local_stamp
        return _local_stamp(v)
    except Exception:  # noqa: BLE001
        try:
            return datetime.fromisoformat(str(v)).replace(tzinfo=None)
        except ValueError:
            return None


def _private_names(persona: str) -> set[str]:
    try:
        from tools.location import known_places
        return {k["name"].casefold() for k in known_places(persona) if k.get("private")}
    except Exception:  # noqa: BLE001
        return set()


def _home(persona: str) -> dict | None:
    p = _home_point(persona)
    return {"lat": p[0], "lon": p[1], "label": "home", "kind": "home"} if p else None


_LATER_DAY_RE = re.compile(r"\b(tomorrow|this weekend|at the weekend|next week|on (mon|tues|wednes|"
                           r"thurs|fri|satur|sun)day)\b", re.I)


def where_now(persona: str | None = None, user_text: str = "") -> dict | None:
    """{lat, lon, label, kind} — code only. A plan for another day is measured from home.
    Otherwise: the place arrived at today; else the rounded last report while fresh; else the
    next located block of today's plan within three hours that is a known place (no lookup on
    the reply path); else home — most plans start there (review 2026-11-26 #15d). A private
    place is never named in `label` (R24, review #7)."""
    persona = resolve_persona(persona)
    from tools import location as L
    try:
        if _LATER_DAY_RE.search(str(user_text or "")):
            return _home(persona)
        private = _private_names(persona)
        cz = L.current_zone(persona) or {}
        entered = _stamp(cz.get("entered_at"))
        if cz.get("zone") and cz["zone"] != L.AWAY and entered and entered.date() == date.today():
            p = L.place_named(cz["zone"], persona)
            if p:
                label = "" if p["name"].casefold() in private else p["name"]
                return {"lat": p["lat"], "lon": p["lon"], "label": label, "kind": "at"}
        last = L.last_position(persona)
        at = _stamp(last.get("at")) if last else None
        fresh = timedelta(hours=float(_limits()["last_position_fresh_hours"]))
        if last and at and timedelta(0) <= _now() - at <= fresh:
            return {"lat": last["lat"], "lon": last["lon"], "label": "", "kind": "near"}
        planned = _planned_location(persona)
        if planned:
            if planned["label"].casefold() in private:
                planned["label"] = ""
            return planned
        return _home(persona)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[places] where-now unavailable: {exc}")
    return None


def _plan_blocks(persona: str) -> list[dict]:
    try:
        from tools import day_plan as DP
        plan = DP._read_json(DP._plan_path(DP._today(), persona), None) or {}
        return sorted(plan.get("blocks") or [], key=lambda b: b.get("start") or "")
    except Exception:  # noqa: BLE001
        return []


def _planned_location(persona: str) -> dict | None:
    try:
        from tools import day_plan as DP
        from tools.location import place_named
        now = _now()
        for b in _plan_blocks(persona):
            loc = str(b.get("location") or "").strip()
            start = DP._dt(b.get("start"))
            if not loc or start is None or start < now or start - now > timedelta(hours=3):
                continue
            p = place_named(loc, persona) or place_named(loc.split(",", 1)[0], persona)
            if p:
                return {"lat": p["lat"], "lon": p["lon"], "label": p["name"], "kind": "planned",
                        "at": start.isoformat(timespec="minutes")}
    except Exception:  # noqa: BLE001
        pass
    return None


# ---------------------------------------------------------------------------
# places_near — code only, no model call (R25: relevance, not nearness)
# ---------------------------------------------------------------------------

def _mentions_path(persona: str) -> Path:
    return _dir(persona) / "place_mentions.jsonl"


def _mention_rows(persona: str) -> list[dict]:
    out = []
    try:
        for ln in _mentions_path(persona).read_text().splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                continue
    except OSError:
        pass
    return out


def _signature(row: dict) -> str:
    return json.dumps([row.get("verdict") or "none", row.get("occasion") or {}], sort_keys=True)


def occasion_kind(row: dict) -> str:
    """What a place is for: its occasion's kind; else what its own kind names (a pizzeria is
    for a meal); else "" — a place nobody said the use of. An AVOID place with neither is
    avoided for anything ("never again" needs no occasion — review 2026-11-26 #4)."""
    occ = row.get("occasion") or {}
    k = occ.get("kind") if isinstance(occ, dict) else None
    if k:
        return str(k)
    kind = " ".join(str(row.get("kind") or "").casefold().split())
    hit = _KIND_FROM_PLACE.get(kind) or next(
        (v for w, v in _KIND_FROM_PLACE.items() if re.search(rf"\b{re.escape(w)}\b", kind)), "")
    if hit:
        return hit
    return "any" if row.get("verdict") == "avoid" else ""


def _occasion_matches(row: dict, kind: str) -> bool:
    rk = occasion_kind(row)
    if not rk:
        return False
    return rk == kind or rk == "any" or kind == "any"


def _open_at(row: dict, at: datetime | None) -> bool | None:
    hours = row.get("hours")
    if not hours:
        return None
    try:
        from tools.places import _open_at as open_at
        return open_at({"regularOpeningHours": {"periods": hours}}, at or _now(), date.today())
    except Exception:  # noqa: BLE001
        return None


def _round_m(d: float) -> int:
    """Metres as a person would say them — to 50 m, or 100 m past a kilometre. Coarser than
    the raw figure on purpose: three exact distances to named public places from the last
    reported point would pin that point (review 2026-11-26, coordinates #3)."""
    step = 50 if d < 1000 else 100
    return int(max(step, round(d / step) * step))


def places_near(where: dict, occasion: str, at: datetime | None = None, planned: bool = False,
                persona: str | None = None, limit: int = 4) -> list[dict]:
    """Saved places near `where` that fit `occasion`. Returns `{name, distance_m, verdict,
    occasion, open, signature}` — names and metres, NEVER a coordinate.

    - occasion kind must match (`any` matches every kind; see `occasion_kind`);
    - private and hidden never; removed never; an ambiguous place nobody has confirmed never
      (it may be the wrong branch — R15);
    - `avoid` is returned whenever its occasion matches (R10 — to steer away), and a decline
      never silences it;
    - `try` only when the occasion is an actual plan (R25), never on a passing walk;
    - closed then, where hours are known, is left out;
    - a declined raise waits until the place's verdict or occasion changes; a raise neither
      taken up nor declined is not repeated for the same occasion within the cooldown."""
    persona = resolve_persona(persona)
    lim = _limits()
    with persona_scope(persona):
        raises = _mention_rows(persona)
        cool = _now() - timedelta(hours=float(lim["raise_cooldown_hours"]))
        out = []
        for r in _rows():
            if not _live(r) or r.get("private") or "lat" not in r:
                continue
            if r.get("ambiguous") and not r.get("confirmed"):
                continue
            if not _occasion_matches(r, occasion):
                continue
            v = r.get("verdict") or "none"
            if v == "try" and not planned:
                continue
            try:
                d = _haversine_m(float(where["lat"]), float(where["lon"]),
                                 float(r["lat"]), float(r["lon"]))
            except (KeyError, TypeError, ValueError):
                continue
            if d > float(lim["near_max_m"]):
                continue
            opened = _open_at(r, at)
            if opened is False and v != "avoid":
                continue
            mine = [m for m in raises if m.get("place") == r["name"]]
            sig = _signature(r)
            if v != "avoid" and any(m.get("response") == "declined" and m.get("signature") == sig
                                    for m in mine):
                continue
            if any(m.get("response") in ("none", "pending") and m.get("occasion") == occasion
                   and str(m.get("at") or "") >= cool.isoformat() for m in mine):
                continue
            occ = dict(r.get("occasion") or {})
            occ.setdefault("kind", occasion_kind(r))
            out.append({"name": r["name"], "distance_m": _round_m(d), "verdict": v,
                        "occasion": occ, "open": opened, "signature": sig})
        out.sort(key=lambda p: (p["verdict"] != "go_to", p["distance_m"]))
        return out[:limit]


def errands_near(where: dict, persona: str | None = None) -> list[dict]:
    """Open tasks whose place (the task `zone`, choice 6) is a SAVED place within
    `errand_near_m` — "you're near the chemist and the prescription is ready" is this join,
    in code. Zones (home, office) are not errands. Names, metres and the task's words only."""
    persona = resolve_persona(persona)
    lim = _limits()
    out = []
    try:
        from tools.obligations import _load
        with persona_scope(persona):
            tasks = [t for t in _load(persona) if t.get("status") == "open" and t.get("zone")]
            if not tasks:
                return []
            spots = {p["name"].casefold(): p for p in positioned(persona) if not p["private"]}
            today = date.today().isoformat()
            for t in tasks:
                p = spots.get(str(t["zone"]).casefold())
                if p is None:
                    continue
                if str(t.get("not_before") or t.get("deferred_until") or "") > today:
                    continue
                d = _haversine_m(float(where["lat"]), float(where["lon"]), p["lat"], p["lon"])
                if d <= float(lim["errand_near_m"]):
                    out.append({"name": p["name"], "distance_m": _round_m(d),
                                "task": str(t.get("what") or "")[:80], "task_id": t.get("id")})
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[places] errands not checked: {exc}")
    return out


# ---------------------------------------------------------------------------
# When a turn calls for places (Mike's choice 2 — attached by code, not a tool)
# ---------------------------------------------------------------------------

_MEAL_RE = re.compile(
    r"\b(dinner|lunch|brunch|breakfast|supper|eat(ing)? out|grab (a )?(bite|food)|"
    r"somewhere to eat|where (should|shall|can|do) (we|i) eat|restaurant|takeaway|take-away|"
    r"pizza|curry|sushi|ramen|burger|tapas|hungry|book a table|table for)\b", re.I)
_COFFEE_RE = re.compile(r"\b(coffee|café|cafe|flat white|latte|cappuccino)\b", re.I)
_DRINKS_RE = re.compile(r"\b(a drink|drinks|pub|bar|pint|cocktail|wine bar)\b", re.I)
_PAST_RE = re.compile(r"\b(had|ate|we went|i went|was (great|good|awful|bad)|last night)\b", re.I)
_PLAN_RE = re.compile(
    r"\b(tonight|this evening|later|tomorrow|this weekend|should (we|i)|shall (we|i)|"
    r"where (to|should|shall|can)|any (ideas|suggestions)|suggest|recommend|thinking of|"
    r"plan(ning)?|book|fancy|free time|what (should|can) (i|we) do)\b", re.I)
# A free slot is raised only on a turn asking what to do with time — not on any planning word
# ("book the dentist for tomorrow" is not a request for an outing — review 2026-11-26 #11).
_FREE_RE = re.compile(
    r"\b(free time|what (should|can|shall) (i|we) do|any (ideas|suggestions)|something to do|"
    r"at a loose end|bored|kill (some )?time|fancy (doing|going))\b", re.I)


def occasion_for_turn(user_text: str) -> tuple[str, bool] | None:
    """(occasion kind, planned) from the user's words, or None. A meal said in the past tense
    ("had pizza last night") is a log, not an occasion."""
    t = str(user_text or "")
    if not t.strip():
        return None
    planned = bool(_PLAN_RE.search(t))
    if _PAST_RE.search(t) and not planned:
        return None
    if _MEAL_RE.search(t):
        return "meal", planned or "?" in t
    if _COFFEE_RE.search(t):
        return "coffee", planned or "?" in t
    if _DRINKS_RE.search(t):
        return "drinks", planned or "?" in t
    return None


def _occasion_from_saved(user_text: str) -> tuple[str, bool] | None:
    """A user's own occasion, or one with no turn regex (shop, errand, "climbing"), fires when
    the turn names it or what a saved place is for ("bouldering") — review 2026-11-26 #4."""
    t = str(user_text or "").casefold()
    if not t.strip() or (_PAST_RE.search(t) and not _PLAN_RE.search(t)):
        return None
    for r in _rows():
        if not _live(r):
            continue
        occ = r.get("occasion") or {}
        k = occ.get("kind") if isinstance(occ, dict) else ""
        if not k or k in ("meal", "coffee", "drinks", "any"):
            continue
        words = {k.replace("_", " "), str(occ.get("what") or "").casefold()}
        if any(w and len(w) >= 4 and re.search(rf"\b{re.escape(w)}\b", t) for w in words):
            return k, True
    return None


def _meal_soon(persona: str) -> bool:
    """A meal in today's plan within the next three hours (ruling 2's third trigger)."""
    try:
        from tools import day_plan as DP
        now = _now()
        for b in _plan_blocks(persona):
            start = DP._dt(b.get("start"))
            if start and now <= start <= now + timedelta(hours=3) \
                    and _MEAL_RE.search(str(b.get("title") or "")):
                return True
    except Exception:  # noqa: BLE001
        pass
    return False


def _free_minutes_now(persona: str) -> int:
    """Minutes free from now to the next fixed boundary in today's stored plan — read, never
    rebuilt (the reply's own day-plan pass builds it)."""
    try:
        from tools import day_plan as DP
        now = _now()
        blocks = _plan_blocks(persona)
        if any(DP._dt(b["start"]) <= now < DP._dt(b["end"]) and b.get("kind") != "task"
               for b in blocks if b.get("start") and b.get("end")):
            return 0
        nxt = next((DP._dt(b["start"]) for b in blocks
                    if b.get("start") and DP._dt(b["start"]) > now and b.get("kind") != "task"),
                   None)
        plan = DP._read_json(DP._plan_path(DP._today(), persona), None) or {}
        end = nxt or DP._dt((plan.get("window") or {}).get("bed"))
        return int((end - now).total_seconds() // 60) if end else 0
    except Exception:  # noqa: BLE001
        return 0


def _fmt_distance(m: int) -> str:
    return f"{m} m" if m < 1000 else f"{m / 1000:.1f} km"


def _fmt_verdict(p: dict) -> str:
    occ = p.get("occasion") or {}
    what = occ.get("what") or occ.get("kind") or ""
    v = p.get("verdict")
    if v == "go_to":
        return f"their go-to{' for ' + what if what else ''}"
    if v == "try":
        return f"they want to try it{' — ' + what if what else ''}"
    if v == "avoid":
        return f"AVOID ({what or 'any'}) — name it only to steer away"
    return f"saved{' — ' + what if what else ''}"


def turn_places(persona: str | None, user_text: str, user_turn: bool) -> dict:
    """What this turn should know about the user's places, decided in code: the places near
    where they are (or will be) that fit what the turn is about, and errands near them.
    Returns {"lines": [...], "attached": [{name, occasion, signature, verdict}]}."""
    out: dict = {"lines": [], "attached": []}
    if not user_turn:
        return out
    persona = resolve_persona(persona)
    try:
        with persona_scope(persona):
            if _obj() is None or not any(_live(r) for r in _rows()):
                return out
            text = str(user_text or "")
            where = where_now(persona, text)
            if where is None:
                return out
            hit = occasion_for_turn(text) or _occasion_from_saved(text)
            if hit is None and _PLAN_RE.search(text) and _meal_soon(persona):
                hit = ("meal", True)
            if hit is None and _FREE_RE.search(text) and _free_minutes_now(persona) >= 60:
                hit = ("activity", True)
            places = places_near(where, hit[0], planned=hit[1], persona=persona) if hit else []
            errands = errands_near(where, persona) if where["kind"] in ("at", "near") else []
            raised = {(m.get("place"), m.get("task")) for m in _mention_rows(persona)
                      if str(m.get("at") or "")[:10] == date.today().isoformat()}
            errands = [e for e in errands if (e["name"], e["task"]) not in raised]
            for p in places:
                out["lines"].append(f"- {p['name']} — {_fmt_distance(p['distance_m'])} — "
                                    f"{_fmt_verdict(p)}"
                                    + (" — open then" if p.get("open") is True else ""))
                out["attached"].append({"name": p["name"], "occasion": hit[0],
                                        "signature": p["signature"], "verdict": p["verdict"]})
            for e in errands:
                out["lines"].append(f"- {e['name']} — {_fmt_distance(e['distance_m'])} — an "
                                    f"open task is done there: \"{e['task']}\"")
                out["attached"].append({"name": e["name"], "task": e["task"],
                                        "occasion": "errand", "signature": ""})
            if out["lines"]:
                rel = {"at": "where the user is", "near": "where the user last reported being",
                       "planned": "where the user is due to be next",
                       "home": "home"}[where["kind"]]
                label = where.get("label") if where["kind"] != "home" else ""
                out["lines"].insert(0, f"Measured from {rel}" + (f" ({label})" if label else "")
                                    + ":")
                _stat(persona, "places_attached")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[places] turn places not built: {exc}")
        return {"lines": [], "attached": []}
    return out


def _named(name: str, text: str) -> bool:
    """The place is named in the text: its full name, or its first word when that is
    distinctive ("Bianco" for "Bianco 43") — review 2026-11-26 #15f."""
    low = text.casefold()
    n = name.casefold()
    if n in low:
        return True
    first = re.sub(r"^the\s+", "", n).split()[0] if n.split() else ""
    first = re.sub(r"['’]s$", "", first)
    return len(first) >= 4 and bool(re.search(rf"\b{re.escape(first)}", low))


# A decline is read only when it is ABOUT the place (review 2026-11-26 #3): a bare "no" answers
# whatever else the reply asked ("did you take your meds?" — "no, not yet").
_DECLINE_RE = re.compile(
    r"\b(not (tonight|today|there|that one|that place|in the mood for)|rather not|"
    r"something else|somewhere else|don'?t fancy|not feeling it|another time|skip it|"
    r"not keen|give it a miss|not that)\b", re.I)
_ACCEPT_RE = re.compile(r"\b(sounds good|good (idea|shout)|let'?s (go|do)|perfect|"
                        r"book (it|us)|we'?ll go)\b", re.I)


def note_reply(persona: str | None, reply: str, attached: list[dict]) -> int:
    """After the reply: an attached place the reply NAMED was raised — recorded, with its
    response pending until the user's next turn. Attached but unnamed is not a raise."""
    if not attached or not reply:
        return 0
    persona = resolve_persona(persona)
    n = 0
    for a in attached:
        if not _named(a["name"], reply):
            continue
        _append(_mentions_path(persona), {"at": _iso(), "place": a["name"],
                                          "occasion": a.get("occasion"),
                                          "task": a.get("task"),
                                          "verdict": a.get("verdict"),
                                          "signature": a.get("signature", ""),
                                          "response": "pending"})
        n += 1
    if n:
        _stat(persona, "places_raised", n)
    return n


def note_response(persona: str | None, user_text: str, user_turn: bool) -> None:
    """The user's next turn answers the raises still pending: declined, accepted or none —
    read in code from their words. A decline needs the user to turn the PLACE down: its name
    beside a declining phrase, or a declining phrase when only one place was raised. An avoid
    raise is never declined — agreeing to steer away ("no, definitely not there") must not
    silence the warning (R10). None counts as neither."""
    if not user_turn:
        return
    persona = resolve_persona(persona)
    path = _mentions_path(persona)
    rows = _mention_rows(persona)
    pending = [r for r in rows if r.get("response") == "pending"]
    if not pending:
        return
    t = str(user_text or "")
    offered = [r for r in pending if r.get("verdict") != "avoid"]
    for r in pending:
        named = _named(r["place"], t)
        if r.get("verdict") == "avoid":
            r["response"] = "none"
        elif _DECLINE_RE.search(t) and (named or len(offered) == 1):
            r["response"] = "declined"
        elif _ACCEPT_RE.search(t) and (named or len(offered) == 1):
            r["response"] = "accepted"
        else:
            r["response"] = "none"
        r["answered_at"] = _iso()
    with _LOCK:
        tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
        tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
