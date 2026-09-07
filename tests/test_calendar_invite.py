"""
tests/test_calendar_invite.py — send_calendar_invite, the gate and the payload.

Written with the tool (2026-09-07). The defect being closed is that the assistant
told Mike a person had been invited when nothing had ever been sent: `attendees`
on a calendar write is a private label. These tests hold the two properties that
make the replacement trustworthy — nothing goes out without approval, and what
does go out is a real invitation — plus the resolution rules that stop it being
sent about the wrong event.

Run: python3 tests/test_calendar_invite.py
"""
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.caldav as caldav        # noqa: E402
import tools.mail as mail            # noqa: E402

EVENT = {
    "uid": "evt-1@ai-life-manager",
    "title": "Manny's concert",
    "start": "2026-09-20T19:00:00",
    "end": "2026-09-20T21:00:00",
    "description": "School hall",
    "location": "Bushey Hall",
    "recurrence": "",
}
CONTACT = "iva.diamond@bp.com"
sent: list = []


class _SMTP:
    def __init__(self, *a, **k): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def starttls(self): pass
    def login(self, *a): pass
    def send_message(self, msg): sent.append(msg)


def _patches(events=None):
    """Everything external stubbed: CRM allowlist, calendar, SMTP, mail config."""
    import smtplib
    return [
        mock.patch.object(mail, "_known_recipients",
                          return_value={CONTACT: "Iva Diamond", "mike@example.test": "you"}),
        mock.patch.object(mail, "_load_config",
                          return_value={"auth": {"username": "mike@example.test",
                                                 "password": "x"}}),
        mock.patch.object(caldav, "_load_config",
                          return_value={"enabled": True, "timezone": "Europe/London",
                                        "calendar_url": "https://example.test/cal/"}),
        mock.patch.object(caldav, "_get_event_by_uid", return_value=dict(EVENT)),
        mock.patch.object(caldav, "_query_events",
                          return_value={"events": events if events is not None else [dict(EVENT)]}),
        mock.patch.object(smtplib, "SMTP", _SMTP),
    ]


def run(fn, *args, **kwargs):
    ps = _patches(kwargs.pop("_events", None))
    for p in ps:
        p.start()
    try:
        return fn(*args, **kwargs)
    finally:
        for p in ps:
            p.stop()


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}  {name}")
    return bool(cond)


def main() -> int:
    import tempfile
    results = []

    # Confirmation store must not touch the real persona tree.
    with tempfile.TemporaryDirectory() as tmp:
        import tools.confirm as confirm
        store = Path(tmp) / "pending.json"
        with mock.patch.object(confirm, "_store_path", return_value=store), \
             mock.patch.object(confirm, "_declined_path", return_value=Path(tmp) / "declined.json"):

            # 1. A recipient who is not a saved contact is refused in code.
            r = run(mail.send_calendar_invite, to="stranger@example.com", uid=EVENT["uid"])
            results.append(check("unknown recipient refused",
                                 "error" in r and "not a known recipient" in r["error"]))
            results.append(check("  ...and nothing was sent", not sent))

            # 2. First call sends nothing and asks for approval.
            r = run(mail.send_calendar_invite, to=CONTACT, uid=EVENT["uid"])
            token = r.get("confirm_token") or r.get("token")
            results.append(check("first call is PENDING, not a send",
                                 not sent and "sent" not in str(r.get("status", ""))))
            results.append(check("  ...approval preview names the event and recipient",
                                 "Manny's concert" in str(r) and "Iva Diamond" in str(r)))
            results.append(check("  ...and warns what the recipient will see",
                                 "title, time and location" in str(r)))

            # 3. Approving it sends a real invitation.
            results.append(check("a token was issued", bool(token)))
            if token:
                confirm.approve(token)
                r = run(mail.send_calendar_invite, to=CONTACT, uid=EVENT["uid"],
                        confirm_token=token)
                results.append(check("approved call reports invitation_sent",
                                     r.get("status") == "invitation_sent"))
                results.append(check("  ...exactly one message left the building", len(sent) == 1))

                if sent:
                    raw = sent[0].as_string()
                    results.append(check("payload is METHOD:REQUEST", "METHOD:REQUEST" in raw))
                    results.append(check("payload carries a real ATTENDEE line",
                                         "ATTENDEE" in raw and "mailto:" + CONTACT in raw))
                    results.append(check("  ...with the organiser set to the user",
                                         "ORGANIZER:mailto:mike@example.test" in raw))
                    results.append(check("  ...and the event's own UID, so an update supersedes it",
                                         EVENT["uid"] in raw))
                    results.append(check("  ...attached as a .ics for clients that ignore the part",
                                         "invite.ics" in raw))

                # 4. A used token cannot be replayed.
                r = run(mail.send_calendar_invite, to=CONTACT, uid=EVENT["uid"],
                        confirm_token=token)
                results.append(check("a spent token is refused",
                                     "error" in r and len(sent) == 1))

            # 4b. THE production failure of 2026-09-07 (seq 010). Everything above
            #     passed while the real thing was broken, because these tests drove
            #     consume() and the app drives confirm.execute() — a SECOND registry
            #     (_EXECUTORS) the tool had not been added to. Mike approved the
            #     invitation and got back "Nothing here knows how to carry out
            #     'send_calendar_invite'". Drive the path the app drives.
            sent.clear()
            r = run(mail.send_calendar_invite, to=CONTACT, uid=EVENT["uid"])
            tok2 = r.get("confirm_token") or r.get("token")
            results.append(check("the action is in the server's executor map",
                                 "send_calendar_invite" in confirm._EXECUTORS))
            if tok2:
                confirm.approve(tok2)
                ps = _patches()
                for pp in ps:
                    pp.start()
                try:
                    r = confirm.execute(tok2)
                finally:
                    for pp in ps:
                        pp.stop()
                results.append(check("approving in the app actually sends it",
                                     r.get("status") == "executed" and len(sent) == 1))
                results.append(check("  ...and does not report unexecutable",
                                     r.get("status") != "unexecutable"))

            # 5. Ambiguity is an error, never a guess.
            two = [dict(EVENT), dict(EVENT, uid="evt-2@ai-life-manager",
                                     start="2026-09-20T09:00:00")]
            r = run(mail.send_calendar_invite, to=CONTACT, title="Manny's concert",
                    date="2026-09-20", _events=two)
            results.append(check("two matching events refuse and list candidates",
                                 "error" in r and len(r.get("candidates", [])) == 2))

            # 6. No match refuses rather than inventing an event.
            r = run(mail.send_calendar_invite, to=CONTACT, title="Nothing like this",
                    date="2026-09-20")
            results.append(check("no matching event refuses", "error" in r))

    print(f"\n{sum(results)}/{len(results)} checks pass")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
