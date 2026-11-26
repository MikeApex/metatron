"""
tests/test_caldav_event_titles.py — the calendar write door refuses placeholder uids and
titles carrying the internal word "user" ([DB-1029-10]).

No network: every refusal returns before config or HTTP is touched, which the test asserts by
making both explode if reached.

Usage: python3 tests/test_caldav_event_titles.py
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.caldav as caldav  # noqa: E402

BOOM = mock.patch.object(caldav, "_load_config", side_effect=AssertionError("reached config"))
BOOM2 = mock.patch.object(caldav, "_get_event_by_uid", side_effect=AssertionError("reached lookup"))


class Refusals(unittest.TestCase):
    def setUp(self):
        for m in (BOOM, BOOM2):
            m.start()
            self.addCleanup(m.stop)

    def test_internal_word_in_title_refused_on_write_and_update(self):
        for t in ["Sam and user at High Street", "User's dentist", "Lunch with the user",
                  "Dinner (user)", "Walk with Sam and USER", "Pick up the user’s coat",
                  "Lunch & user"]:
            r = caldav.write_calendar_event(t, "2026-12-01T10:00:00", "2026-12-01T11:00:00")
            self.assertIn("error", r, t)
            self.assertIn("user", r["error"])
            self.assertIn("error", caldav.update_calendar_event("real-uid-123", title=t), t)

    def test_placeholder_uid_refused_on_update_and_delete(self):
        for u in ["...", "", "  ", "<uid>", "uid", "…", "'...'", "None"]:
            r = caldav.update_calendar_event(u, location="x")
            self.assertIn("placeholder", r.get("error", ""), repr(u))
            r = caldav.delete_calendar_event(u)
            self.assertIn("read the", r.get("error", "").lower(), repr(u))

    def test_ordinary_titles_and_real_uids_pass_the_guards(self):
        for t in ["Sam and Dana at High Street", "Usernames workshop", "Superuser audit",
                  "Dentist", "end-user training", "Power-user workshop", "Multi-user rollout",
                  "USER acceptance testing", "Review user-facing copy", "User group meetup",
                  "Review for user research", "Sync with the user group", "Plan the user-centric roadmap"]:
            self.assertIsNone(caldav._internal_title_error(t), t)
        self.assertIsNone(caldav._internal_title_error(None))
        for u in ["20261201T100000-abc@example.com", "9f1c2e7a-3b4d-4e5f-8a9b-0c1d2e3f4a5b"]:
            self.assertIsNone(caldav._placeholder_uid_error(u), u)

    def test_refusal_message_reads_as_a_person_not_vocabulary(self):
        err = caldav._internal_title_error("Lunch with the user")["error"]
        self.assertIn("the person this calendar belongs to", err)

    def test_lone_cr_cannot_start_a_new_ical_line(self):
        self.assertNotIn("\r", caldav._escape_ical("a\rSTATUS:CANCELLED"))
        self.assertEqual(caldav._escape_ical("a\rb\r\nc"), "a\\nb\\nc")

    def test_update_without_a_title_is_not_blocked_by_the_title_rule(self):
        # title=None means "leave it alone"; only the lookup (stubbed to explode) is reached
        with self.assertRaises(AssertionError):
            caldav.update_calendar_event("real-uid-123", location="High Street")


CFG = {"enabled": True, "calendar_url": "https://cal.example/events", "timezone": "Europe/London",
       "auth": {"username": "u", "password": "p"}}
CLEAN = {"overlaps": [], "exact_duplicate": None, "near_duplicate_candidates": [],
         "recurring_series_match": [], "location_transition_flags": [], "day_digest": [],
         "unverified_events": [], "attendees_resolved": []}


class CreateLocation(unittest.TestCase):
    def _create(self, **kw):
        put = mock.Mock()
        put.return_value.raise_for_status = lambda: None
        with mock.patch.object(caldav, "_load_config", return_value=CFG), \
                mock.patch.object(caldav.requests, "put", put), \
                mock.patch.object(caldav, "_note_plan_write", lambda: None), \
                mock.patch("tools.scheduling._compute_conflicts", return_value=CLEAN) as cc:
            r = caldav.write_calendar_event("Lunch with Dana", "2026-12-01T12:00:00",
                                            "2026-12-01T13:00:00", **kw)
        return r, put.call_args.kwargs["data"].decode(), cc

    def test_location_written_escaped_and_passed_to_conflict_check(self):
        r, ics, cc = self._create(location="High Street, London; E14")
        self.assertNotIn("error", r)
        self.assertIn("LOCATION:High Street\\, London\\; E14", ics)
        self.assertEqual(cc.call_args.kwargs["location"], "High Street, London; E14")

    def test_no_location_writes_no_line_and_empty_check(self):
        r, ics, cc = self._create()
        self.assertNotIn("LOCATION", ics)
        self.assertEqual(cc.call_args.kwargs["location"], "")

    def test_schema_advertises_location(self):
        self.assertIn("location", caldav.WRITE_CALENDAR_EVENT_SCHEMA["input_schema"]["properties"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
