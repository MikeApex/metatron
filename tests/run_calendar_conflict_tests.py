#!/usr/bin/env python3
"""
Calendar conflict-detection tests — tools/scheduling.py + tools/caldav.py.

WHY THIS EXISTS
---------------
Filed after a real incident: a meeting with Jonas was scheduled three times in
duplicate, because write_calendar_event had no duplicate check at all and
Logistics relied on independently noticing conflicts (CONFLICT_POSSIBLE) rather
than a deterministic check. The fix moved that check into code, running
automatically on every write/update rather than depending on the agent
remembering to call it. The build brief that produced this suite was explicit
that this needed to surface issues through testing, not through use — a
"quick regression pass" was rejected in favor of this file.

WHAT IT DOES NOT DO
-------------------
No live CalDAV server. All tests mock tools.scheduling._query_events (the
CalDAV REPORT layer) and, for the caldav.py write/update/delete tests,
tools.caldav.requests and tools.scheduling._compute_conflicts. This is
deliberate: an automated test that writes to a real calendar either pollutes
it with test events or needs a disposable calendar nobody has set up, and
either way tests logic bugs slower than mocked fixtures do.

USAGE
    source .venv/bin/activate
    python tests/run_calendar_conflict_tests.py
"""

import json
import sys
import unittest
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, ".")

from tools import scheduling  # noqa: E402


def _event(uid, title, start, end, location="", recurrence="", attendees=None, status=""):
    return {
        "uid": uid, "title": title, "start": start, "end": end,
        "description": "", "location": location, "status": status,
        "recurrence": recurrence, "attendees": attendees or [],
        "conflict_check_status": status,
    }


class ConflictDetectionTests(unittest.TestCase):
    """Cases 1-3, 5, 8, 11-12: check_calendar_conflicts / _compute_conflicts logic."""

    def _check(self, events, **kwargs):
        with patch.object(scheduling, "_query_events", return_value={"events": events}), \
             patch.object(scheduling, "search_contacts", return_value="[]"):
            return scheduling._compute_conflicts(**kwargs)

    def test_01_exact_duplicate_detected(self):
        events = [_event("u1", "Meeting with Jonas", "2026-08-10T14:00:00", "2026-08-10T14:30:00")]
        result = self._check(events, start="2026-08-10T14:00:00", end="2026-08-10T14:30:00", title="Meeting with Jonas")
        self.assertIsNotNone(result["exact_duplicate"])
        self.assertEqual(result["exact_duplicate"]["uid"], "u1")

    def test_02_near_duplicate_reworded_title_close_time(self):
        events = [_event("u1", "Jonas 1:1", "2026-08-10T14:00:00", "2026-08-10T14:30:00")]
        result = self._check(events, start="2026-08-10T14:15:00", end="2026-08-10T14:45:00", title="catch up with Jonas")
        self.assertIsNone(result["exact_duplicate"], "reworded title + shifted time must not be an exact duplicate")
        self.assertEqual(len(result["near_duplicate_candidates"]), 1)
        self.assertEqual(result["near_duplicate_candidates"][0]["uid"], "u1")

    def test_03_false_positive_guard_different_meetings_same_person(self):
        # Same person, same day, clearly different purposes/times far apart —
        # must not be flagged as a duplicate just because the name matches.
        events = [_event("u1", "Jonas — budget review", "2026-08-10T09:00:00", "2026-08-10T09:30:00", attendees=["Jonas"])]
        result = self._check(
            events, start="2026-08-10T16:00:00", end="2026-08-10T16:30:00",
            title="Jonas — quarterly planning", attendees=["Jonas"],
        )
        self.assertIsNone(result["exact_duplicate"])
        # Shared attendee alone, 6.5 hours apart, should not register as time-close.
        self.assertEqual(result["near_duplicate_candidates"], [])

    def test_05_recurring_series_fits_and_breaks_cadence(self):
        events = [
            _event("series1", "Team Sync", "2026-08-04T10:00:00", "2026-08-04T10:30:00", recurrence="FREQ=WEEKLY;BYDAY=TU"),
        ]
        # Same weekday (Tuesday), same time next week — fits cadence.
        fits = self._check(events, start="2026-08-11T10:00:00", end="2026-08-11T10:30:00", title="Team Sync")
        self.assertTrue(fits["recurring_series_match"][0]["fits_cadence"])
        # Different weekday/time — a supplemental extra, does not fit cadence.
        breaks = self._check(events, start="2026-08-12T15:00:00", end="2026-08-12T15:30:00", title="Team Sync")
        self.assertFalse(breaks["recurring_series_match"][0]["fits_cadence"])

    def test_05b_duplicate_of_recurring_occurrence_caught_as_overlap(self):
        events = [_event("series1", "Team Sync", "2026-08-04T10:00:00", "2026-08-04T10:30:00", recurrence="FREQ=WEEKLY;BYDAY=TU")]
        result = self._check(events, start="2026-08-04T10:00:00", end="2026-08-04T10:30:00", title="Team Sync")
        self.assertIsNotNone(result["exact_duplicate"], "creating a second event matching an existing RRULE occurrence must be caught")

    def test_08_exclude_uid_excludes_self(self):
        events = [_event("self-uid", "Dentist", "2026-08-10T09:00:00", "2026-08-10T10:00:00")]
        result = self._check(
            events, start="2026-08-10T09:00:00", end="2026-08-10T10:00:00",
            title="Dentist", exclude_uid="self-uid",
        )
        self.assertIsNone(result["exact_duplicate"])
        self.assertEqual(result["overlaps"], [])

    def test_10_location_transition_stub(self):
        events = [_event("u1", "Client visit", "2026-08-10T09:00:00", "2026-08-10T10:00:00", location="Downtown Office")]
        tight = self._check(events, start="2026-08-10T10:15:00", end="2026-08-10T11:00:00", title="Client B", location="Uptown Office")
        self.assertEqual(len(tight["location_transition_flags"]), 1)

        same_location = self._check(events, start="2026-08-10T10:15:00", end="2026-08-10T11:00:00", title="Client B", location="Downtown Office")
        self.assertEqual(same_location["location_transition_flags"], [])

        ample_gap = self._check(events, start="2026-08-10T12:00:00", end="2026-08-10T13:00:00", title="Client B", location="Uptown Office")
        self.assertEqual(ample_gap["location_transition_flags"], [])

    def test_11_back_to_back_events_not_flagged_as_overlap(self):
        # DTEND is exclusive per RFC 5545 — one event ending exactly when the
        # next starts is normal, not a conflict. This is the off-by-one that
        # "found through use" would look like.
        events = [_event("u1", "Meeting A", "2026-08-10T09:00:00", "2026-08-10T10:00:00")]
        result = self._check(events, start="2026-08-10T10:00:00", end="2026-08-10T11:00:00", title="Meeting B")
        self.assertEqual(result["overlaps"], [])

    def test_11b_genuine_overlap_is_flagged(self):
        events = [_event("u1", "Meeting A", "2026-08-10T09:00:00", "2026-08-10T10:00:00")]
        result = self._check(events, start="2026-08-10T09:30:00", end="2026-08-10T10:30:00", title="Meeting B")
        self.assertEqual(len(result["overlaps"]), 1)

    def test_12_all_day_duplicate_deadlines(self):
        events = [_event("u1", "Pay credit card bills", "2026-08-15T00:00:00", "2026-08-16T00:00:00")]
        result = self._check(events, start="2026-08-15T00:00:00", end="2026-08-16T00:00:00", title="Pay credit card bills")
        self.assertIsNotNone(result["exact_duplicate"])

    def test_check_error_on_query_failure(self):
        with patch.object(scheduling, "_query_events", return_value={"error": "CalDAV request failed: timeout"}):
            result = scheduling._compute_conflicts(start="2026-08-10T09:00:00", end="2026-08-10T10:00:00", title="X")
        self.assertIn("check_error", result)

    def test_unverified_events_surfaced(self):
        events = [_event("u1", "Old write", "2026-08-10T09:00:00", "2026-08-10T10:00:00", status="FAILED")]
        result = self._check(events, start="2026-08-11T09:00:00", end="2026-08-11T10:00:00", title="Something else")
        self.assertEqual(len(result["unverified_events"]), 1)
        self.assertEqual(result["unverified_events"][0]["uid"], "u1")

    def test_09_attendee_no_crm_match_does_not_error(self):
        with patch.object(scheduling, "_query_events", return_value={"events": []}), \
             patch.object(scheduling, "search_contacts", return_value="Error: no contact found"):
            result = scheduling._compute_conflicts(
                start="2026-08-10T09:00:00", end="2026-08-10T10:00:00", title="X", attendees=["Nobody Known"],
            )
        self.assertEqual(result["attendees_resolved"], [{"name": "Nobody Known", "contact_id": None}])

    def test_09b_attendee_crm_match_resolved(self):
        with patch.object(scheduling, "_query_events", return_value={"events": []}), \
             patch.object(scheduling, "search_contacts", return_value=json.dumps([{"id": "c-42", "name": "Jonas Whitfield"}])):
            result = scheduling._compute_conflicts(
                start="2026-08-10T09:00:00", end="2026-08-10T10:00:00", title="X", attendees=["Jonas"],
            )
        self.assertEqual(result["attendees_resolved"], [{"name": "Jonas", "contact_id": "c-42"}])


class WriteCalendarEventTests(unittest.TestCase):
    """Cases 4, 6, 13: write_calendar_event's tiered response and fail-open marker."""

    def setUp(self):
        self.cfg_patch = patch(
            "tools.caldav._load_config",
            return_value={"enabled": True, "calendar_url": "https://fake.example/cal", "auth": {}, "timezone": "UTC"},
        )
        self.cfg_patch.start()
        self.addCleanup(self.cfg_patch.stop)

    def test_04_exact_duplicate_refused_without_override(self):
        from tools import caldav
        dup = {"uid": "existing-1", "title": "Meeting with Jonas", "start": "2026-08-10T14:00:00", "end": "2026-08-10T14:30:00"}
        with patch("tools.scheduling._compute_conflicts", return_value={"overlaps": [dup], "exact_duplicate": dup}):
            result = caldav.write_calendar_event(
                title="Meeting with Jonas", start="2026-08-10T14:00:00", end="2026-08-10T14:30:00",
            )
        self.assertEqual(result.get("error"), "duplicate_event")

    def test_04b_exact_duplicate_created_with_override(self):
        from tools import caldav
        dup = {"uid": "existing-1", "title": "Meeting with Jonas", "start": "2026-08-10T14:00:00", "end": "2026-08-10T14:30:00"}
        with patch("tools.scheduling._compute_conflicts", return_value={"overlaps": [dup], "exact_duplicate": dup}), \
             patch("tools.caldav.requests.put") as mock_put:
            mock_put.return_value.raise_for_status.return_value = None
            result = caldav.write_calendar_event(
                title="Meeting with Jonas", start="2026-08-10T14:00:00", end="2026-08-10T14:30:00",
                override_duplicate=True,
            )
        self.assertTrue(result.get("success"))
        mock_put.assert_called_once()

    def test_04c_near_duplicate_does_not_block_creation(self):
        from tools import caldav
        near = {"uid": "u1", "title": "Jonas 1:1", "start": "2026-08-10T14:15:00", "end": "2026-08-10T14:45:00", "title_similarity": 0.7, "shared_attendees": []}
        with patch("tools.scheduling._compute_conflicts", return_value={
            "overlaps": [], "exact_duplicate": None, "near_duplicate_candidates": [near],
            "recurring_series_match": [], "location_transition_flags": [], "day_digest": [],
            "unverified_events": [], "attendees_resolved": [],
        }), patch("tools.caldav.requests.put") as mock_put:
            mock_put.return_value.raise_for_status.return_value = None
            result = caldav.write_calendar_event(
                title="catch up with Jonas", start="2026-08-10T14:15:00", end="2026-08-10T14:45:00",
            )
        self.assertTrue(result.get("success"))
        self.assertIn("conflict_check", result)
        self.assertEqual(result["conflict_check"]["status"], "ok")
        self.assertIn("near_duplicate_candidates", result["conflict_check"]["evidence"])

    def test_13_check_failure_allows_write_and_marks_event(self):
        from tools import caldav
        with patch("tools.scheduling._compute_conflicts", return_value={"check_error": "CalDAV request failed: timeout"}), \
             patch("tools.caldav.requests.put") as mock_put:
            mock_put.return_value.raise_for_status.return_value = None
            result = caldav.write_calendar_event(
                title="Meeting with Jonas", start="2026-08-10T14:00:00", end="2026-08-10T14:30:00",
            )
        self.assertTrue(result.get("success"))
        self.assertTrue(result["title"].startswith("[VERIFY]"))
        self.assertEqual(result["conflict_check"]["status"], "failed")
        # Confirm the marker actually made it into the PUT body, not just the
        # return value — that's what a later scan finds.
        put_body = mock_put.call_args.kwargs["data"].decode("utf-8")
        self.assertIn("X-CONFLICT-CHECK-STATUS:FAILED", put_body)
        self.assertIn("[VERIFY] Meeting with Jonas", put_body)

    def test_no_conflict_clean_write_has_no_conflict_check_field(self):
        from tools import caldav
        with patch("tools.scheduling._compute_conflicts", return_value={
            "overlaps": [], "exact_duplicate": None, "near_duplicate_candidates": [],
            "recurring_series_match": [], "location_transition_flags": [], "day_digest": [],
            "unverified_events": [], "attendees_resolved": [],
        }), patch("tools.caldav.requests.put") as mock_put:
            mock_put.return_value.raise_for_status.return_value = None
            result = caldav.write_calendar_event(title="Dentist", start="2026-08-10T09:00:00", end="2026-08-10T10:00:00")
        self.assertTrue(result.get("success"))
        self.assertNotIn("conflict_check", result)


class UpdateDeleteCalendarEventTests(unittest.TestCase):
    """Cases 6-8: update excludes own uid and re-checks new time; delete removes."""

    def setUp(self):
        self.cfg_patch = patch(
            "tools.caldav._load_config",
            return_value={"enabled": True, "calendar_url": "https://fake.example/cal", "auth": {}, "timezone": "UTC"},
        )
        self.cfg_patch.start()
        self.addCleanup(self.cfg_patch.stop)
        self.existing = {
            "uid": "u1", "title": "Meeting with Jonas", "start": "2026-08-10T14:00:00", "end": "2026-08-10T14:30:00",
            "description": "", "location": "", "status": "", "recurrence": "", "attendees": [],
            "conflict_check_status": "OK", "_event_url": "https://fake.example/cal/u1.ics",
        }

    def test_06_update_excludes_own_uid_from_conflict_check(self):
        from tools import caldav
        with patch("tools.caldav._get_event_by_uid", return_value=self.existing) as mock_get, \
             patch("tools.scheduling._compute_conflicts") as mock_check, \
             patch("tools.caldav.requests.put") as mock_put:
            mock_check.return_value = {
                "overlaps": [], "exact_duplicate": None, "near_duplicate_candidates": [],
                "recurring_series_match": [], "location_transition_flags": [], "day_digest": [],
                "unverified_events": [], "attendees_resolved": [],
            }
            mock_put.return_value.raise_for_status.return_value = None
            result = caldav.update_calendar_event(uid="u1", start="2026-08-10T15:30:00", end="2026-08-10T16:00:00")

        self.assertTrue(result.get("success"))
        self.assertEqual(mock_check.call_args.kwargs["exclude_uid"], "u1")

    def test_07_non_time_field_update_does_not_spuriously_conflict(self):
        from tools import caldav
        with patch("tools.caldav._get_event_by_uid", return_value=self.existing), \
             patch("tools.scheduling._compute_conflicts") as mock_check, \
             patch("tools.caldav.requests.put") as mock_put:
            mock_check.return_value = {
                "overlaps": [], "exact_duplicate": None, "near_duplicate_candidates": [],
                "recurring_series_match": [], "location_transition_flags": [], "day_digest": [],
                "unverified_events": [], "attendees_resolved": [],
            }
            mock_put.return_value.raise_for_status.return_value = None
            result = caldav.update_calendar_event(uid="u1", description="Bring the slide deck.")

        self.assertTrue(result.get("success"))
        # Unchanged fields carried over from the existing event (start/end are
        # positional args to _compute_conflicts — see update_calendar_event).
        self.assertEqual(mock_check.call_args.args[0], "2026-08-10T14:00:00")

    def test_update_new_time_conflicts_with_a_different_event(self):
        from tools import caldav
        other = {"uid": "u2", "title": "Blocked slot", "start": "2026-08-10T15:30:00", "end": "2026-08-10T16:00:00"}
        with patch("tools.caldav._get_event_by_uid", return_value=self.existing), \
             patch("tools.scheduling._compute_conflicts", return_value={"overlaps": [other], "exact_duplicate": other}):
            result = caldav.update_calendar_event(uid="u1", start="2026-08-10T15:30:00", end="2026-08-10T16:00:00", title="Blocked slot")
        self.assertEqual(result.get("error"), "duplicate_event")

    def test_08b_delete_removes_event(self):
        from tools import caldav
        with patch("tools.caldav._get_event_by_uid", return_value=self.existing), \
             patch("tools.caldav.requests.delete") as mock_delete:
            mock_delete.return_value.status_code = 200
            mock_delete.return_value.raise_for_status.return_value = None
            result = caldav.delete_calendar_event(uid="u1")
        self.assertTrue(result.get("success"))
        mock_delete.assert_called_once()

    def test_delete_not_found(self):
        from tools import caldav
        with patch("tools.caldav._get_event_by_uid", return_value={"error": "No event found with uid 'ghost'."}):
            result = caldav.delete_calendar_event(uid="ghost")
        self.assertIn("error", result)


def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (ConflictDetectionTests, WriteCalendarEventTests, UpdateDeleteCalendarEventTests):
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    print(f"\n{'=' * 60}\n{total - failed}/{total} PASS\n{'=' * 60}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
