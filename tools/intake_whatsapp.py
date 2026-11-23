"""
tools/intake_whatsapp.py — WhatsApp, the VM side: receive, screen, extract, surface.

Plan: archive/plans/whatsapp_input_plan_2026-10-26.md (V1–V9); this build's re-anchored delta,
with Mike's rulings A–D: archive/plans/whatsapp_phase1_build_plan_2026-11-23.md.

WHAT IT DOES
------------
The phone pushes the messages of the chats the user chose to share (POST /device/whatsapp/events,
core/server.py). For each one, here, in code:

1. **Screen** (V2) — word and pattern lists in config/templates/whatsapp_screen.yaml, tuned to
   over-flag. A hit becomes a held-back flag — who, which chat, when, category, **no text** — and
   nothing of the message reaches extraction, intake, a record or any model. A message in a
   script with no translation model is held back the same way, as `unscreened` (decision D).
2. **Translate** Bulgarian to English on the VM (decision D: a small local model, CTranslate2;
   the text never leaves the machine and is never stored). Extraction stays code.
3. **Extract a fact** (V3) — type, time, at most two short named spans, who it is from (the
   user's own name for them, never a WhatsApp display name). **Never a sentence of theirs.**
4. **Ingest** (V4) — an intake Envelope whose `subject` is the fact, through tools/intake.ingest,
   so `action_required` facts surface to the head layer exactly as mail does (V5).

**No message text is ever written anywhere.** It is held in memory for the length of a request.
What persists, per user, under data/personas/{p}/intake/:

    whatsapp_index.jsonl   one row per fact: chat, times, type, re-surface state, fingerprint
    whatsapp_flags.jsonl   held-back messages: who, chat, when, category — no text
    whatsapp_state.json    the share list, the backup cursor, last reply time per chat, the salt

Every write takes tools.intake._state_lock — the hourly sweep runs in the scheduler process and
the endpoint in the server process (plan § 2.4).

THE CHANNEL IS OFF FOR EVERY USER until BOTH the intake stanza `channels.whatsapp: true` AND the
user's `whatsapp` consent record (core/consent.py) are present. Turning either off stops
collection and deletes nothing; deleting is the user's own opt-in, `delete_all()` (Mike,
decision C). Un-sharing a chat deletes that chat at once (W3).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import secrets
import threading
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from tools import intake

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _ROOT / "config" / "templates" / "whatsapp_screen.yaml"

CHANNEL = "whatsapp"
MAX_EVENTS = 500                 # per request; the phone batches (plan § 2.1)
MAX_TEXT_CHARS = 4000
MAX_LABEL_CHARS = 60
_MS_THRESHOLD = 10 ** 11         # a `time` at or above this is milliseconds, refused (§ 2.2)
RESURFACE_AFTER_HOURS = 24       # W8
NO_EVENT_TIME_RELEVANT_HOURS = 72
DELIVERY_WINDOW_MIN = 30         # the digest's pattern: one session's Coordinator + Synth
RETENTION_DAYS = 90              # W6 / V9
_ACTION_TYPES = ("question", "proposal", "request")
_KINDS = ("one_to_one", "group")


class ChannelOff(Exception):
    """The channel's gate is shut for this user — the phone shows "WhatsApp link is off"."""


class EventError(ValueError):
    """A request the endpoint refuses as a whole (400)."""


# ---------------------------------------------------------------------------
# Config, paths, state
# ---------------------------------------------------------------------------

_cfg_cache: dict = {"mtime": None, "data": None}


def screen_config() -> dict:
    """whatsapp_screen.yaml, re-read when it changes. A missing or broken file screens EVERYTHING
    (fail closed): an empty list would let every message through."""
    try:
        mtime = _CONFIG_PATH.stat().st_mtime_ns
        if _cfg_cache["mtime"] != mtime:
            _cfg_cache["data"] = yaml.safe_load(_CONFIG_PATH.read_text()) or {}
            _cfg_cache["mtime"] = mtime
        return _cfg_cache["data"]
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[whatsapp] screen config unreadable — holding every message back: {exc}")
        return {"_broken": True}


def _dir(persona: str | None) -> Path:
    return intake._intake_dir(persona)


def _index_path(persona):
    return _dir(persona) / "whatsapp_index.jsonl"


def _flags_path(persona):
    return _dir(persona) / "whatsapp_flags.jsonl"


def _state_path(persona):
    return _dir(persona) / "whatsapp_state.json"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except Exception:  # noqa: BLE001
                continue
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    tmp.chmod(0o600)
    tmp.replace(path)


def _load_state(persona) -> dict:
    return intake._read_json(_state_path(persona), {}) or {}


def _save_state(state: dict, persona) -> None:
    intake._write_json(_state_path(persona), state)


def _salt(state: dict) -> bytes:
    """The per-user fingerprint salt — never the auth signing key, so rotating the password does
    not turn every re-send into a "clash" (verify new 1). Made on first use; the caller saves."""
    if not state.get("salt"):
        state["salt"] = secrets.token_hex(32)
    return bytes.fromhex(state["salt"])


def fingerprint(text: str, salt: bytes) -> str:
    """A keyed hash of a message's text: tells "the same message again" from "a different message
    that drew the same key" (§ 2.2, review 5). Not text, and not reversible without the salt."""
    return hmac.new(salt, (text or "").encode("utf-8", "replace"), hashlib.sha256).hexdigest()[:16]


def native_key(chat: str, time_s: int, ordinal: int) -> str:
    """THE message key (plan P2, phase-1 § 2.2): canonical chat + time in whole SECONDS + ordinal.
    Seconds because the nightly increments carry seconds (format description § 12) while live
    notifications carry milliseconds — the phone floors, and the VM refuses a ms-shaped time."""
    return f"{chat}|{int(time_s)}|{int(ordinal)}"


def _iso(time_s: int) -> str:
    return datetime.fromtimestamp(int(time_s)).isoformat(timespec="seconds")


def _persona_name(persona: str | None) -> str:
    from core.persona import resolve_persona
    return resolve_persona(persona)


def _consent_granted(persona: str | None) -> bool:
    try:
        from core import consent
        return consent.is_granted("whatsapp", _persona_name(persona))
    except Exception as exc:  # noqa: BLE001 — fail closed
        logger.warning(f"[whatsapp] consent not readable — channel treated as off: {exc}")
        return False


def channel_open(persona: str | None, cfg: dict | None = None) -> bool:
    """Intake on, the stanza on, and the user's own `whatsapp` consent record. All three."""
    cfg = intake.load_config(persona) if cfg is None else cfg
    if not cfg.get("enabled") or not (cfg.get("channels") or {}).get(CHANNEL):
        return False
    return _consent_granted(persona)


# ---------------------------------------------------------------------------
# V2 — the screen
# ---------------------------------------------------------------------------

_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "@": "a", "$": "s"})
_compiled: dict = {"src": None, "rules": None}


def _deobfuscate(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "").casefold()
    t = t.translate(_LEET)
    t = re.sub(r"(\w)\1{2,}", r"\1\1", t)                       # sooooo → soo
    t = re.sub(r"\b(?:\w[.\-_*\s]){2,}\w\b",                      # k.i.l.l / s e x → kill / sex
               lambda m: re.sub(r"[.\-_*\s]", "", m.group(0)) if all(
                   len(p) == 1 for p in re.split(r"[.\-_*\s]", m.group(0)) if p) else m.group(0), t)
    return t


def _word_rx(word: str) -> str:
    w = str(word).casefold().strip()
    star = w.endswith("*")
    w = re.escape(w.rstrip("*")).replace(r"\ ", r"\s+")
    return r"\b" + w + (r"\w*" if star else r"\b")


def _rules() -> list[tuple[str, re.Pattern]]:
    cfg = screen_config()
    src = id(cfg)
    if _compiled["src"] == src:
        return _compiled["rules"]
    rules = []
    for category, spec in (cfg.get("screen") or {}).items():
        spec = spec or {}
        parts = [_word_rx(w) for w in spec.get("words") or [] if str(w).strip()]
        parts += [str(p) for p in spec.get("patterns") or [] if str(p).strip()]
        if parts:
            rules.append((category, re.compile("|".join(f"(?:{p})" for p in parts), re.UNICODE)))
    _compiled.update(src=src, rules=rules)
    return rules


def screen(text: str) -> str | None:
    """The first category the text hits, or None. A broken config holds back everything."""
    if screen_config().get("_broken"):
        return "unscreened"
    plain = _deobfuscate(text)
    for category, rx in _rules():
        if rx.search(plain) or rx.search(unicodedata.normalize("NFKC", text or "").casefold()):
            return category
    return None


# ---------------------------------------------------------------------------
# Languages — Bulgarian translated on the VM (decision D)
# ---------------------------------------------------------------------------

def script_of(text: str) -> str:
    """'latin', 'cyrillic' or 'other' — by the share of letters, per whatsapp_screen.yaml."""
    letters = [c for c in text or "" if c.isalpha()]
    if not letters:
        return "latin"
    share = float((screen_config().get("languages") or {}).get("script_share", 0.5))
    n = len(letters)
    cyr = sum(1 for c in letters if "CYRILLIC" in unicodedata.name(c, ""))
    lat = sum(1 for c in letters if "LATIN" in unicodedata.name(c, ""))
    if cyr / n > share:
        return "cyrillic"
    if (n - cyr - lat) / n > share:
        return "other"           # Greek, Arabic, CJK, … — no model yet: held back unscreened
    return "cyrillic" if cyr > lat else "latin"


class _Translator:
    """OPUS-MT Bulgarian→English through CTranslate2 (int8), loaded on first use and unloaded
    after `unload_after_idle_seconds` unused. ~150–250 MB while loaded (plan § 5 D). The model
    directory is made once by scripts/fetch_whatsapp_translation_model.py; without it there is
    no translation, and Bulgarian is held back as `unscreened` — never sent anywhere else."""

    def __init__(self, model_dir: Path, idle_seconds: int) -> None:
        self.model_dir = model_dir
        self.idle_seconds = idle_seconds
        self._lock = threading.Lock()
        self._model = None
        self._sp_src = None
        self._sp_tgt = None
        self._timer: threading.Timer | None = None

    def available(self) -> bool:
        return (self.model_dir / "model.bin").exists() and (self.model_dir / "source.spm").exists()

    def _load(self) -> None:
        import ctranslate2
        import sentencepiece
        self._model = ctranslate2.Translator(str(self.model_dir), device="cpu",
                                             compute_type="int8", inter_threads=1,
                                             intra_threads=1)
        self._sp_src = sentencepiece.SentencePieceProcessor(
            model_file=str(self.model_dir / "source.spm"))
        self._sp_tgt = sentencepiece.SentencePieceProcessor(
            model_file=str(self.model_dir / "target.spm"))
        logger.info("[whatsapp] translation model loaded")

    def unload(self) -> None:
        with self._lock:
            self._model = self._sp_src = self._sp_tgt = None
            self._timer = None
        # Freed is not returned: glibc keeps the pages unless asked, and the point of unloading
        # on a 4 GB VM is to give them back. Linux only; elsewhere a no-op.
        try:
            import ctypes
            import gc
            gc.collect()
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except Exception:  # noqa: BLE001
            pass
        logger.info("[whatsapp] translation model unloaded (idle)")

    def __call__(self, text: str) -> str:
        with self._lock:
            if self._model is None:
                self._load()
            pieces = self._sp_src.encode(text, out_type=str)[:400] + ["</s>"]
            out = self._model.translate_batch([pieces], beam_size=2, max_decoding_length=512)
            tokens = [t for t in out[0].hypotheses[0] if t != "</s>"]
            result = self._sp_tgt.decode(tokens)
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.idle_seconds, self.unload)
            self._timer.daemon = True
            self._timer.start()
            return result


_translators: dict = {}
_test_translator = None


def set_translator(fn) -> None:
    """Tests only: a stand-in `fn(text) -> english`, or None to restore the real model."""
    global _test_translator
    _test_translator = fn


def translate(text: str, lang: str) -> str | None:
    """English for `text` in `lang`, or None when no model is available for it."""
    if _test_translator is not None:
        return _test_translator(text)
    spec = ((screen_config().get("languages") or {}).get(lang) or {})
    if not spec.get("model_dir"):
        return None
    t = _translators.get(lang)
    if t is None:
        idle = int((screen_config().get("languages") or {}).get("unload_after_idle_seconds", 600))
        t = _translators[lang] = _Translator(_ROOT / spec["model_dir"], idle)
    if not t.available():
        return None
    try:
        return t(text)
    except Exception as exc:  # noqa: BLE001 — a broken model is "no translation", fail closed
        logger.warning(f"[whatsapp] translation failed — message held back unscreened: {exc}")
        return None


def english_for(text: str) -> tuple[str | None, str]:
    """(english text or None, language). None means: hold back as `unscreened`."""
    s = script_of(text)
    if s == "latin":
        return text, "en"
    if s == "cyrillic":
        return translate(text, "bg"), "bg"
    return None, "other"


# ---------------------------------------------------------------------------
# V3 — the fact
# ---------------------------------------------------------------------------

_TIME_RX = re.compile(r"\d{1,2}[:.]\d{2}|\d\s?(?:am|pm)\b|\b(?:noon|midnight)\b|\d\s?ч\b|\bобед",
                      re.IGNORECASE | re.UNICODE)


_CLOCK_RX = re.compile(r"(?<![\d:.])([01]?\d|2[0-3])[:.]([0-5]\d)(?![\d:.])")


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(phrase.casefold()) + r"(?!\w)", text) is not None


def find_when(original: str, english: str, sent_at: datetime, lang: str) -> str | None:
    """The first believable date/time in the message, as ISO 'YYYY-MM-DD[ HH:MM]', or None.

    Read from the ORIGINAL text (dateparser knows Bulgarian), relative to the message's own time,
    preferring the future. A hit is kept only if its matched text has a digit or a date word:
    dateparser alone reads "may", "second" and "sun" as dates."""
    try:
        from dateparser.search import search_dates
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[whatsapp] dateparser unavailable: {exc}")
        return None
    words = {str(w).casefold() for w in (screen_config().get("facts") or {}).get("date_words") or []}
    langs = ["bg", "en"] if lang == "bg" else ["en"]
    settings = {"RELATIVE_BASE": sent_at, "PREFER_DATES_FROM": "future",
                "RETURN_AS_TIMEZONE_AWARE": False}
    for source in (original, english if english != original else None):
        if not source:
            continue
        try:
            hits = search_dates(source, languages=langs, settings=settings) or []
        except Exception:  # noqa: BLE001
            hits = []
        for matched, when in hits:
            m = matched.casefold()
            tokens = set(re.findall(r"\w+", m, re.UNICODE))
            if not (re.search(r"\d", m) or tokens & words):
                continue
            if _TIME_RX.search(matched):
                return when.strftime("%Y-%m-%d %H:%M")
            # dateparser often matches the day alone ("в събота в 19:00" → "събота"): take the
            # clock time from elsewhere in the message when there is exactly one.
            # The original first: a translation may render 19:00 as "7:00 p.m.".
            clocks = {m.groups() for m in _CLOCK_RX.finditer(original or "")} or {
                m.groups() for m in _CLOCK_RX.finditer(english or "")}
            if len(clocks) == 1:
                hh, mm = clocks.pop()
                return when.replace(hour=int(hh), minute=int(mm)).strftime("%Y-%m-%d %H:%M")
            return when.strftime("%Y-%m-%d")
    return None


def fact_type(english: str, when: str | None) -> str:
    facts = screen_config().get("facts") or {}
    low = " " + " ".join((english or "").casefold().split()) + " "
    if when and any(_contains_phrase(low, p) for p in facts.get("proposal_markers") or []):
        return "proposal"
    if any(_contains_phrase(low, p) for p in facts.get("request_markers") or []):
        return "request"
    first = (re.findall(r"\w+", low, re.UNICODE) or [""])[0]
    if "?" in low or first in {str(w).casefold() for w in facts.get("question_openers") or []}:
        # "How are you?" asks nothing of the user. A greeting alone is chat, unless the same
        # message asks something else as well (a second question mark).
        if (any(_contains_phrase(low, p) for p in facts.get("greeting_questions") or [])
                and low.count("?") <= 1):
            return "info"
        return "question"
    return "info"


def find_spans(original: str, english: str) -> list[str]:
    """At most two named spans, each ≤ span_max_chars: the event noun, and a capitalised place
    after a preposition. Sender-controlled substrings — a span carrying an injection marker is
    dropped, never kept (W7; plan V4)."""
    from tools.untrusted import contains_injection_markers
    facts = screen_config().get("facts") or {}
    cap = int(facts.get("span_max_chars", 40))
    spans: list[str] = []
    low = (english or "").casefold()
    for noun in facts.get("event_nouns") or []:
        if _contains_phrase(low, str(noun)):
            spans.append(str(noun))
            break
    preps = "|".join(re.escape(str(p)) for p in facts.get("place_prepositions") or [])
    if preps:
        rx = re.compile(r"(?:^|\s)(?:" + preps + r")\s+((?:[A-ZА-Я][\w'&.-]*)(?:\s+[A-ZА-Я][\w'&.-]*){0,2})",
                        re.UNICODE)
        for source in (original, english):
            m = rx.search(source or "")
            if m:
                spans.append(m.group(1)[:cap])
                break
    return [s for s in spans if s and not contains_injection_markers(s)][:2]


def build_fact(original: str, english: str, lang: str, sent_at: datetime, kind: str,
               who: str) -> dict:
    when = find_when(original, english, sent_at, lang)
    ftype = fact_type(english, when)
    spans = find_spans(original, english)
    action = ftype in _ACTION_TYPES if kind == "one_to_one" else ftype == "proposal"
    parts = [ftype, f"from {who}"] + [f'"{s}"' for s in spans] + ([when] if when else [])
    return {"type": ftype, "when": when, "spans": spans, "action": action,
            "awaiting_reply": kind == "one_to_one" and ftype in _ACTION_TYPES,
            "subject": " · ".join(parts)[:200]}


# ---------------------------------------------------------------------------
# The share list (P1) and the cursor (P3)
# ---------------------------------------------------------------------------

def _clean_label(value) -> str:
    return " ".join(str(value or "").split())[:MAX_LABEL_CHARS]


def _require_open(persona) -> None:
    if not channel_open(persona):
        raise ChannelOff("channel_off")


def set_share_list(persona: str | None, payload: dict) -> dict:
    """Replace the VM's copy of the share list whole. A chat that drops off is un-shared and
    PURGED before this returns (W3). `merges` move a hidden id's entries to its canonical id."""
    _require_open(persona)
    chats = payload.get("chats")
    if not isinstance(chats, list):
        raise EventError("`chats` must be a list")
    new: dict[str, dict] = {}
    for item in chats:
        if not isinstance(item, dict):
            raise EventError("each chat must be an object")
        chat = str(item.get("chat") or "").strip()
        kind = item.get("kind")
        if not chat or "|" in chat or kind not in _KINDS:
            raise EventError("each chat needs `chat` (an id) and `kind` (one_to_one or group)")
        senders = item.get("senders") or {}
        if not isinstance(senders, dict):
            raise EventError("`senders` must be an object")
        new[chat] = {"kind": kind, "label": _clean_label(item.get("label")),
                     "senders": {str(k): _clean_label(v) for k, v in list(senders.items())[:2000]}}
    merges = payload.get("merges") or []
    if not isinstance(merges, list):
        raise EventError("`merges` must be a list")
    purged = 0
    with intake._state_lock(persona):
        state = _load_state(persona)
        old = state.get("share") or {}
        removed = [c for c in old if c not in new]
        for chat in removed:
            purged += purge_chat(persona, chat)
        state = _load_state(persona)          # purge_chat rewrote it
        state["share"] = new
        _apply_merges(persona, state, merges)
        _save_state(state, persona)
    return {"shared": len(new), "removed": len(removed), "purged_facts": purged}


def _apply_merges(persona, state: dict, merges: list) -> None:
    pairs = [(str(m.get("from") or ""), str(m.get("to") or "")) for m in merges
             if isinstance(m, dict) and m.get("from") and m.get("to")]
    if not pairs:
        return
    rename = dict(pairs)
    rows = _read_jsonl(_index_path(persona))
    for r in rows:
        if r.get("chat") in rename:
            r["chat"] = rename[r["chat"]]
    _write_jsonl(_index_path(persona), rows)
    last = state.get("last_reply") or {}
    for a, b in pairs:
        if a in last:
            last[b] = max(last.pop(a), last.get(b, 0))
    state["last_reply"] = last


def get_cursor(persona: str | None) -> dict:
    _require_open(persona)
    return {"cursor": _load_state(persona).get("cursor")}


# ---------------------------------------------------------------------------
# Events (V1's body) → screen → fact → ingest
# ---------------------------------------------------------------------------

def _flag(persona, env_id: str, chat: str, sender: str, time_s: int, category: str) -> None:
    rows = _read_jsonl(_flags_path(persona))
    if any(r.get("id") == env_id for r in rows):
        return
    rows.append({"id": env_id, "chat": chat, "sender": sender, "time": _iso(time_s),
                 "category": category, "flagged_at": datetime.now().isoformat(timespec="seconds")})
    _write_jsonl(_flags_path(persona), rows)


def _validate(ev, i: int) -> tuple[dict | None, str | None]:
    if not isinstance(ev, dict):
        return None, "not an object"
    kind = ev.get("kind")
    if kind not in ("message", "update", "reply_marker"):
        return None, "unknown kind"
    chat = ev.get("chat")
    if not isinstance(chat, str) or not chat.strip() or "|" in chat:
        return None, "no chat id"
    t = ev.get("time")
    if not isinstance(t, int) or isinstance(t, bool) or t <= 0:
        return None, "no time (whole seconds)"
    if t >= _MS_THRESHOLD:
        return None, "time is in milliseconds; send whole seconds"
    ordinal = ev.get("ordinal", 0)
    if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 0:
        return None, "bad ordinal"
    text = ev.get("text")
    if kind == "reply_marker":
        if text not in (None, ""):
            return None, "a reply_marker never carries text"
    elif not isinstance(text, str):
        return None, "no text"
    elif len(text) > MAX_TEXT_CHARS:
        return None, f"text over {MAX_TEXT_CHARS} characters"
    sender = ev.get("sender") or ""
    if not isinstance(sender, str):
        return None, "bad sender"
    return {"kind": kind, "chat": chat.strip(), "time": t, "ordinal": ordinal,
            "text": text or "", "sender": sender.strip(), "source": ev.get("source") or ""}, None


def _who(share_entry: dict, kind: str, sender: str) -> tuple[str, str]:
    """(name shown in the fact, sender_display). The user's own name for them only."""
    label = share_entry.get("label") or "a contact"
    if kind == "one_to_one":
        return label, share_entry.get("label") or ""
    name = (share_entry.get("senders") or {}).get(sender) if sender else ""
    if name:
        return name, name
    return f"a member of {label}", ""


def _analyse(ev: dict, entry: dict) -> dict:
    """Translate, screen and, if it passes, build the fact — no state touched, no lock held.
    `category` set means held back; `fact` is then None and nothing else is computed."""
    kind = entry["kind"]
    english, lang = english_for(ev["text"])
    category = "unscreened" if english is None else (
        screen(english) or (screen(ev["text"]) if lang != "en" else None))
    if category:
        return {"category": category, "fact": None, "display": ""}
    sender = ev["sender"] if kind == "group" else ev["chat"]
    who, display = _who(entry, kind, sender)
    fact = build_fact(ev["text"], english, lang, datetime.fromtimestamp(ev["time"]), kind, who)
    return {"category": None, "fact": fact, "display": display}


def handle_events(persona: str | None, payload: dict) -> dict:
    """The body of POST /device/whatsapp/events (plan § 2.2). Text is held in memory only."""
    _require_open(persona)
    events = payload.get("events")
    if not isinstance(events, list):
        raise EventError("`events` must be a list")
    if len(events) > MAX_EVENTS:
        raise EventError(f"at most {MAX_EVENTS} events per request")
    cursor = payload.get("cursor")
    if cursor is not None and (not isinstance(cursor, int) or isinstance(cursor, bool)
                               or cursor <= 0 or cursor >= _MS_THRESHOLD):
        raise EventError("`cursor` must be whole seconds")

    out = {"accepted": 0, "duplicates": 0, "updated": 0, "dropped_not_shared": 0,
           "held_back": 0, "rejected": [], "action_needed": False}
    cfg = intake.load_config(persona)

    # The slow part — translation (~0.1 s a Bulgarian message, ~0.3 s to load), screening and
    # fact-building — happens BEFORE the state lock, which the scheduler's hourly sweep also
    # needs; only the dedupe and the writes hold it. Against the share list as read now; the
    # locked pass re-checks every chat against the share list as it is then.
    share_now = _load_state(persona).get("share") or {}
    analysed: dict[int, dict] = {}
    for i, raw in enumerate(events):
        ev, err = _validate(raw, i)
        if err or ev["kind"] == "reply_marker" or ev["chat"] not in share_now:
            continue
        analysed[i] = _analyse(ev, share_now[ev["chat"]])

    with intake._state_lock(persona):
        state = _load_state(persona)
        salt = _salt(state)
        share = state.get("share") or {}
        index = {r["id"]: r for r in _read_jsonl(_index_path(persona)) if r.get("id")}
        seen = intake._load_seen(persona)
        envelopes: list[intake.Envelope] = []
        pending: dict[str, dict] = {}        # env id → index row, written after ingest
        markers: list[tuple[str, int]] = []

        for i, raw in enumerate(events):
            ev, err = _validate(raw, i)
            if err:
                out["rejected"].append({"index": i, "reason": err})
                continue
            entry = share.get(ev["chat"])
            if entry is None:
                out["dropped_not_shared"] += 1
                continue
            kind = entry["kind"]
            if ev["kind"] == "reply_marker":
                markers.append((ev["chat"], ev["time"]))
                out["accepted"] += 1
                continue
            sender = ev["sender"] if kind == "group" else ev["chat"]
            key = native_key(ev["chat"], ev["time"], ev["ordinal"])
            env_id = intake.envelope_id(CHANNEL, key)
            fp = fingerprint(ev["text"], salt)

            if ev["kind"] == "message" and (env_id in seen or env_id in index or env_id in pending):
                prior = index.get(env_id) or pending.get(env_id) or {}
                if prior.get("fp") in (None, fp):
                    out["duplicates"] += 1
                    continue
                # A different message drew the same key — an ordinal clash between the live and
                # backup paths. Re-keyed, never dropped (review 5).
                key = f"{key}|{fp[:8]}"
                env_id = intake.envelope_id(CHANNEL, key)
                if env_id in seen or env_id in index or env_id in pending:
                    out["duplicates"] += 1
                    continue

            a = analysed.get(i) or _analyse(ev, entry)
            category = a["category"]
            if category:
                _flag(persona, env_id, ev["chat"], sender, ev["time"], category)
                if ev["kind"] == "update" and env_id in index:
                    _drop_fact(persona, env_id)
                    index.pop(env_id, None)
                out["held_back"] += 1
                continue

            fact, display = a["fact"], a["display"]
            env = intake.Envelope(
                channel=CHANNEL, native_id=key, received=_iso(ev["time"]),
                sender_address=sender, sender_display=display, subject=fact["subject"],
                body="", thread_id="",
                signals={"whatsapp": {"type": fact["type"], "kind": kind,
                                      "action": fact["action"]}})
            row = {"id": env_id, "native_id": key, "chat": ev["chat"], "kind": kind,
                   "time": _iso(ev["time"]), "event_time": fact["when"], "type": fact["type"],
                   "sender_known": bool(display), "awaiting_reply": fact["awaiting_reply"],
                   "resurfaced_at": None, "delivered_at": None, "fp": fp}
            if ev["kind"] == "update" and env_id in index:
                result = intake.classify(env, cfg, {})
                revise(persona, env, result)
                row["resurfaced_at"] = index[env_id].get("resurfaced_at")
                row["delivered_at"] = index[env_id].get("delivered_at")
                index[env_id] = row
                out["updated"] += 1
                out["action_needed"] |= result.category == "action_required"
                continue
            envelopes.append(env)
            pending[env_id] = row

        if envelopes:
            res = intake.ingest(envelopes, persona, cfg=cfg)
            for env in res["processed"]:
                index[env.id] = pending[env.id]
                out["accepted"] += 1
                if res["results"][env.id].category == "action_required":
                    out["action_needed"] = True
            out["duplicates"] += len(res["duplicates"])
        _write_jsonl(_index_path(persona), list(index.values()))

        if markers:
            last = state.setdefault("last_reply", {})
            for chat, t in markers:
                last[chat] = max(int(last.get(chat) or 0), t)
        if cursor is not None:
            state["cursor"] = cursor
        _save_state(state, persona)

    for chat, t in markers:
        _reply_marker_evidence(persona, chat, t, index)
    return out


def _reply_marker_evidence(persona, chat: str, t: int, index: dict) -> None:
    ids = {r["id"] for r in index.values()
           if r.get("chat") == chat and r.get("type") in _ACTION_TYPES and r.get("time", "") < _iso(t)}
    if not ids:
        return
    try:
        from tools.obligations import match_reply_marker
        match_reply_marker(ids, _iso(t), persona=persona)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[whatsapp] reply-marker evidence check failed: {exc}")


def revise(persona: str | None, env: intake.Envelope, result) -> int:
    """An update (plan P2): replace the stored fact for that envelope. `seen_at` is kept, so a
    fact its domain has already read does not re-surface by being edited."""
    def transform(row: dict):
        if row.get("id") != env.id:
            return row
        new = dict(row)
        new.update({"subject": env.subject[:200], "sender": env.sender_address,
                    "sender_display": env.sender_display, "category": result.category,
                    "disposition": result.disposition, "domain": result.domain,
                    "source": result.source, "reason": result.reason,
                    "revised_at": datetime.now().isoformat(timespec="seconds")})
        return new
    return intake._rewrite_records(transform, persona)


def _drop_fact(persona, env_id: str) -> None:
    intake._rewrite_records(lambda r: None if r.get("id") == env_id else r, persona)


# ---------------------------------------------------------------------------
# V6 — the awaiting-reply backstop, and its one context line
# ---------------------------------------------------------------------------

def _answered(row: dict, state: dict) -> bool:
    last = int((state.get("last_reply") or {}).get(row.get("chat")) or 0)
    return bool(last) and _iso(last) > str(row.get("time") or "")


def backstop(persona: str | None, now: datetime | None = None) -> int:
    """Mark for re-surfacing, once, each one-to-one question or proposal unanswered past 24 h and
    still relevant (W8; decision A's tolerance: a question answered only by a message the
    increments leave out may be re-raised once)."""
    now = now or datetime.now()
    marked = 0
    with intake._state_lock(persona):
        rows = _read_jsonl(_index_path(persona))
        state = _load_state(persona)
        for r in rows:
            if (r.get("kind") != "one_to_one" or not r.get("awaiting_reply")
                    or r.get("type") not in ("question", "proposal") or r.get("resurfaced_at")):
                continue
            try:
                sent = datetime.fromisoformat(r["time"])
            except Exception:  # noqa: BLE001
                continue
            if now - sent < timedelta(hours=RESURFACE_AFTER_HOURS):
                continue
            ev = r.get("event_time")
            if ev:
                try:
                    if datetime.fromisoformat(ev if " " in ev else ev + " 23:59") < now:
                        continue
                except Exception:  # noqa: BLE001
                    continue
            elif now - sent > timedelta(hours=NO_EVENT_TIME_RELEVANT_HOURS):
                continue
            if _answered(r, state):
                continue
            r["resurfaced_at"] = now.isoformat(timespec="seconds")
            marked += 1
        if marked:
            _write_jsonl(_index_path(persona), rows)
    return marked


def context_lines(persona: str | None, now: datetime | None = None) -> list[str]:
    """`[WhatsApp — still unanswered]`, offered to every context load within DELIVERY_WINDOW_MIN
    of the first that showed it (Coordinator and Synth of one session), then never again. A reply
    marker that arrived meanwhile clears it."""
    from tools.untrusted import wrap_untrusted
    now = now or datetime.now()
    path = _index_path(persona)
    if not path.exists():
        return []
    items: list[str] = []
    with intake._state_lock(persona):
        rows = _read_jsonl(path)
        state = _load_state(persona)
        records = None
        changed = False
        for r in rows:
            if not r.get("resurfaced_at") or _answered(r, state):
                continue
            first = r.get("delivered_at")
            if first:
                try:
                    if now - datetime.fromisoformat(first) > timedelta(minutes=DELIVERY_WINDOW_MIN):
                        continue
                except Exception:  # noqa: BLE001
                    continue
            else:
                r["delivered_at"] = now.isoformat(timespec="seconds")
                changed = True
            if records is None:
                records = {x.get("id"): x for x in intake.read_records(persona=persona)
                           if x.get("channel") == CHANNEL}
            rec = records.get(r["id"])
            if rec:
                items.append(f"- {rec.get('subject')}")
        if changed:
            _write_jsonl(path, rows)
    if not items:
        return []
    return ["[WhatsApp — still unanswered after a day; raise it once, gently]\n"
            + wrap_untrusted("\n".join(items), source="whatsapp facts")]


# ---------------------------------------------------------------------------
# V8 purge (W3), the user's opt-in deletion (decision C), V9 expiry (W6)
# ---------------------------------------------------------------------------

def _forget(persona, ids: set[str]) -> int:
    """Delete these facts everywhere the channel keeps them: records, seen, index, flags, and
    pending WhatsApp cards. Answered cards stay — they record a tap the user made."""
    if not ids:
        return 0
    with intake._state_lock(persona):
        n = intake._rewrite_records(lambda r: None if r.get("id") in ids else r, persona)
        seen = intake._load_seen(persona)
        if any(i in seen for i in ids):
            intake._save_seen({k: v for k, v in seen.items() if k not in ids}, persona)
        rows = _read_jsonl(_index_path(persona))
        _write_jsonl(_index_path(persona), [r for r in rows if r.get("id") not in ids])
    try:
        from tools.obligations import drop_pending_proposals
        drop_pending_proposals(ids, source="whatsapp", persona=persona)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[whatsapp] pending cards not removed: {exc}")
    return n


def purge_chat(persona: str | None, chat: str) -> int:
    """Un-sharing a chat (W3): everything the channel holds for it, at once."""
    with intake._state_lock(persona):
        ids = {r["id"] for r in _read_jsonl(_index_path(persona)) if r.get("chat") == chat}
        n = _forget(persona, ids)
        flags = _read_jsonl(_flags_path(persona))
        kept = [f for f in flags if f.get("chat") != chat]
        if len(kept) != len(flags):
            _write_jsonl(_flags_path(persona), kept)
        state = _load_state(persona)
        if chat in (state.get("last_reply") or {}):
            state["last_reply"].pop(chat)
            _save_state(state, persona)
    return n


def delete_all(persona: str | None) -> dict:
    """The user's own opt-in (decision C): every WhatsApp fact, flag, marker, the share list, the
    cursor and the salt. Not gated on the channel being open — withdrawing consent first must not
    take away the means to delete."""
    with intake._state_lock(persona):
        ids = {r["id"] for r in _read_jsonl(_index_path(persona)) if r.get("id")}
        ids |= {r.get("id") for r in intake.read_records(persona=persona)
                if r.get("channel") == CHANNEL and r.get("id")}
        n = _forget(persona, ids)
        flags = len(_read_jsonl(_flags_path(persona)))
        for path in (_index_path(persona), _flags_path(persona), _state_path(persona)):
            if path.exists():
                path.unlink()
    return {"deleted_facts": n, "deleted_flags": flags}


def _task_held_ids(persona) -> set[str]:
    try:
        from tools.obligations import _load, _norm
        held = set()
        for t in _load(persona):
            t = _norm(t)
            if t.get("source_id"):
                held.add(t["source_id"])
            for p in t.get("proposals") or []:
                if p.get("envelope_id"):
                    held.add(p["envelope_id"])
        return held
    except Exception as exc:  # noqa: BLE001 — unsure what a task holds → expire nothing
        logger.warning(f"[whatsapp] task lookup failed — expiry skipped: {exc}")
        return {"*"}


def expire(persona: str | None, now: datetime | None = None) -> int:
    """Facts and flags past RETENTION_DAYS go, unless a task carries the fact (V9). The index is
    read first, so an hour with nothing to expire costs one small read and no rewrite."""
    now = now or datetime.now()
    cutoff = (now - timedelta(days=RETENTION_DAYS)).isoformat(timespec="seconds")
    path = _index_path(persona)
    old = [r for r in _read_jsonl(path) if str(r.get("time") or "") < cutoff] if path.exists() else []
    n = 0
    if old:
        held = _task_held_ids(persona)
        if "*" not in held:
            n = _forget(persona, {r["id"] for r in old if r["id"] not in held})
    fpath = _flags_path(persona)
    if fpath.exists():
        with intake._state_lock(persona):
            flags = _read_jsonl(fpath)
            kept = [f for f in flags if str(f.get("time") or "") >= cutoff]
            if len(kept) != len(flags):
                _write_jsonl(fpath, kept)
    return n


def hourly(persona: str | None, cfg: dict | None = None) -> None:
    """From intake.sweep(), every hour whatever the switches say: expiry always; the backstop only
    while the channel is open. Does nothing at all for a user who never had the channel."""
    if not _index_path(persona).exists() and not _flags_path(persona).exists():
        return
    expire(persona)
    if channel_open(persona, cfg):
        backstop(persona)
