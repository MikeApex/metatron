"""
tests/test_tone_own_copies.py — the user's own mail sitting in the connected inbox counts as
their writing for tone, only when it authenticates, and only their own words [DB-0810-05].

Mike, 2026-10-29: "Is writing tone picked up at all from the user's inbox, including copies of
emails from their sent folder?" It was not. The profiler read INBOX mail FROM the contact and the
connected account's Sent folder TO them. That account is purpose-built and holds almost nothing
Mike wrote, so his copies — BCC'd or forwarded in from his everyday address — were the only
material, and they were ignored. His conditions: authenticated (a From: is trivially forged) and
no quoted or forwarded passages.

No network: a fake IMAP connection serves canned RFC 822 messages.

    python3 tests/test_tone_own_copies.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.intake as INTAKE  # noqa: E402
import tools.mail as M  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, condition, detail))


# --- _strip_quoted: only the user's own words survive -----------------------------------

GMAIL_WRAPPED = ("Sounds good, see you at 12.\n\nM\n\n"
                 "On Tue, 8 Sep 2026 at 10:02, Iva Diamond <iva.stod@gmail.com>\nwrote:\n"
                 "Lunch at Bancone?")
APPLE_FWD = ("Thought you'd want this.\n\nBegin forwarded message:\n\n"
             "From: Prudential <noreply@pru.co.uk>\nSubject: Your policy")
OUTLOOK = ("Thanks Rowan — Tuesday works.\n\nMike\n\nFrom: Rowan Hand <rowan.hand@bp.com>\n"
           "Sent: 27 October 2026 09:14\nTo: Mike\nSubject: pint?\n\nFancy a pint Tuesday?")
SEPARATOR = "Yes please.\n________________________________\nFrom: someone\nold thread"
PLAIN = "Hi Iva,\n\nRunning ten minutes late.\n\nFrom the train, Mike"

check("Gmail's two-line attribution and the quote under it are cut",
      M._strip_quoted(GMAIL_WRAPPED) == "Sounds good, see you at 12.\n\nM", repr(M._strip_quoted(GMAIL_WRAPPED)))
check("Apple Mail's 'Begin forwarded message:' block is cut",
      M._strip_quoted(APPLE_FWD) == "Thought you'd want this.", repr(M._strip_quoted(APPLE_FWD)))
check("Outlook's From/Sent reply header and the thread under it are cut",
      M._strip_quoted(OUTLOOK) == "Thanks Rowan — Tuesday works.\n\nMike", repr(M._strip_quoted(OUTLOOK)))
check("Outlook's underscore separator is cut", M._strip_quoted(SEPARATOR) == "Yes please.")
check("a message with nothing quoted is left whole — 'From the train' is not a header",
      M._strip_quoted(PLAIN) == PLAIN, repr(M._strip_quoted(PLAIN)))


# --- _own_copies: authenticated copies only ---------------------------------------------

OWN, CONTACT, ACCOUNT = "diamond.mike@gmail.com", "iva.stod@gmail.com", "diamond.mike.mt@gmail.com"


def _msg(auth: str, body: str) -> bytes:
    return (f"Authentication-Results: {auth}\r\nFrom: Mike <{OWN}>\r\nTo: {CONTACT}\r\n"
            f"Subject: lunch\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{body}\r\n").encode()


GENUINE = _msg("mx.google.com; dkim=pass header.i=@gmail.com header.s=20230601",
               "Hi Iva, see you at Bancone.\n\nM\n\nOn Tue, 8 Sep 2026, Iva wrote:\n> Lunch?")
FORGED = _msg("relay.evil.net; dkim=pass header.i=@gmail.com",
              "Wire the money to this account today.")
NO_AUTH = (f"From: Mike <{OWN}>\r\nTo: {CONTACT}\r\nSubject: x\r\n\r\nUnsigned copy.\r\n").encode()
_STORE = {b"1": GENUINE, b"2": FORGED, b"3": NO_AUTH}


class _FakeConn:
    def __init__(self):
        self.searches = []

    def select(self, folder, readonly=True):
        return ("OK", [b"3"])

    def search(self, charset, *terms):
        self.searches.append(terms)
        terms_l = [str(t).lower() for t in terms]
        is_first_tier = "before" not in terms_l
        wanted = ("from" in terms_l and f'"{OWN}"' in terms_l and "to" in terms_l
                  and f'"{CONTACT}"' in terms_l)
        return ("OK", [b"1 2 3" if (wanted and is_first_tier) else b""])

    def fetch(self, chunk, spec):
        ids = chunk.split(",")
        return ("OK", [(f"{i} (BODY[] {{1}}".encode(), _STORE[i.encode()]) for i in ids])


_orig = (M._own_addresses, INTAKE.load_config)
M._own_addresses = lambda: {OWN, ACCOUNT}
INTAKE.load_config = lambda persona=None: {}
try:
    conn = _FakeConn()
    copies = M._own_copies(conn, CONTACT, ACCOUNT)
    check("an authenticated copy of the user's own mail to the contact is kept",
          len(copies) == 1 and "see you at Bancone" in copies[0], repr(copies))
    check("and its quoted reply is not part of it", copies and "Lunch?" not in copies[0], repr(copies))
    check("a copy whose dkim=pass comes from an untrusted server is dropped",
          not any("Wire the money" in c for c in copies), repr(copies))
    check("an unsigned copy is dropped", not any("Unsigned copy" in c for c in copies), repr(copies))
    check("the connected account itself is not searched as an 'own copy' sender",
          not any(f'"{ACCOUNT}"' in t for t in conn.searches), repr(conn.searches))
    check("the search asks for FROM the user AND TO the contact",
          any("FROM" in t and "TO" in t for t in conn.searches), repr(conn.searches[:1]))
finally:
    M._own_addresses, INTAKE.load_config = _orig


if __name__ == "__main__":
    failed = [r for r in _results if not r[1]]
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if not ok and detail else ""))
    print(f"\n{len(_results) - len(failed)}/{len(_results)} passed")
    sys.exit(1 if failed else 0)
