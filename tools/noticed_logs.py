"""
tools/noticed_logs.py — logs Metatron notices the user keeps, offered on a card; and the derived
writer, in shadow.

archive/plans/data_objects_phase2_build_plan_2026-11-22.md (phase 2 of
custom_logs_and_places_plan_2026-11-21.md). Rulings R5, R21, R28, R29, R34 (Mike, 2026-11-21).

WHAT THE USER SEES. When they keep mentioning a kind of thing no log holds, the next reply asks
once — "Want me to start a list of the places you've mentioned wanting to try?" — and a card in
the app carries the answer. Yes starts the list with what they already said filed in. No is
remembered. "That belongs in my X list" turns the offer into one to keep those facts in X.

THE RULE IT IS BUILT ON (phase 1, three failed holds — archive/PROJECT_LOG.md § 11-22 second):
every write to a user's log here is made by CODE, an unbound caller. One model judgement — the
matcher, `data_object_matcher` (bulk tier, bare, empty grant) — decides only whether a category
already has a home, deserves a new list, is not a list, or repeats an earlier offer. Code counts,
holds, raises the card, files the facts and records the outcome. The answer is the card, never
the reply's wording.

THE LIFE OF AN OFFER (`capture/noticed.json`, sensitive tier — it carries the user's topics)

    matching ─ matcher ─▶ held ─ next user turn ─▶ open (a card) ─▶ yes | failed | no | expired
          │                                          └─ "belongs in X" ─▶ superseded (+ an alias offer)
          └▶ none (not a list) | home (a store fits) | same (an earlier offer) | matcher_failed

  - The card is raised at the NEXT real user turn, not at detection: a card raised between turns
    would sit on screen before anything asked the question (review 2026-11-22, § 2.1).
  - No, none and home stand until the held count doubles; expired and failed until
    `noticed_raise_count` more facts arrive; matcher_failed is retried once.
  - Outcomes are read from server state only (`reconcile`): a token still pending is open; an
    `offer_id` in the declined ledger is no; otherwise expired. Yes/failed/superseded are set by
    the code that caused them, under the same lock.

LOCK ORDER: this module's own lock (`capture/noticed.lock`), then capture's (outcome rows), the
confirm store's, then the data-object registry's. Capture never calls in here holding its own
lock, so nothing takes them in another order. Capture's lock is an fcntl lock on a fresh file
handle and is NOT re-entrant — which is why the offer state does not share it.

A8: no orchestrator code lives here; core/orchestrator.py `_take_log_offer()` and
`_offer_receipt()` stay in the pipeline beside `_unsaved_log_notes()`.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import logging
import re
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta

from core.persona import persona_scope, resolve_persona

logger = logging.getLogger(__name__)

AGENT = "data_object_matcher"
CREATE, ALIAS = "create_data_object", "alias_data_object"

# Tests set this False so the matcher runs inline against a stub.
MATCH_IN_BACKGROUND = True

_STALE_MATCHING_S = 600          # a `matching` offer older than this was orphaned by a restart
_MAX_FACTS_SHOWN = 3             # held summaries the matcher sees, to name the list well
_IDENT_RE = re.compile(r"\b[a-z]+_[a-z_]+\b")


# ---------------------------------------------------------------------------
# Seams
# ---------------------------------------------------------------------------

def _cap():
    from tools import capture
    return capture


def _cfg() -> dict:
    return _cap().config()


def _on(cfg: dict) -> bool:
    return bool(cfg.get("enabled")) and str(cfg.get("noticed_logs", "ask")).lower() == "ask"


def _call_matcher(payload: str, persona: str) -> str | None:
    """One bulk-tier call. Its own `source="capture"` trace, like the extractor's backfill
    calls, so A9 does not count it as a session; the spend guard is checked first.
    Returns None when the call could not be made — the spend guard, a provider error, an
    empty reply — which is not the matcher's judgement and must not count against the
    category (diff review F5)."""
    from core import trace as _tr
    from core.orchestrator import run_session
    C = _cap()
    if not C._within_spend():
        return None
    owned = _tr.start_request_trace("noticed-log matcher", persona, is_proactive=True,
                                    source="capture")
    try:
        raw = run_session(AGENT, user_input=payload, persona=persona, complexity="quick",
                          bare=True, proactive=True)
        return raw if (raw or "").strip() else None
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[noticed] matcher call failed: {exc}")
        return None
    finally:
        if owned is not None:
            _tr.finish_request_trace("")
        _tr.set_trace(None)


def _now() -> datetime:
    return _cap()._now()


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def _path(persona: str):
    return _cap()._dir(persona) / "noticed.json"


_TLOCK = threading.RLock()
_HELD: dict[str, list] = {}


@contextmanager
def _locked(persona: str):
    """Exclusive across threads and processes, re-entrant within a thread (the
    tools/data_objects.py `_locked` pattern) — the executors, the detector and the
    matcher's write-back all take it, sometimes nested."""
    with _TLOCK:
        key = str(_path(persona))
        held = _HELD.get(key)
        if held:
            held[1] += 1
            try:
                yield
            finally:
                held[1] -= 1
            return
        fh = open(_cap()._dir(persona) / "noticed.lock", "a+")
        try:
            fcntl.flock(fh, fcntl.LOCK_EX)
            _HELD[key] = [fh, 1]
            try:
                yield
            finally:
                _HELD.pop(key, None)
                fcntl.flock(fh, fcntl.LOCK_UN)
        finally:
            fh.close()


def _load(persona: str) -> dict:
    st = _cap()._read_json(_path(persona), {})
    st.setdefault("offers", [])
    return st


def _save(persona: str, st: dict) -> None:
    _cap()._write_json(_path(persona), st)


def offers(persona: str) -> list[dict]:
    return list(_load(persona)["offers"])


def _row(persona: str, offer: dict) -> None:
    """Content-free: what kind of offer and how it ended — never a category or a name."""
    _cap()._row(persona, row="offer", kind=offer.get("kind") or "-",
                outcome=offer.get("status"))


def _held_rows(persona: str, categories, since: str = "") -> list[dict]:
    cats = set(categories)
    return [r for r in _cap()._read_uncategorised(persona, since) if r.get("category") in cats]


def _latest(st: dict, category: str) -> dict | None:
    """The newest offer carrying this category, following a `same` verdict to its target."""
    # A "belongs in X" alias offer that was declined or ignored hands the topic back to the
    # list offer it replaced (reconciled to `expired`): the user never answered that one
    # (diff review F6).
    hits = [o for o in st["offers"] if category in o.get("categories", [])
            and not (o.get("parent") and o.get("status") in ("no", "expired"))]
    if not hits:
        return None
    o = hits[-1]
    seen = set()
    while o.get("status") == "same" and o.get("same_as") and o["id"] not in seen:
        seen.add(o["id"])
        nxt = next((x for x in st["offers"] if x["id"] == o["same_as"]), None)
        if nxt is None:
            break
        o = nxt
    return o


def _may_offer_again(persona: str, o: dict, cfg: dict) -> bool:
    n = int(cfg.get("noticed_raise_count", 3))
    status = o.get("status")
    total = len(_held_rows(persona, o.get("categories", [])))
    at = int(o.get("count_at") or 0)
    if status == "matching":
        try:
            age = (_now() - datetime.fromisoformat(o["created"])).total_seconds()
        except (KeyError, ValueError):
            age = _STALE_MATCHING_S + 1
        return age > _STALE_MATCHING_S
    if status in ("held", "open", "yes", "superseded", "same"):
        return False
    if status in ("no", "none", "home"):
        return total >= 2 * max(at, 1)
    if status in ("expired", "failed"):
        return total >= at + n
    if status == "deferred":
        return True                     # the call could not be made — try again next time
    if status == "matcher_failed":
        # One retry; after that the bad-answer topic waits for its count to double, like a
        # "none" — never closed for good (diff review F5).
        return int(o.get("retries") or 0) < 2 or total >= 2 * max(at, 1)
    return False


# ---------------------------------------------------------------------------
# The detector (plan § 3.1) — code, no model
# ---------------------------------------------------------------------------

def consider(persona: str, category: str) -> dict | None:
    """Called after capture keeps an `other` fact. When its category reaches the threshold and
    nothing rules it out, start one matcher judgement (off the reply's path). Never raises."""
    try:
        cfg = _cfg()
        if not _on(cfg) or not category:
            return None
        window = int(cfg.get("noticed_window_days", 30))
        since = (_now() - timedelta(days=window)).isoformat()
        if len(_held_rows(persona, [category], since)) < int(cfg.get("noticed_raise_count", 3)):
            return None
        from tools import data_objects as DO
        with persona_scope(persona):
            if DO.resolve(category) is not None:
                return None                     # it has a home — an alias found it
        C = _cap()
        with _locked(persona):
            st = _load(persona)
            _reconcile(persona, st)
            prior = _latest(st, category)
            if prior is not None and not _may_offer_again(persona, prior, cfg):
                _save(persona, st)
                return None
            judge = True
            if prior is not None and prior.get("status") in ("matching", "matcher_failed",
                                                             "deferred"):
                # Re-ask the same record — an orphan a restart left `matching`, a deferred
                # call, or one retry of a bad answer — rather than appending a second one.
                if prior.get("status") == "matcher_failed":
                    prior["retries"] = int(prior.get("retries") or 0) + 1
                if category not in prior.get("categories", []):
                    prior["categories"] = sorted(set(prior["categories"]) | {category})
                prior["status"] = "matching"
                prior["created"] = _now().isoformat(timespec="seconds")
                offer = prior
            elif prior is not None and prior.get("kind") in ("create", "alias"):
                # Offered before and not taken (no, expired, failed): the matcher already
                # judged this topic. Asking it again — shown its own earlier offer — answers
                # "the same", and the topic could never come back (diff review F1). So the
                # same verdict is held again, with no model call.
                cats = sorted(set(prior.get("categories", [])) | {category})
                offer = {k: prior[k] for k in ("kind", "name", "description", "ask",
                                               "identity", "log", "about") if k in prior}
                offer.update(id=uuid.uuid4().hex[:10], categories=cats, status="held",
                             count_at=len(_held_rows(persona, cats)), again_of=prior["id"],
                             created=_now().isoformat(timespec="seconds"), retries=0)
                st["offers"].append(offer)
                judge = False
            else:
                cats = sorted(set((prior or {}).get("categories", [])) | {category})
                offer = {"id": uuid.uuid4().hex[:10], "categories": cats, "status": "matching",
                         "kind": None, "count_at": len(_held_rows(persona, cats)),
                         "created": _now().isoformat(timespec="seconds"), "retries": 0}
                st["offers"].append(offer)
            _save(persona, st)
        if not judge:
            return offer
        if MATCH_IN_BACKGROUND:
            threading.Thread(target=_judge, args=(persona, offer["id"]), daemon=True,
                             name="noticed-matcher").start()
        else:
            _judge(persona, offer["id"])
        return offer
    except Exception as exc:  # noqa: BLE001 — never takes a turn down
        logger.warning(f"[noticed] consider failed: {exc}")
        return None


def sweep(persona: str) -> int:
    """The daily catch-up inside `capture_weekly_rollup`: reconcile outcomes, then re-consider
    every category in the window — anything a restart interrupted. Returns offers started."""
    cfg = _cfg()
    if not _on(cfg):
        return 0
    reconcile(persona)
    window = int(cfg.get("noticed_window_days", 30))
    since = (_now() - timedelta(days=window)).isoformat()
    cats = sorted({r["category"] for r in _cap()._read_uncategorised(persona, since)
                   if r.get("category")})
    return sum(1 for c in cats if consider(persona, c))


# ---------------------------------------------------------------------------
# The matcher (plan § 3.2) — the one judgement, validated by code
# ---------------------------------------------------------------------------

def _payload(persona: str, offer: dict, st: dict) -> dict:
    from tools import data_objects as DO
    rows = _held_rows(persona, offer["categories"])
    logs = [{"id": o["id"], "name": o["name"], "aliases": o.get("aliases") or [],
             "description": o.get("description") or "", "store": o.get("store")}
            for o in DO.objects()
            if o.get("status") == "active" and not o.get("merged_into")]
    mine = set(offer["categories"])
    # Never the topic being judged: shown its own earlier offer, the matcher would call it
    # "the same" and the topic could never be offered again (diff review F1).
    earlier = [{"offer": o["id"], "about": _about(o) or ", ".join(o.get("categories", []))}
               for o in st["offers"]
               if o["id"] != offer["id"] and not (mine & set(o.get("categories", [])))
               and o.get("status") in ("no", "expired", "none", "failed")
               and not o.get("parent")]
    return {"categories": offer["categories"],
            "examples": [r.get("say", "") for r in rows[-_MAX_FACTS_SHOWN:]],
            "logs": logs, "earlier_offers": earlier}


def _clean(v, limit: int) -> str:
    t = " ".join(str(v or "").split())
    return t if t and len(t) <= limit and not _IDENT_RE.search(t) else ""


def parse_verdict(raw: str, payload: dict) -> dict | None:
    """The matcher's answer, validated; None for anything that does not hold up. A bad answer
    offers nothing — an object nobody wanted must not happen (R15)."""
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except ValueError:
        return None
    if not isinstance(obj, dict):
        return None
    v = str(obj.get("verdict") or "").strip().lower()
    if v == "none":
        return {"verdict": "none"}
    if v == "match":
        ids = {lg["id"] for lg in payload.get("logs", [])}
        about = _clean(obj.get("about"), 90)
        log = str(obj.get("log") or "")
        return {"verdict": "match", "log": log, "about": about} if log in ids and about else None
    if v == "same_offer":
        ids = {e["offer"] for e in payload.get("earlier_offers", [])}
        off = str(obj.get("offer") or "")
        return {"verdict": "same_offer", "offer": off} if off in ids else None
    if v == "new":
        name, desc = _clean(obj.get("name"), 40), _clean(obj.get("description"), 120)
        ask = _clean(obj.get("ask"), 90)
        ident = str(obj.get("identity") or "thing").strip().lower()
        if not (name and desc and ask) or not ask.lower().startswith(("a list", "a log")) \
                or ident not in ("thing", "occurrence"):
            return None
        return {"verdict": "new", "name": name, "description": desc, "ask": ask,
                "identity": ident}
    return None


def _judge(persona: str, offer_id: str) -> None:
    try:
        with persona_scope(persona):
            C = _cap()
            with _locked(persona):
                st = _load(persona)
                offer = next((o for o in st["offers"] if o["id"] == offer_id), None)
                if offer is None or offer.get("status") != "matching":
                    return
                payload = _payload(persona, offer, st)
            raw = _call_matcher(json.dumps(payload, ensure_ascii=False), persona)
            verdict = parse_verdict(raw, payload) if raw is not None else None
            from tools import data_objects as DO
            with _locked(persona):
                st = _load(persona)
                offer = next((o for o in st["offers"] if o["id"] == offer_id), None)
                if offer is None or offer.get("status") != "matching":
                    return
                offer["judged_at"] = _now().isoformat(timespec="seconds")
                if raw is None:
                    offer["status"] = "deferred"       # not asked — not the matcher's answer
                elif verdict is None:
                    offer["status"] = "matcher_failed"
                elif verdict["verdict"] == "none":
                    offer["status"] = "none"
                elif verdict["verdict"] == "same_offer":
                    target = next(o for o in st["offers"] if o["id"] == verdict["offer"])
                    target["categories"] = sorted(set(target.get("categories", []))
                                                  | set(offer["categories"]))
                    offer.update(status="same", same_as=target["id"])
                elif verdict["verdict"] == "match":
                    o = DO.get(verdict["log"])
                    # A store (contacts, tasks …) or a log the user put away is a home, not a
                    # list to add to: no card (plan § 3.2).
                    if (o and o.get("store") == "archive" and o.get("status") == "active"
                            and not o.get("merged_into")):
                        offer.update(status="held", kind="alias", log=o["id"],
                                     about=verdict["about"])
                    else:
                        offer.update(status="home", log=verdict["log"])
                elif DO.close_match(verdict["name"]) is not None:
                    # A log the user already keeps — archived, private or near-named, which
                    # the matcher was not shown — would refuse the Yes (diff review F4).
                    offer.update(status="home", log=DO.close_match(verdict["name"])["id"])
                else:
                    offer.update(status="held", kind="create", name=verdict["name"],
                                 description=verdict["description"], ask=verdict["ask"],
                                 identity=verdict["identity"])
                _save(persona, st)
                _row(persona, offer)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[noticed] matcher judgement failed: {exc}")


# ---------------------------------------------------------------------------
# The card (plan § 3.3)
# ---------------------------------------------------------------------------

def _about(o: dict) -> str:
    if o.get("about"):
        return o["about"]
    ask = str(o.get("ask") or "")
    for p in ("a list of ", "a log of "):
        if ask.lower().startswith(p):
            return ask[len(p):]
    return o.get("name") or ""


def _in_list(name: str) -> str:
    return name if name.lower().endswith((" list", " log")) else f"{name} list"


def _raise(persona: str, offer: dict, cfg: dict) -> bool:
    """Raise the card for a held offer. Caller holds capture's lock."""
    from tools import confirm
    from tools import data_objects as DO
    n = len(_held_rows(persona, offer["categories"]))
    if offer["kind"] == "create":
        with persona_scope(persona):
            near = DO.close_match(offer["name"])
        if near is not None:
            offer.update(status="home", log=near["id"])   # started meanwhile, in words or by hand
            return False
        action = CREATE
        args = {"offer_id": offer["id"], "name": offer["name"],
                "description": offer["description"], "identity": offer["identity"]}
        description = f"Start {offer['ask']} ({n} so far)"
        question = f"Want me to start {offer['ask']}?"
    else:
        with persona_scope(persona):
            o = DO.get(offer["log"])
        if o is None:
            offer["status"] = "failed"
            return False
        action = ALIAS
        args = {"offer_id": offer["id"], "log": o["id"]}
        description = f"Keep {_about(offer)} in {o['name']} ({n} so far)"
        question = f"Want me to keep {_about(offer)} in your {_in_list(o['name'])}?"
    ttl = int(float(cfg.get("noticed_card_ttl_hours", 2)) * 3600)
    card = confirm.request(action, args, description, persona=persona, ttl_seconds=ttl)
    if card.get("status") != "PENDING_CONFIRMATION":
        return False
    offer.update(status="open", token=card["confirm_token"], question=question, count_at=n,
                 raised_at=_now().isoformat(timespec="seconds"))
    _row(persona, offer)
    return True


def take_offer(persona: str) -> dict | None:
    """At the start of a real user turn's Synthesizer pass: raise the oldest held offer's card
    and return what the reply should ask. One open offer per user at a time. Never raises."""
    try:
        cfg = _cfg()
        if not _on(cfg):
            return None
        C = _cap()
        with _locked(persona):
            st = _load(persona)
            _reconcile(persona, st)
            still = next((o for o in st["offers"] if o.get("status") == "open"), None)
            if still is not None:
                # One card at a time. The open one is reported so every turn while it waits
                # carries the "belongs in my X list" cue — that answer comes on a LATER turn
                # than the question (diff review F2).
                _save(persona, st)
                return {"token": still["token"], "question": still.get("question", ""),
                        "kind": still.get("kind"), "still_open": True}
            held = [o for o in st["offers"] if o.get("status") == "held"]
            offer = None
            for o in held:
                if _raise(persona, o, cfg):
                    offer = o
                    break
            _save(persona, st)
        if offer is None:
            return None
        return {"token": offer["token"], "question": offer["question"], "kind": offer["kind"]}
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[noticed] offer not raised: {exc}")
        return None


def questions_since(persona: str, before: set) -> list[dict]:
    """Questions for offer cards raised since `before` (a set of pending tokens) — this turn's,
    including one raised mid-turn by "belongs in my X list"."""
    try:
        from tools.confirm import pending
        live = {p["token"] for p in pending(persona) if p["token"] not in (before or set())}
        return [{"question": o["question"],
                 "phrase": (o.get("ask") if o.get("kind") == "create" else _about(o)) or ""}
                for o in offers(persona)
                if o.get("status") == "open" and o.get("token") in live and o.get("question")]
    except Exception:  # noqa: BLE001
        return []


def on_alias(obj_id: str) -> dict | None:
    """The Synthesizer added a name to an active archive log while an offer to start a new list
    was open: withdraw that card (no decline is recorded — nothing was refused) and offer to keep
    the same facts in this log instead. Nothing is filed until the user taps (review R4/R5)."""
    from tools import confirm
    from tools import data_objects as DO
    persona = resolve_persona(None)
    o = DO.get(obj_id)
    if not (o and o.get("store") == "archive" and o.get("status") == "active"
            and not o.get("merged_into")):
        return None
    cfg = _cfg()
    C = _cap()
    with _locked(persona):
        st = _load(persona)
        _reconcile(persona, st)
        offer = next((x for x in st["offers"]
                      if x.get("status") == "open" and x.get("kind") == "create"), None)
        if offer is None or confirm.withdraw(offer["token"], persona) is None:
            _save(persona, st)
            return None
        offer["status"] = "superseded"
        _row(persona, offer)
        child = {"id": uuid.uuid4().hex[:10], "categories": list(offer["categories"]),
                 "status": "held", "kind": "alias", "log": o["id"], "about": _about(offer),
                 "parent": offer["id"], "count_at": offer.get("count_at", 0),
                 "created": _now().isoformat(timespec="seconds"), "retries": 0}
        st["offers"].append(child)
        _raise(persona, child, cfg)
        _save(persona, st)
    return child


# ---------------------------------------------------------------------------
# Outcomes, from server state only (plan § 3.4)
# ---------------------------------------------------------------------------

def _reconcile(persona: str, st: dict) -> None:
    """Caller holds capture's lock."""
    open_ = [o for o in st["offers"] if o.get("status") == "open"]
    if not open_:
        return
    from tools.confirm import declined, pending
    live = {p["token"] for p in pending(persona)}
    refused = {(r.get("args") or {}).get("offer_id") for r in declined(None, persona)
               if r.get("action") in (CREATE, ALIAS)}
    for o in open_:
        if o.get("token") in live:
            continue
        # A ledger record whose args failed decline()'s tamper check has no offer_id and
        # cannot be attributed: it reads as expired, the conservative side.
        o["status"] = "no" if o["id"] in refused else "expired"
        o["resolved_at"] = _now().isoformat(timespec="seconds")
        if o["status"] == "no":
            o["count_at"] = len(_held_rows(persona, o.get("categories", [])))
        _row(persona, o)
        parent = next((x for x in st["offers"] if x["id"] == o.get("parent")), None)
        if parent is not None and parent.get("status") == "superseded":
            parent.update(status="expired",
                          count_at=len(_held_rows(persona, parent.get("categories", []))))


def reconcile(persona: str) -> None:
    C = _cap()
    with _locked(persona):
        st = _load(persona)
        _reconcile(persona, st)
        _save(persona, st)


# ---------------------------------------------------------------------------
# The executors — POST /confirm, by code (tools/confirm.py _EXECUTORS)
# ---------------------------------------------------------------------------

def _file(persona: str, obj_id: str, offer: dict) -> int:
    """File every held fact of the offer's categories into the log, as code. Read at tap time,
    so a mention made between the question and the tap is filed too (review R7)."""
    from tools import data_objects as DO
    o = DO.get(obj_id)
    rows = _held_rows(persona, offer.get("categories", []))
    for r in rows:
        DO.archive_write(o, {"text": r.get("say", ""), "noted_at": str(r.get("ts", ""))[:10],
                             "source": "noticed"})
    return len(rows)


def _finish(persona: str, st: dict, offer: dict, status: str, **kw) -> None:
    offer.update(status=status, resolved_at=_now().isoformat(timespec="seconds"), **kw)
    _save(persona, st)
    _row(persona, offer)


def create_noticed_log(offer_id: str, name: str, description: str, identity: str,
                       persona: str | None = None, confirm_token: str = ""):
    """The user tapped Yes on "Start a list …": start it (origin "noticed") and file what they
    already said. Spends the approval through `consume()` like every gated tool."""
    from tools import data_objects as DO
    from tools.confirm import consume
    persona = resolve_persona(persona)
    args = {"offer_id": offer_id, "name": name, "description": description,
            "identity": identity}
    C = _cap()
    with _locked(persona):
        ok, reason = consume(confirm_token, CREATE, args, persona=persona)
        if not ok:
            return {"error": f"List not started: {reason}"}
        st = _load(persona)
        offer = next((o for o in st["offers"] if o["id"] == offer_id), None)
        if offer is None:
            return {"error": "List not started: that offer is no longer on record."}
        with persona_scope(persona):
            out = DO.create_object(name, description=description, identity=identity,
                                   origin="noticed", persona=persona)
            if not out.get("created"):
                # Any match — exact or near — files nothing: the near match is the one phase 1
                # refused to file into, and it may be a store, archived or private (review R1).
                _finish(persona, st, offer, "failed")
                near = (out.get("match") or {}).get("name")
                return {"error": (f"you already keep something close: {near} — nothing new "
                                  f"was started.") if near else
                        f"List not started: {out.get('error')}."}
            oid = out["object"]["id"]
            for cat in offer.get("categories", []):
                DO.add_alias(oid, cat)
            n = _file(persona, oid, offer)
        _finish(persona, st, offer, "yes", log=oid)
    return f"Started {name} with {n} entries."


def alias_noticed_log(offer_id: str, log: str, persona: str | None = None,
                      confirm_token: str = ""):
    """The user tapped Yes on "Keep … in X": file what they said into X and make the topic one
    of X's names, so it is never offered as a new list again."""
    from tools import data_objects as DO
    from tools.confirm import consume
    persona = resolve_persona(persona)
    args = {"offer_id": offer_id, "log": log}
    C = _cap()
    with _locked(persona):
        ok, reason = consume(confirm_token, ALIAS, args, persona=persona)
        if not ok:
            return {"error": f"Nothing added: {reason}"}
        st = _load(persona)
        offer = next((o for o in st["offers"] if o["id"] == offer_id), None)
        if offer is None:
            return {"error": "Nothing added: that offer is no longer on record."}
        with persona_scope(persona):
            o = DO.get(log)
            if not (o and o.get("store") == "archive" and o.get("status") == "active"
                    and not o.get("merged_into")):
                _finish(persona, st, offer, "failed")
                return {"error": "Nothing added: that list is put away or cannot take entries."}
            for cat in offer.get("categories", []):
                DO.add_alias(o["id"], cat)
            n = _file(persona, o["id"], offer)
        _finish(persona, st, offer, "yes")
    return f"Kept {n} in {o['name']}."


# ---------------------------------------------------------------------------
# The derived writer — in shadow (plan § 3.5, R15)
# ---------------------------------------------------------------------------

_WRITE_TOOLS = ("write_data_object", "write_archive")


def _derived_path(persona: str):
    return _cap()._dir(persona) / "derived.jsonl"


def derived(persona: str, rid: str, c: dict, writes: list, touched, user_text: str = "") -> str:
    """One `entry` candidate from the extractor. Returns its content-free outcome. In shadow
    it is recorded and NOTHING is written; on, code writes it marked derived. Never raises."""
    try:
        cfg = _cfg()
        mode = str(cfg.get("derived_entries", "shadow")).lower()
        if not cfg.get("enabled") or mode not in ("shadow", "on"):
            return "derived_off"
        from tools import data_objects as DO
        with persona_scope(persona):
            o = DO.get(str(c.get("target") or ""))
            if (o is None or o.get("status") != "active" or o.get("merged_into")
                    or (o.get("store") != "archive" and o["id"] == o.get("store"))):
                return "derived_invalid"
            prop = c.get("proposal")
            allowed = set(DO.fields_of(o)) | {"text", "notes"}
            if not isinstance(prop, dict) or not prop or any(k not in allowed for k in prop):
                return "derived_invalid"

            def _names(args: dict) -> set:
                out = {str(args.get("object") or ""), str(args.get("category") or "")}
                hit = DO.resolve(str(args.get("object") or "")) if args.get("object") else None
                return out | ({hit["id"]} if hit else set())
            written = any(t in _WRITE_TOOLS and o["id"] in _names(a or {}) for t, a in writes)
            if o["id"] in set(touched or ()) or written:
                return "derived_kept"
            rec = {"ts": _now().isoformat(timespec="seconds"), "request_id": rid,
                   "target": o["id"], "proposal": prop, "say": c.get("say", ""),
                   "quote": c.get("quote", ""), "user_text": (user_text or "")[:600],
                   "mode": mode}
            C = _cap()
            with _locked(persona):
                with open(_derived_path(persona), "a") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if mode != "on":
                return "derived_shadow"
            if o.get("store") != "archive":
                return "derived_unsupported"
            DO.archive_write(o, {**prop, "derived": True, "source_turn": rid})
            return "derived_written"
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[noticed] derived entry not handled: {exc}")
        return "derived_failed"


# ---------------------------------------------------------------------------
# Report, labels, score
# ---------------------------------------------------------------------------

def summary(persona: str) -> dict:
    st = _load(persona)
    by: dict[str, int] = {}
    for o in st["offers"]:
        by[o.get("status", "?")] = by.get(o.get("status", "?"), 0) + 1
    yes, no = by.get("yes", 0), by.get("no", 0)
    return {"crossed": len(st["offers"]), "by_status": by,
            "cards": sum(1 for o in st["offers"] if o.get("token")),
            "yes_rate": (yes / (yes + no)) if (yes + no) else None}


def report_lines(persona: str) -> list[str]:
    s = summary(persona)
    rate = "—" if s["yes_rate"] is None else f"{s['yes_rate']:.0%}"
    by = ", ".join(f"{k} {v}" for k, v in sorted(s["by_status"].items())) or "none"
    lines = [f"  noticed logs: {s['crossed']} crossed the threshold · {s['cards']} cards raised "
             f"· {by} · yes rate {rate}"]
    path = _derived_path(persona)
    recs = [ln for ln in path.read_text().splitlines() if ln.strip()] if path.exists() else []
    lines.append(f"  derived entries: {len(recs)} proposals recorded "
                 f"({_cfg().get('derived_entries', 'shadow')})")
    return lines


def _labels_path(persona: str):
    return _cap()._dir(persona) / "derived_labels.jsonl"


def label_derived(persona: str, n: int = 60) -> str:
    """M4: Mike labels the shadow proposals. Enter = right; w = a value wrong or invented;
    x = not an entry for that log; d = already kept; q = quit."""
    import random
    from tools import data_objects as DO
    path = _derived_path(persona)
    recs = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()] \
        if path.exists() else []
    done = set()
    lp = _labels_path(persona)
    if lp.exists():
        done = {json.loads(ln)["key"] for ln in lp.read_text().splitlines() if ln.strip()}
    pool = [r for r in recs if f"{r['request_id']}:{r['target']}" not in done]
    sample = random.Random(11).sample(pool, min(n, len(pool)))
    with open(lp, "a") as fh:
        for i, r in enumerate(sample, 1):
            o = DO.get(r["target"]) or {"name": r["target"]}
            print(f"\n[{i}/{len(sample)}] USER: {r.get('user_text') or r.get('quote')}")
            print(f"  log: {o['name']}   proposed entry: "
                  f"{json.dumps(r['proposal'], ensure_ascii=False)[:300]}")
            k = input("  Enter=right  w=wrong value  x=not an entry  d=already kept  q=quit > ")
            if k.strip() == "q":
                break
            lab = {"w": "wrong_value", "x": "not_entry", "d": "duplicate"}.get(k.strip(), "right")
            fh.write(json.dumps({"key": f"{r['request_id']}:{r['target']}", "label": lab}) + "\n")
    return score_derived(persona)


def score_derived(persona: str) -> str:
    lp = _labels_path(persona)
    rows = [json.loads(ln) for ln in lp.read_text().splitlines() if ln.strip()] \
        if lp.exists() else []
    if not rows:
        return "no derived labels yet"
    right = sum(1 for r in rows if r["label"] == "right")
    floor = float((_cfg().get("minimums") or {}).get("precision", 0.90))
    prec = right / len(rows)
    by = ", ".join(f"{k} {sum(1 for r in rows if r['label'] == k)}"
                   for k in ("right", "wrong_value", "not_entry", "duplicate"))
    return (f"derived writer precision {prec:.0%} (n={len(rows)}, min {floor:.0%}) — "
            f"{'PASS' if prec >= floor else 'below the floor'} · {by}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="tools.noticed_logs")
    ap.add_argument("--persona", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--report", action="store_true")
    g.add_argument("--label-derived", action="store_true")
    g.add_argument("--score-derived", action="store_true")
    g.add_argument("--sweep", action="store_true")
    a = ap.parse_args()
    with persona_scope(a.persona):
        if a.report:
            print("\n".join(report_lines(a.persona)))
        elif a.label_derived:
            print(label_derived(a.persona))
        elif a.score_derived:
            print(score_derived(a.persona))
        else:
            # Inline: a daemon thread would die with this process before judging anything.
            global MATCH_IN_BACKGROUND
            MATCH_IN_BACKGROUND = False
            print(f"offers started: {sweep(a.persona)}")


if __name__ == "__main__":
    main()
