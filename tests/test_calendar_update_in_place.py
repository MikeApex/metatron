"""
tests/test_calendar_update_in_place.py — an edit changes what was asked, and nothing else.

Review 2026-11-05, finding 7 (and finding 50's note that the update tests mocked the fetch
with a flat dict, which is why this was invisible). update_calendar_event rebuilt a single
VEVENT from the formatted fields and PUT it over the whole CalDAV resource. A resource is a
master VEVENT, its VALARMs and EXDATEs, and one sibling VEVENT per rescheduled occurrence
(RECURRENCE-ID) — so:

  - "move the dentist to 3:30" deleted the reminder;
  - retitling a weekly class brought back the occurrence the user had cancelled (EXDATE)
    and dropped the one they had moved (the sibling).

These fixtures are real .ics text through the real GET → edit → PUT path, not a flat dict:
a plain single event (the common case, which must not regress) and a series whose
rescheduled sibling is written FIRST, so the master has to be found rather than assumed.
build_invite_ics must carry the EXDATEs too.

No network: requests.get/put are replaced, the conflict check is stubbed, the day-planner
notification is a no-op.

Usage:
    python3 tests/test_calendar_update_in_place.py
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.caldav as caldav        # noqa: E402

CFG = {"enabled": True, "calendar_url": "https://cal.example/events", "timezone": "Europe/London",
       "auth": {"username": "u", "password": "p"}}

CLEAN = {"overlaps": [], "exact_duplicate": None, "near_duplicate_candidates": [],
         "recurring_series_match": [], "location_transition_flags": [], "day_digest": [],
         "unverified_events": [], "attendees_resolved": []}

SINGLE = "\r\n".join([
    "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Google Inc//Google Calendar 70.9054//EN",
    "BEGIN:VEVENT",
    "DTSTART;TZID=Europe/London:20261118T140000",
    "DTEND;TZID=Europe/London:20261118T143000",
    "DTSTAMP:20261101T090000Z",
    "UID:dentist@google.com",
    "SUMMARY:Dentist",
    "DESCRIPTION:Bring the referral form",
    "LOCATION:Smile Clinic",
    "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:This is an event reminder",
    "TRIGGER:-P0DT0H30M0S", "END:VALARM",
    "END:VEVENT", "END:VCALENDAR", ""])

SERIES = "\r\n".join([
    "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Google Inc//Google Calendar 70.9054//EN",
    # The rescheduled occurrence first: the master must be found, not taken as VEVENT #1.
    "BEGIN:VEVENT",
    "DTSTART;TZID=Europe/London:20261125T190000",
    "DTEND;TZID=Europe/London:20261125T200000",
    "RECURRENCE-ID;TZID=Europe/London:20261125T180000",
    "UID:yoga@google.com",
    "SUMMARY:Yoga (moved to 7)",
    "END:VEVENT",
    "BEGIN:VEVENT",
    "DTSTART;TZID=Europe/London:20261104T180000",
    "DTEND;TZID=Europe/London:20261104T190000",
    "RRULE:FREQ=WEEKLY;BYDAY=WE",
    "EXDATE;TZID=Europe/London:20261118T180000",
    "DTSTAMP:20261101T090000Z",
    "UID:yoga@google.com",
    "SUMMARY:Yoga class",
    "DESCRIPTION:Bring a mat. The studio asks everyone to arrive ten minutes early so th",
    " at the session can start on time.",
    "LOCATION:Studio 2",
    "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:This is an event reminder",
    "TRIGGER:-P0DT0H30M0S", "END:VALARM",
    "END:VEVENT", "END:VCALENDAR", ""])


class _Resp:
    def __init__(self, status=200, text=""):
        self.status_code, self.text = status, text

    def raise_for_status(self):
        return None


class Base(unittest.TestCase):
    ics = SINGLE

    def setUp(self):
        self.puts: list[str] = []
        patches = [
            mock.patch.object(caldav, "_load_config", lambda persona=None: dict(CFG)),
            mock.patch.object(caldav.requests, "get", lambda url, **k: _Resp(200, self.ics)),
            mock.patch.object(caldav.requests, "put", self._put),
            mock.patch("tools.scheduling._compute_conflicts", return_value=dict(CLEAN)),
            mock.patch.object(caldav, "_note_plan_write", lambda: None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _put(self, url, data=b"", **kwargs):
        self.puts.append(data.decode("utf-8"))
        return _Resp(201)

    def body(self) -> str:
        self.assertEqual(len(self.puts), 1, "expected exactly one PUT")
        return self.puts[0]

    def master(self, body: str) -> str:
        """The VEVENT block of the PUT body that has no RECURRENCE-ID."""
        blocks = body.split("BEGIN:VEVENT")[1:]
        masters = [b for b in blocks if "RECURRENCE-ID" not in b.split("BEGIN:VALARM")[0]]
        self.assertEqual(len(masters), 1, body)
        return masters[0]


class SingleEvent(Base):
    ics = SINGLE

    def test_time_only_change_keeps_the_alarm(self):
        out = caldav.update_calendar_event(
            "dentist@google.com", start="2026-11-18T15:30:00", end="2026-11-18T16:00:00")
        self.assertTrue(out.get("success"), out)
        body = self.body()
        self.assertIn("BEGIN:VALARM", body)
        self.assertIn("TRIGGER:-P0DT0H30M0S", body)
        self.assertIn("DTSTART;TZID=Europe/London:20261118T153000", body)
        self.assertNotIn("20261118T140000", body)
        # Nothing the call did not name was rewritten.
        for kept in ("SUMMARY:Dentist", "DESCRIPTION:Bring the referral form",
                     "LOCATION:Smile Clinic"):
            self.assertEqual(body.count(kept), 1, kept)
        self.assertEqual(body.count("BEGIN:VEVENT"), 1)

    def test_retitle_keeps_the_alarm_and_the_time(self):
        caldav.update_calendar_event("dentist@google.com", title="Dentist — check-up")
        body = self.body()
        self.assertIn("SUMMARY:Dentist — check-up", body)
        self.assertNotIn("SUMMARY:Dentist\r\n", body)
        self.assertIn("DTSTART;TZID=Europe/London:20261118T140000", body)
        self.assertIn("BEGIN:VALARM", body)

    def test_a_new_alarm_replaces_the_old_one(self):
        caldav.update_calendar_event("dentist@google.com", alarm_minutes_before=10)
        body = self.body()
        self.assertEqual(body.count("BEGIN:VALARM"), 1, body)
        self.assertIn("TRIGGER:-PT10M", body)
        self.assertNotIn("TRIGGER:-P0DT0H30M0S", body)

    def test_properties_stay_ahead_of_the_alarm(self):
        caldav.update_calendar_event("dentist@google.com", title="Dentist", location="Room 4")
        master = self.master(self.body())
        alarm_at = master.index("BEGIN:VALARM")
        for prop in ("SUMMARY:", "LOCATION:Room 4", "DTSTAMP:", "X-CONFLICT-CHECK-STATUS:"):
            self.assertLess(master.index(prop), alarm_at, prop)


class Series(Base):
    ics = SERIES

    def test_the_master_is_read_not_the_first_vevent(self):
        ev = caldav._get_event_by_uid("yoga@google.com")
        self.assertEqual(ev["title"], "Yoga class")
        self.assertEqual(ev["recurrence"], "FREQ=WEEKLY;BYDAY=WE")

    def test_retitle_keeps_exdate_sibling_and_alarm(self):
        out = caldav.update_calendar_event("yoga@google.com", title="Yoga (beginners)")
        self.assertTrue(out.get("success"), out)
        body = self.body()
        # The cancelled occurrence stays cancelled.
        self.assertIn("EXDATE;TZID=Europe/London:20261118T180000", body)
        # The moved occurrence is still there, untouched — its own title included.
        self.assertIn("RECURRENCE-ID;TZID=Europe/London:20261125T180000", body)
        self.assertIn("SUMMARY:Yoga (moved to 7)", body)
        self.assertEqual(body.count("BEGIN:VEVENT"), 2)
        # The reminder survives.
        self.assertIn("TRIGGER:-P0DT0H30M0S", body)
        master = self.master(body)
        self.assertIn("SUMMARY:Yoga (beginners)", master)
        self.assertNotIn("SUMMARY:Yoga class", master)
        self.assertIn("RRULE:FREQ=WEEKLY;BYDAY=WE", master)
        self.assertIn("DTSTART;TZID=Europe/London:20261104T180000", master)
        # A folded line it did not touch is kept exactly as fetched.
        self.assertIn("so th\r\n at the session", master)

    def test_the_invitation_carries_the_exdate(self):
        ev = caldav.find_event_for_invite(uid="yoga@google.com")
        ics = caldav.build_invite_ics(ev, organizer_email="me@example.com",
                                      attendee_email="friend@example.com")
        self.assertIn("RRULE:FREQ=WEEKLY;BYDAY=WE", ics)
        self.assertIn("EXDATE;TZID=Europe/London:20261118T180000", ics)

    def test_an_invitation_found_by_title_carries_the_exdate(self):
        listed = {"uid": "yoga@google.com", "title": "Yoga class",
                  "start": "2026-11-04T18:00:00", "end": "2026-11-04T19:00:00",
                  "recurrence": "FREQ=WEEKLY;BYDAY=WE", "description": "", "location": ""}
        with mock.patch.object(caldav, "_query_events", lambda *a, **k: {"events": [listed]}):
            ev = caldav.find_event_for_invite(title="Yoga", date="2026-11-04")
        ics = caldav.build_invite_ics(ev, organizer_email="me@example.com",
                                      attendee_email="friend@example.com")
        self.assertIn("EXDATE;TZID=Europe/London:20261118T180000", ics)


if __name__ == "__main__":
    unittest.main(verbosity=2)
