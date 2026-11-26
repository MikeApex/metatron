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
        for t in ["Benny and user at Canary Wharf", "User's dentist", "Lunch with the user",
                  "USER check-in", "Dinner (user)"]:
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
        for t in ["Benny and Dana at Canary Wharf", "Usernames workshop", "Superuser audit",
                  "Dentist"]:
            self.assertIsNone(caldav._internal_title_error(t), t)
        self.assertIsNone(caldav._internal_title_error(None))
        for u in ["20261201T100000-abc@example.com", "9f1c2e7a-3b4d-4e5f-8a9b-0c1d2e3f4a5b"]:
            self.assertIsNone(caldav._placeholder_uid_error(u), u)

    def test_update_without_a_title_is_not_blocked_by_the_title_rule(self):
        # title=None means "leave it alone"; only the lookup (stubbed to explode) is reached
        with self.assertRaises(AssertionError):
            caldav.update_calendar_event("real-uid-123", location="Canary Wharf")


if __name__ == "__main__":
    unittest.main(verbosity=2)
