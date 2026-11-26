"""
tests/test_forward_recipient_trail.py — a forwarded message keeps who it was first sent to.

The recovered recipients are DISPLAY ONLY: headers and quoted To: lines are sender-writable,
so they must never unlock the self-forward unwrap, change the sender, or reach the ledger.

Run: python3 tests/test_forward_recipient_trail.py
"""
from __future__ import annotations

import email
import email.policy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.intake import Envelope                                   # noqa: E402
from tools.intake_email import _signals                             # noqa: E402
from tools.intake_forward import header_recipients, unwrap          # noqa: E402

CFG = {"forwarding": {"enabled": True, "own_addresses": ["owner@example.com"]}}
GOOD_AUTH = "mx.google.com; dkim=pass header.i=@example.com"


def parse(headers: str):
    return email.message_from_string(headers + "\n\nbody\n", policy=email.policy.default)


def env(sender="owner@example.com", body="", signals=None):
    return Envelope(channel="email", native_id="1", received="2026-11-26T10:00:00",
                    sender_address=sender, sender_display="X", subject="Fwd: hi",
                    body=body, signals=signals or {})


checks = []


def check(name, ok):
    checks.append((name, bool(ok)))


# 1. Auto-forward header chain (earliest hop first).
m = parse("Delivered-To: primary@example.com\nX-Forwarded-To: primary@example.com\n"
          "X-Forwarded-For: relative@example.org primary@example.com\n"
          "Delivered-To: relative@example.org\nFrom: a@acme.com\nTo: relative@example.org")
rec = header_recipients(m)
check("auto-forward chain recovers the original address", "relative@example.org" in rec)
check("auto-forward chain also names the forwarding target", "primary@example.com" in rec)
check("signals carry it", _signals(m, []).get("original_recipients") == rec)

# 2. Ordinary message: one Delivered-To, nothing recovered.
m = parse("Delivered-To: primary@example.com\nFrom: a@acme.com\nTo: primary@example.com")
check("ordinary message is unchanged", header_recipients(m) == [] and
      "original_recipients" not in _signals(m, []))

# 3. Caps and junk.
many = " ".join(f"u{i}@example.com" for i in range(20))
check("count capped", len(header_recipients(parse(f"X-Forwarded-To: {many}\nFrom: a@b.co"))) == 5)
check("junk dropped, long address dropped", header_recipients(parse(
    "X-Forwarded-To: not an address, " + "a" * 300 + "@example.com\nFrom: a@b.co")) == [])

# 4. Inline self-forwards (Gmail, Apple, Outlook shapes), authenticated.
gmail = ("Look\n\n---------- Forwarded message ---------\nFrom: Jane <jane@acme.com>\n"
         "Date: Mon\nSubject: Lunch\nTo: Relative <relative@example.org>, other@example.org\n\nHi\n")
out, safe = unwrap(env(body=gmail), CFG, GOOD_AUTH)
check("gmail inline: sender unwrapped", out.sender_address == "jane@acme.com")
check("gmail inline: original recipients recovered",
      out.signals.get("original_recipients") == ["relative@example.org", "other@example.org"])
check("gmail inline: still ledger-unsafe", safe is False)

apple = ("FYI\n\nBegin forwarded message:\n\nFrom: Jane <jane@acme.com>\n"
         "Subject: Lunch\nTo: relative@example.org\n\nHi\n")
out, _ = unwrap(env(body=apple), CFG, GOOD_AUTH)
check("apple inline recovered", out.signals.get("original_recipients") == ["relative@example.org"])

outlook = ("-----Original Message-----\nFrom: Jane <jane@acme.com>\nSent: Monday\n"
           "To: relative@example.org\nSubject: Lunch\n\nHi\n")
out, _ = unwrap(env(body=outlook), CFG, GOOD_AUTH)
check("outlook inline recovered", out.signals.get("original_recipients") == ["relative@example.org"])

# 5. Header recipients already on the envelope survive and merge.
out, _ = unwrap(env(body=gmail, signals={"original_recipients": ["hop@example.org"]}),
                CFG, GOOD_AUTH)
check("header and inline recipients merge",
      out.signals["original_recipients"][0] == "hop@example.org" and
      "relative@example.org" in out.signals["original_recipients"])

# 6. Spoof: unauthenticated message claiming to be the owner. Recipient may be shown
#    (already on the envelope) but the gate is unchanged: no unwrap, nothing recovered
#    from the body, sender untouched, ledger-safe as before.
out, safe = unwrap(env(body=gmail, signals={"original_recipients": ["spoof@example.net"]}),
                   CFG, "mx.google.com; dkim=fail header.i=@example.com")
check("spoof: sender not unwrapped", out.sender_address == "owner@example.com")
check("spoof: body To: not harvested", out.signals["original_recipients"] == ["spoof@example.net"])
check("spoof: no unwrap markers", "unwrapped_from" not in out.signals and safe is True)
out, _ = unwrap(env(sender="stranger@evil.net", body=gmail), CFG, GOOD_AUTH)
check("non-owner sender: nothing changes", out.sender_address == "stranger@evil.net"
      and "original_recipients" not in out.signals)

# 7. A forged X-Forwarded-To does not make an owner address authenticate.
m = parse("X-Forwarded-To: owner@example.com\nFrom: owner@example.com")
out, _ = unwrap(env(body=gmail, signals=_signals(m, [])), CFG, "")
check("forged header grants nothing", out.sender_address == "owner@example.com"
      and "unwrapped_from" not in out.signals)

passed = sum(ok for _, ok in checks)
for n, ok in checks:
    print(f"  {'PASS' if ok else 'FAIL'}  {n}")
print(f"\n{passed}/{len(checks)} checks pass")
sys.exit(0 if passed == len(checks) else 1)
