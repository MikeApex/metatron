"""
tools/intake_forward.py — see through a message the user forwarded to themselves.

THE PROBLEM, MEASURED. On the 2026-09-04 labelled corpus, **18 of 33 messages** were
forwards from Mike's own address into the intake account. Every signal the code tier
classifies on is about who sent it — the taught `rules:`, the learned sender ledger,
the bulk headers — so on 55% of real inbound all three read "the user", learn nothing,
and hand the message to the model with only a subject and a body. That is most of why
the code tier resolved 1 message in 33.

Unwrapping restores the original sender, and with it the whole code tier.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE SECURITY GATE IS THE POINT OF THIS MODULE, NOT A CHECK ON THE SIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A `From:` line inside a message body is text an attacker writes. Unwrapping means
taking an identity claim out of attacker-controlled bytes and giving it to the
classifier — and the sender ledger LEARNS from what the classifier decides, so a forged
identity does not merely mislead one message, it hardens into a rule that mislabels
that sender's real mail afterwards.

So the unwrap is gated on TWO conditions, and the second is the one that matters:

1. The outer sender is one of the user's own configured addresses, AND
2. **The outer message authenticates as genuinely theirs** — a `dkim=pass` (or
   `arc=pass`) in `Authentication-Results` whose signing domain matches the outer
   sender's domain.

Condition 1 alone is worthless: the `From:` header is trivially forged, so anyone who
can put a message in the inbox can claim to be the user. Condition 2 is what makes the
claim mean something, because it is checked by the receiving mail server against a
published key rather than asserted by the sender.

**A forward that fails authentication is not rejected — it is left wrapped**, and
classified exactly as it is today. Failing closed here means "no worse than before",
which is the right failure: the alternative is discarding real mail because a header
was missing.

WHAT IS DELIBERATELY NOT TRUSTED even after the gate passes: the body's claimed
original sender is used for ROUTING ONLY — the sender ledger is not taught from an
unwrapped envelope (see `unwrap()`'s `ledger_safe` flag). Authentication proves the
user forwarded it; it does not prove the quoted `From:` inside is accurate, because
the user could have forwarded something itself forged. Routing on it is cheap to get
wrong. Learning from it is not.
"""

from __future__ import annotations

import email.utils
import logging
import re
from dataclasses import replace

logger = logging.getLogger(__name__)

# Gmail and most receivers write one of these; the value is the receiver's own verdict,
# not the sender's claim. Checked case-insensitively.
_AUTH_PASS_RE = re.compile(
    r"\b(?P<method>dkim|arc)=pass\b(?P<rest>(?:[^;(]|\([^)]*\))*)", re.IGNORECASE)
# Two shapes, because DKIM and ARC do not write the domain the same way and only the
# first was handled until 2026-09-04. DKIM: `header.i=@example.com` / `header.d=example.com`.
# ARC as Gmail actually emits it: `arc=pass (i=1 spf=pass ... dkdomain=example.com)` —
# a parenthetical with `dkdomain=`/`fromdomain=`, which the header.* pattern never matched.
# So the arc=pass path advertised in the docstring was dead on real mail, and the test
# covering it passed only because its fixture used a shape Gmail does not produce.
_SIGNING_DOMAIN_RE = re.compile(
    r"(?:header\.(?:i|d)|dkdomain|fromdomain)=@?(?P<domain>[A-Za-z0-9.\-]+)",
    re.IGNORECASE)

# The forwarded-header block. Handles the three shapes actually seen in the corpus:
# Gmail's "---------- Forwarded message ---------", Apple Mail's "Begin forwarded
# message:", and a bare quoted header run. Anchored to a From: line either way, because
# that is the only field being extracted.
_FORWARD_MARKERS = (
    "forwarded message",
    "begin forwarded message",
    "original message",
)
_FROM_LINE_RE = re.compile(
    r"^\s*(?:[>\s]*)From:\s*(?P<value>.+)$", re.IGNORECASE | re.MULTILINE)

# How far into the body to look for the forwarded header block. A forwarded header sits
# at the top of the quoted section; scanning the whole body would pick up a `From:` in
# an unrelated quoted thread further down and silently reassign the sender to it.
_SCAN_CHARS = 1_200


def _trusted_authserv(cfg: dict) -> set[str]:
    """authserv-ids whose verdict we accept. Configurable; Gmail's is the default."""
    fwd = (cfg or {}).get("forwarding") or {}
    vals = fwd.get("trusted_authserv") or ["mx.google.com"]
    return {str(v).strip().lower() for v in vals if str(v).strip()}


def _authenticates_as(sender_address: str, auth_results: str,
                      trusted: set[str] | None = None) -> bool:
    """True when the receiver verified this really came from the sender's domain.

    Requires the signing domain to MATCH the claimed sender's domain. A bare
    `dkim=pass` is not sufficient: forwarded and relayed mail routinely carries a
    passing signature for some *other* domain, and accepting that would let any
    correctly-signed message from anywhere satisfy the gate.
    """
    if not sender_address or "@" not in sender_address or not auth_results:
        return False
    claimed = sender_address.rsplit("@", 1)[-1].strip().lower()
    if not claimed:
        return False

    # ONLY THE RECEIVING SERVER'S OWN VERDICT COUNTS (fixed 2026-09-04, found by review).
    # An MTA strips only the Authentication-Results headers bearing its OWN authserv-id;
    # any others are passed through as ordinary text. So an attacker can simply add
    #   Authentication-Results: relay.evil.net; dkim=pass header.i=@example.com
    # and, if every AR header is searched, that forged line satisfies the gate — even
    # with the real server's `dkim=fail` sitting beside it. The first implementation
    # joined them all with get_all() and searched the lot, which made the gate
    # decorative: the bytes it trusted were the attacker's.
    #
    # Two rules now: take only the TOPMOST header (prepended last, so it is the
    # receiving MTA's), and require its authserv-id to be one we trust.
    first = auth_results.split("\x00")[0] if "\x00" in auth_results else auth_results
    first = first.strip()
    if not first:
        return False
    authserv = first.split(";", 1)[0].strip().lower()
    allowed = trusted if trusted is not None else {"mx.google.com"}
    if authserv not in allowed:
        logger.info("[intake] ignoring Authentication-Results from an untrusted "
                    "authserv-id %r (trusted: %s)", authserv, sorted(allowed))
        return False

    for m in _AUTH_PASS_RE.finditer(first):
        rest = m.group("rest") or ""
        dom = _SIGNING_DOMAIN_RE.search(rest)
        if not dom:
            continue
        signed = dom.group("domain").strip().lower()
        # Accept an exact match or a subdomain of the claimed domain.
        if signed == claimed or signed.endswith("." + claimed):
            return True
    return False


def _original_sender(body: str) -> tuple[str, str]:
    """`(display, address)` claimed by the forwarded header block, or ("", "")."""
    if not body:
        return "", ""
    head = body[:_SCAN_CHARS]
    lowered = head.lower()
    # SEARCH ONLY AFTER THE MARKER (fixed 2026-09-04, found by review). Scanning the
    # whole window let an attacker choose the identity: send a message whose body OPENS
    # with `From: ceo@bigbank.com`, and when the user forwards it — authenticated, so
    # the gate passes — that line is found before the genuine forwarded header and
    # becomes the sender the entire code tier routes on. The marker is the only thing
    # separating the user's mail client's own header block from attacker text above it.
    positions = [lowered.find(m) for m in _FORWARD_MARKERS]
    positions = [i for i in positions if i >= 0]
    if not positions:
        # No forwarded-header block. A "Fwd:" subject with no block is a user typing a
        # note, not a forward with a recoverable sender — leave it alone.
        return "", ""
    match = _FROM_LINE_RE.search(head, min(positions))
    if not match:
        return "", ""
    display, address = email.utils.parseaddr(match.group("value").strip())
    address = (address or "").strip().lower()
    if "@" not in address:
        return "", ""
    return (display or address), address


def own_addresses(cfg: dict) -> set[str]:
    """The user's own addresses, from `forwarding.own_addresses` in intake.yaml."""
    fwd = (cfg or {}).get("forwarding") or {}
    return {str(a).strip().lower() for a in (fwd.get("own_addresses") or []) if str(a).strip()}


def enabled(cfg: dict) -> bool:
    fwd = (cfg or {}).get("forwarding") or {}
    return bool(fwd.get("enabled", False))


def unwrap(env, cfg: dict, auth_results: str = "") -> tuple[object, bool]:
    """Return `(envelope, ledger_safe)`.

    When the message is an authenticated self-forward carrying a recoverable original
    sender, the returned envelope has that sender substituted and
    `signals["unwrapped_from"]` recording who forwarded it. Otherwise the envelope is
    returned untouched.

    `ledger_safe` is False for an unwrapped envelope: the caller must not teach the
    sender ledger from it. See the module docstring — authentication proves the user
    forwarded the message, not that the quoted header inside is truthful.
    """
    if not enabled(cfg):
        return env, True
    sender = (getattr(env, "sender_address", "") or "").lower()
    if not sender or sender not in own_addresses(cfg):
        return env, True

    if not _authenticates_as(sender, auth_results, _trusted_authserv(cfg)):
        logger.info("[intake] self-forward from %s not unwrapped: no matching "
                    "dkim/arc pass — left wrapped, classified as-is", sender)
        return env, True

    display, address = _original_sender(getattr(env, "body", "") or "")
    if not address or address == sender:
        return env, True

    signals = dict(getattr(env, "signals", None) or {})
    signals["unwrapped_from"] = sender
    signals["forwarded"] = True
    unwrapped = replace(env, sender_address=address,
                        sender_display=display or address, signals=signals)
    logger.info("[intake] unwrapped an authenticated self-forward: routing on the "
                "original sender instead of %s", sender)
    return unwrapped, False
