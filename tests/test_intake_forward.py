"""
tests/test_intake_forward.py — the self-forward unwrap, and the gate that guards it.

WHAT IS ACTUALLY UNDER TEST. Unwrapping takes a sender identity out of a message BODY,
which is attacker-writable, and hands it to a classifier whose decisions the sender
ledger learns from. The feature is two lines of parsing; the gate is the whole build.
So the spoofing cases below are not edge cases — they are the reason the module exists
in the form it does.

Run: python3 tests/test_intake_forward.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.intake import Envelope                     # noqa: E402
from tools.intake_forward import unwrap               # noqa: E402

CFG = {"forwarding": {"enabled": True, "own_addresses": ["mike@example.com"]}}

GOOD_AUTH = ("mx.google.com; dkim=pass header.i=@example.com; "
             "spf=pass smtp.mailfrom=mike@example.com")

FWD_BODY = (
    "Here's the one I mentioned.\n\n"
    "---------- Forwarded message ---------\n"
    "From: Acme Billing <billing@acme.com>\n"
    "Date: Mon, 1 Sep 2026 at 09:14\n"
    "Subject: Your September statement\n"
    "To: Mike <mike@example.com>\n\n"
    "Your statement is ready.\n"
)


def env(sender="mike@example.com", body=FWD_BODY, signals=None):
    return Envelope(channel="email", native_id="1", received="2026-09-04T10:00:00",
                    sender_address=sender, sender_display="Mike",
                    subject="Fwd: Your September statement", body=body,
                    signals=signals or {})


checks: list[tuple[str, bool]] = []


def check(name: str, condition: bool) -> None:
    checks.append((name, bool(condition)))


# ── The feature works at all ────────────────────────────────────────────────
out, ledger_safe = unwrap(env(), CFG, GOOD_AUTH)
check("authenticated self-forward is unwrapped to the original sender",
      out.sender_address == "billing@acme.com")
check("the forwarder is recorded in signals, not lost",
      out.signals.get("unwrapped_from") == "mike@example.com")
check("an unwrapped envelope is marked as forwarded",
      out.signals.get("forwarded") is True)
check("an unwrapped envelope is NOT safe to teach the ledger from",
      ledger_safe is False)
check("the original envelope is not mutated in place",
      env().sender_address == "mike@example.com")

# ── The gate: spoofing must not get through ─────────────────────────────────
out, safe = unwrap(env(), CFG, "")
check("SPOOF: no Authentication-Results at all → left wrapped",
      out.sender_address == "mike@example.com" and safe is True)

out, safe = unwrap(env(), CFG, "mx.google.com; dkim=fail header.i=@example.com")
check("SPOOF: dkim=fail → left wrapped",
      out.sender_address == "mike@example.com" and safe is True)

out, safe = unwrap(env(), CFG, "mx.google.com; dkim=pass header.i=@attacker.com")
check("SPOOF: dkim passes for a DIFFERENT domain → left wrapped "
      "(a valid signature from anywhere must not satisfy the gate)",
      out.sender_address == "mike@example.com" and safe is True)

out, safe = unwrap(env(), CFG, "mx.google.com; dkim=pass")
check("SPOOF: dkim=pass with no signing domain → left wrapped",
      out.sender_address == "mike@example.com" and safe is True)

out, safe = unwrap(env(sender="stranger@evil.com"), CFG, GOOD_AUTH)
check("a forward from someone who is not the user is never unwrapped",
      out.sender_address == "stranger@evil.com" and safe is True)

# A real message that merely quotes a From: line, with no forwarded-header block.
out, safe = unwrap(env(body="Reply below.\nFrom: ceo@bank.com\nPay this now."),
                   CFG, GOOD_AUTH)
check("a bare 'From:' line with no forwarded block is not treated as a forward",
      out.sender_address == "mike@example.com" and safe is True)

# The block exists but the From: sits far past the scan window.
far = ("---------- Forwarded message ---------\n" + ("filler line\n" * 300)
       + "From: late@acme.com\n")
out, safe = unwrap(env(body=far), CFG, GOOD_AUTH)
check("a From: beyond the scan window is not picked up "
      "(prevents reassigning the sender from an unrelated quoted thread)",
      out.sender_address == "mike@example.com")

# ── Configuration ───────────────────────────────────────────────────────────
out, safe = unwrap(env(), {"forwarding": {"enabled": False,
                                          "own_addresses": ["mike@example.com"]}},
                   GOOD_AUTH)
check("disabled in config → no unwrap", out.sender_address == "mike@example.com")

out, safe = unwrap(env(), {}, GOOD_AUTH)
check("absent config → no unwrap, no crash", out.sender_address == "mike@example.com")

out, _ = unwrap(env(), {"forwarding": {"enabled": True, "own_addresses": []}}, GOOD_AUTH)
check("empty own_addresses → no unwrap", out.sender_address == "mike@example.com")

# ── Shapes seen in real mail ────────────────────────────────────────────────
apple = ("FYI\n\nBegin forwarded message:\n\n"
         "From: Jane Roe <jane@acme.com>\nSubject: Lunch\n")
out, _ = unwrap(env(body=apple), CFG, GOOD_AUTH)
check("Apple Mail 'Begin forwarded message:' shape is handled",
      out.sender_address == "jane@acme.com")

quoted = ("> ---------- Forwarded message ---------\n"
          "> From: Bob <bob@acme.com>\n> Subject: Hi\n")
out, _ = unwrap(env(body=quoted), CFG, GOOD_AUTH)
check("a quoted ('> ') forwarded block is handled",
      out.sender_address == "bob@acme.com")

arc = "mx.google.com; arc=pass header.d=example.com; dkim=none"
out, _ = unwrap(env(), CFG, arc)
check("arc=pass with a matching domain also satisfies the gate",
      out.sender_address == "billing@acme.com")

sub = "mx.google.com; dkim=pass header.i=@mail.example.com"
out, _ = unwrap(env(), CFG, sub)
check("a subdomain signature of the claimed domain is accepted",
      out.sender_address == "billing@acme.com")

out, _ = unwrap(env(body="---------- Forwarded message ---------\n"
                         "From: Mike <mike@example.com>\n"), CFG, GOOD_AUTH)
check("a forward whose original sender is the user themselves is left alone",
      out.sender_address == "mike@example.com")

# ── Regressions for the two bypasses found by review, 2026-09-04 ────────────
# Neither was covered by the original 20 checks, and both were live.

# 1. A forged AR header sitting beside the real one. An MTA strips only headers with
#    its OWN authserv-id, so anything else in the message is attacker text.
out, safe = unwrap(env(), CFG, "relay.evil.net; dkim=pass header.i=@example.com")
check("BYPASS 1: AR header from an untrusted authserv-id is ignored",
      out.sender_address == "mike@example.com" and safe is True)

out, safe = unwrap(env(), CFG, "mx.google.com; dkim=fail header.i=@example.com")
check("BYPASS 1: the real server's dkim=fail is honoured",
      out.sender_address == "mike@example.com")

# 2. Attacker-chosen identity above the forward marker. The user forwards a message
#    whose body OPENS with a From: line; authentication passes because the user really
#    did forward it, and the wrong sender is the one the code tier routes on.
poisoned = ("From: ceo@bigbank.com\n"
            "Urgent: wire the funds.\n\n"
            "---------- Forwarded message ---------\n"
            "From: Real Sender <real@acme.com>\n")
out, _ = unwrap(env(body=poisoned), CFG, GOOD_AUTH)
check("BYPASS 2: a From: ABOVE the forward marker is ignored; the quoted "
      "header inside the block is what is used",
      out.sender_address == "real@acme.com")

# 3. Gmail's real ARC shape, which the original fixture did not use.
gmail_arc = ("mx.google.com; dkim=none; arc=pass (i=1 spf=pass "
             "spfdomain=example.com dkdomain=example.com dmarc=pass)")
out, _ = unwrap(env(), CFG, gmail_arc)
check("Gmail's actual arc=pass shape (dkdomain= in a parenthetical) is matched",
      out.sender_address == "billing@acme.com")

passed = sum(1 for _, ok in checks if ok)
for name, ok in checks:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
print(f"\n{passed}/{len(checks)} checks pass")
sys.exit(0 if passed == len(checks) else 1)
