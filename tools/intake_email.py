"""
tools/intake_email.py — the email adapter for the intake pipeline.

Turns IMAP messages into `Envelope` objects and does nothing else. De-duplication,
classification, the ledger and all state belong to tools/intake.py — that division is
what keeps the next adapter (Telegram, SMS) small enough to be worth writing.

**Everything here reuses tools/mail.py rather than reimplementing it.** `_body_text`
alone encodes the HTML fallback, the attachment refusal and the whitespace collapsing;
a second copy would drift, and the drift would be invisible because nothing compares
them. This module adds exactly one thing mail.py does not need: the transport headers
that let Python classify a message without reading a word of its body.

**Read-only, by the same mechanism as the rest of mail.py.** BODY.PEEK and
`readonly=True`, so a sweep running every hour never marks the user's mail as read.
Getting this wrong would be highly visible and highly annoying, which is why it is
stated here as well as there.

The headers that do the work:

  List-Unsubscribe / List-ID   present on essentially all legitimate bulk mail
  Precedence: bulk|list|junk   the older convention, still widely set
  Auto-Submitted               RFC 3834 — machine-generated, not a person
  X-GM-LABELS                  Gmail's own category verdict, free and already computed

That last one is a Gmail IMAP extension. It is attempted only against Gmail hosts and
its failure is never an error — an adapter that broke the sweep on a non-Gmail account
because it asked for a proprietary field would be trading the common case for the
convenient one.
"""

from __future__ import annotations

import email
import email.policy
import email.utils
import imaplib
import logging
import re

from tools.intake import Envelope, register_adapter
from tools.mail import (TIMEOUT_SECONDS, _body_text, _decode, _imap_quote,
                        _load_config)

logger = logging.getLogger(__name__)

# Independent of mail.py's MAX_BODY_CHARS. Classification needs the opening of a
# message, not the whole of it, and the intake path pays for every character twice —
# once in the extractor's context and once in the injection surface it presents.
ADAPTER_BODY_CHARS = 2_000

_BULK_PRECEDENCE = {"bulk", "list", "junk"}


def _clean_label(raw: str) -> str:
    """Gmail returns labels as an IMAP atom list, quoted and escaped in its own way."""
    return raw.strip().strip('"').lstrip("\\").lower()


def _parse_labels(payload) -> list[str]:
    """Pull label names out of an `X-GM-LABELS (...)` fetch response."""
    if payload is None:
        return []
    text = payload.decode("utf-8", "replace") if isinstance(payload, bytes) else str(payload)
    match = re.search(r"X-GM-LABELS\s*\(([^)]*)\)", text, re.IGNORECASE)
    if not match:
        return []
    inner = match.group(1)
    return [_clean_label(tok) for tok in re.findall(r'"[^"]*"|\S+', inner) if tok.strip()]


def _received_iso(msg) -> str:
    """Sender-stated Date, normalised. Falls back to empty rather than to `now`.

    A wrong-but-plausible timestamp is worse than a missing one here: `received` orders
    the digest and picks the newest message in a thread, and a message stamped `now`
    because its header was unparseable would win both.
    """
    raw = msg.get("Date")
    if not raw:
        return ""
    try:
        return email.utils.parsedate_to_datetime(raw).isoformat(timespec="seconds")
    except Exception:
        return ""


def _signals(msg, labels: list[str]) -> dict:
    """Transport-level facts. No body, no cost, no untrusted text interpreted."""
    precedence = (msg.get("Precedence") or "").strip().lower()
    list_id = _decode(msg.get("List-ID"))
    signals = {
        "bulk": precedence in _BULK_PRECEDENCE,
        "list_unsubscribe": bool(msg.get("List-Unsubscribe")),
        "auto_submitted": (msg.get("Auto-Submitted") or "no").strip().lower() != "no",
        "labels": labels,
    }
    if list_id:
        # The bracketed form is the stable part: "Acme News <news.acme.com>".
        match = re.search(r"<([^>]+)>", list_id)
        signals["list_id"] = (match.group(1) if match else list_id).strip().lower()
    return signals


def _thread_id(msg) -> str:
    """The root of the thread, from References or In-Reply-To.

    First entry in References is the thread root and is stable across the whole
    conversation; In-Reply-To only reaches the immediate parent, which would split a
    long thread into overlapping pairs.
    """
    references = (msg.get("References") or "").split()
    if references:
        return references[0].strip()
    parent = (msg.get("In-Reply-To") or "").strip()
    return parent or (msg.get("Message-ID") or "").strip()


# How many of the newest messages the header pass inspects for unseen mail each
# sweep. This bounds two things at once: the metadata cost of an idle sweep (one
# FETCH of this many header blocks, no bodies) and how deep a backlog can drain —
# anything older than the window when intake is first enabled is never triaged,
# which is the honest residual of the 2026-08-19 review's finding 5. 500 covers any
# plausible overnight accumulation and most first-enables; a genuinely deeper
# historical backlog is a one-off manual import, not a sweep's job.
_SCAN_WINDOW = 500

_HEADER_SPEC = "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID FROM SUBJECT DATE)])"


def _native_id(msg) -> str:
    """The stable per-message identity, from headers alone.

    Message-ID when present. A message without one (rare, non-conforming) would get a
    fresh envelope id every sweep and be re-processed forever, so synthesise a stable
    one from what cannot change. ONE implementation used by both the header pass and
    the full fetch — the seen-set keys on the hash of this value, so two spellings
    would quietly break de-duplication.
    """
    native = (msg.get("Message-ID") or "").strip()
    if native:
        return native
    _, address = email.utils.parseaddr(_decode(msg.get("From")))
    return f"{address}|{_decode(msg.get('Subject'))}|{msg.get('Date')}"


def _seq_of(prefix: bytes) -> bytes | None:
    """The sequence number leading a FETCH response item, e.g. b'42 (BODY[...'."""
    match = re.match(rb"(\d+)", prefix or b"")
    return match.group(1) if match else None


def fetch(limit: int = 50, skip=None) -> list[Envelope]:
    """Unseen messages from the configured folder, oldest first, as envelopes.

    Two passes, and the split is the point (2026-08-19 review, findings 5 and 8):

    1. **Header pass** — one FETCH of identity headers for the newest `_SCAN_WINDOW`
       messages, `skip(native_id)` deciding which are new. An idle hourly sweep ends
       here: metadata only, no bodies, however large the attachments in the mailbox.
    2. **Body pass** — full BODY.PEEK for at most `limit` unseen messages, **oldest
       first**, so a backlog (overnight accumulation, first enable) drains across
       sweeps instead of the newest `limit` shadowing the rest forever.

    Without `skip` the old behaviour stands: newest `limit`, bodies and all.

    Returns an empty list when email is unconfigured or disabled — not an error. The
    sweep runs on a timer against every persona, and most of them have no mailbox set
    up; a raise here would fill the scheduler log with failures that mean nothing.
    Connection and login problems DO raise, because those are real and the sweep
    reports them per-channel.
    """
    cfg = _load_config()
    if not cfg.get("enabled"):
        return []

    host = (cfg.get("host") or "").strip()
    auth = cfg.get("auth") or {}
    username = (auth.get("username") or "").strip()
    password = auth.get("password") or ""
    if not (host and username and password):
        logger.info("[intake] email enabled but not fully configured — skipping")
        return []

    folder = cfg.get("default_folder") or "INBOX"
    wants_labels = "gmail" in host.lower()
    limit = max(1, int(limit))

    conn = imaplib.IMAP4_SSL(host, timeout=TIMEOUT_SECONDS)
    envelopes: list[Envelope] = []
    try:
        conn.login(username, password)
        status, _ = conn.select(_imap_quote(folder), readonly=True)
        if status != "OK":
            raise RuntimeError(f"could not open folder {folder!r}")

        status, data = conn.search(None, "ALL")
        if status != "OK":
            raise RuntimeError("IMAP search failed")

        ids = data[0].split()
        if not ids:
            return []

        if skip is None:
            wanted = ids[-limit:]
        else:
            scan = ids[-_SCAN_WINDOW:]
            # One range FETCH for the whole window — sequence numbers from a search
            # are ascending, so the span is contiguous.
            span = (f"{scan[0].decode()}:{scan[-1].decode()}"
                    if len(scan) > 1 else scan[0].decode())
            status, header_data = conn.fetch(span, _HEADER_SPEC)
            if status != "OK":
                raise RuntimeError("IMAP header fetch failed")
            wanted = []
            for item in header_data:
                if not isinstance(item, tuple):
                    continue
                seq = _seq_of(item[0])
                if seq is None:
                    continue
                msg = email.message_from_bytes(item[1], policy=email.policy.default)
                if not skip(_native_id(msg)):
                    wanted.append(seq)
            wanted = wanted[:limit]        # ascending → oldest unseen first

        spec = "(X-GM-LABELS BODY.PEEK[])" if wants_labels else "(BODY.PEEK[])"
        for mid in wanted:
            try:
                status, msg_data = conn.fetch(mid, spec)
            except imaplib.IMAP4.error:
                if not wants_labels:
                    raise
                # A Gmail-looking host that rejects the extension: fall back once and
                # keep going without labels rather than losing the message entirely.
                wants_labels = False
                spec = "(BODY.PEEK[])"
                status, msg_data = conn.fetch(mid, spec)

            if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                continue

            labels = _parse_labels(msg_data[0][0]) if wants_labels else []
            msg = email.message_from_bytes(msg_data[0][1], policy=email.policy.default)
            display, address = email.utils.parseaddr(_decode(msg.get("From")))

            envelopes.append(Envelope(
                channel="email",
                native_id=_native_id(msg),
                received=_received_iso(msg),
                sender_address=address.lower(),
                sender_display=display or address,
                subject=_decode(msg.get("Subject")),
                body=_body_text(msg)[:ADAPTER_BODY_CHARS],
                thread_id=_thread_id(msg),
                signals=_signals(msg, labels),
            ))
    finally:
        try:
            conn.close()
        except Exception:
            pass
        try:
            conn.logout()
        except Exception:
            pass

    return envelopes


register_adapter("email", fetch)
