"""
tests/test_caldav_multi_calendar.py — every calendar the account can see, one event per event.

Written with the change (2026-10-24). Before it the system read one calendar, so a calendar
shared with the account ("Shared with Mike") was invisible. The fixtures below are the
three overlap shapes measured live on the mike persona that day, not invented ones:

  - same UID on two calendars, differing only in an alarm   (an invite on primary + shared)
  - different UIDs, identical times                         ("John Ball school visit")
  - different UIDs, the copies disagree                      ("Jimmy Carr", 21:15 London on
    Metatron vs 22:00 Europe/Budapest on shared — which is 21:00 London)

plus the two parser bugs the merge depends on: a TZID was discarded, and an alarm's
DESCRIPTION overwrote the event's.

No network: requests is replaced by a fake CalDAV server keyed on URL.

Run: python3 tests/test_caldav_multi_calendar.py
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests                      # noqa: E402

import tools.caldav as caldav        # noqa: E402
import tools.scheduling as scheduling  # noqa: E402

HOST = "https://www.google.com"
OWN = f"{HOST}/calendar/dav/metatron%40group.calendar.google.com/events"
PRIMARY = "/calendar/dav/mike%40gmail.com/events/"
HOLIDAYS = "/calendar/dav/holidays%40virtual/events/"
SHARED = "/calendar/dav/shared%40group.calendar.google.com/events/"

CFG = {"enabled": True, "timezone": "Europe/London", "calendar_url": OWN,
       "auth": {"username": "mike@gmail.com", "password": "x"}}


def _vevent(uid, summary, start, end, tz="Europe/London", extra=(), lastmod="20261001T000000Z"):
    if tz == "DATE":
        times = [f"DTSTART;VALUE=DATE:{start}", f"DTEND;VALUE=DATE:{end}"]
    elif tz == "Z":
        times = [f"DTSTART:{start}Z", f"DTEND:{end}Z"]
    else:
        times = [f"DTSTART;TZID={tz}:{start}", f"DTEND;TZID={tz}:{end}"]
    return "\r\n".join(["BEGIN:VEVENT", f"UID:{uid}", *times, f"SUMMARY:{summary}",
                        f"LAST-MODIFIED:{lastmod}", *extra, "END:VEVENT"])


ALARM = ["BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:This is an event reminder",
         "TRIGGER:-P0DT0H30M0S", "END:VALARM"]

CALENDARS = {
    "metatron": [
        _vevent("jb-m@ai-life-manager", "John Ball school visit", "20261112T091500", "20261112T101500"),
        _vevent("jc-m@ai-life-manager", "Jimmy Carr Laughs Funny at the London Palladium",
                "20261113T211500", "20261113T230000",
                extra=["LOCATION:The London Palladium", "DESCRIPTION:Doors open 8:45pm"]),
        _vevent("dentist@ai-life-manager", "Dentist", "20261114T100000", "20261114T110000",
                extra=["DESCRIPTION:Bring the form", *ALARM]),
        _vevent("twin-1@ai-life-manager", "Standup", "20261115T090000", "20261115T091500"),
        _vevent("twin-2@ai-life-manager", "Standup", "20261115T090000", "20261115T091500"),
    ],
    "primary": [
        _vevent("invite-1@google.com", "Parents evening", "20261116T170000", "20261116T180000",
                tz="Z", extra=ALARM, lastmod="20261022T065826Z"),
    ],
    "holidays": [
        _vevent("hol-1@google.com", "Bank holiday", "20261112", "20261113", tz="DATE"),
    ],
    "shared": [
        _vevent("jb-s@google.com", "John Ball school visit", "20261112T091500", "20261112T101500"),
        _vevent("jc-s@google.com", "Jimmy Carr laughs funny at the London Palladium",
                "20261113T220000", "20261114T000000", tz="Europe/Budapest"),
        _vevent("invite-1@google.com", "Parents evening", "20261116T170000", "20261116T180000",
                tz="Z", lastmod="20261022T065822Z"),
        _vevent("swim@google.com", "Swim class", "20261112T103000", "20261112T113000",
                extra=["LOCATION:Aquatics Centre"]),
    ],
}

PATH_TO_CAL = {
    "/calendar/dav/metatron@group.calendar.google.com/events": "metatron",
    "/calendar/dav/mike@gmail.com/events": "primary",
    "/calendar/dav/holidays@virtual/events": "holidays",
    "/calendar/dav/shared@group.calendar.google.com/events": "shared",
}


def _multistatus(*responses):
    return ('<?xml version="1.0"?><D:multistatus xmlns:D="DAV:" '
            'xmlns:caldav="urn:ietf:params:xml:ns:caldav">' + "".join(responses) + "</D:multistatus>")


def _cal_listing():
    def entry(href, name, is_cal=True):
        rtype = "<D:collection/><caldav:calendar/>" if is_cal else "<D:collection/>"
        return (f"<D:response><D:href>{href}</D:href><D:propstat><D:prop>"
                f"<D:displayname>{name}</D:displayname><D:resourcetype>{rtype}</D:resourcetype>"
                f"</D:prop></D:propstat></D:response>")
    return _multistatus(
        entry("/calendar/dav/mike%40gmail.com/", "", is_cal=False),
        entry(PRIMARY, "mike@gmail.com"),
        entry(HOLIDAYS, "Holidays in United Kingdom"),
        entry("/calendar/dav/metatron%40group.calendar.google.com/events/", "Metatron"),
        entry(SHARED, "Shared with Mike"),
        entry("/calendar/dav/mike%40gmail.com/inbox/", "", is_cal=False),
    )


class _Resp:
    def __init__(self, status, text=""):
        self.status_code, self.text = status, text

    def raise_for_status(self):
        if self.status_code >= 400:
            err = requests.HTTPError(f"{self.status_code}")
            err.response = self
            raise err


class FakeServer:
    """Google's shape, as probed 2026-10-24: the principal is answered only at /calendar/dav/."""

    def __init__(self, failing=(), discovery_broken=False):
        self.failing, self.discovery_broken = set(failing), discovery_broken
        self.calls = []

    def request(self, method, url, data=None, headers=None, auth=None, timeout=None, **_):
        from urllib.parse import unquote, urlparse
        path = unquote(urlparse(url).path)
        self.calls.append((method, path))
        if method == "PROPFIND":
            if self.discovery_broken:
                return _Resp(500)
            if path == "/calendar/dav/":
                return _Resp(207, _multistatus(
                    "<D:response><D:href>/calendar/dav/</D:href><D:propstat><D:prop>"
                    "<D:current-user-principal><D:href>/calendar/dav/mike%40gmail.com/user</D:href>"
                    "</D:current-user-principal></D:prop></D:propstat></D:response>"))
            if path == "/calendar/dav/mike@gmail.com/user":
                return _Resp(207, _multistatus(
                    "<D:response><D:href>/calendar/dav/mike@gmail.com/user/</D:href><D:propstat><D:prop>"
                    "<caldav:calendar-home-set><D:href>/calendar/dav/mike%40gmail.com/</D:href>"
                    "</caldav:calendar-home-set></D:prop></D:propstat></D:response>"))
            if path == "/calendar/dav/mike@gmail.com/":
                return _Resp(207, _cal_listing())
            if path.startswith("/.well-known"):
                return _Resp(404)
            return _Resp(207, _multistatus())  # a collection, asked for a principal: nothing
        if method == "REPORT":
            cal = PATH_TO_CAL[path.rstrip("/")]
            if cal in self.failing:
                return _Resp(503)
            body = "".join(
                f"<D:response><D:href>{path}{i}.ics</D:href><D:propstat><D:prop>"
                f"<caldav:calendar-data>BEGIN:VCALENDAR\r\n{ev}\r\nEND:VCALENDAR</caldav:calendar-data>"
                f"</D:prop></D:propstat></D:response>"
                for i, ev in enumerate(CALENDARS[cal]))
            return _Resp(207, _multistatus(body))
        raise AssertionError(f"unexpected {method} {url}")

    def get(self, url, auth=None, timeout=None, **_):
        from urllib.parse import unquote, urlparse
        path = unquote(urlparse(url).path)
        self.calls.append(("GET", path))
        cal_path, _, name = path.rpartition("/")
        uid = name[:-4]
        cal = PATH_TO_CAL.get(cal_path.rstrip("/"))
        for ev in CALENDARS.get(cal, []):
            if f"UID:{uid}\r\n" in ev:
                return _Resp(200, f"BEGIN:VCALENDAR\r\n{ev}\r\nEND:VCALENDAR")
        return _Resp(404)


class Base(unittest.TestCase):
    cfg = CFG

    def server(self, **kw):
        caldav._discovery_cache.clear()
        srv = FakeServer(**kw)
        for p in (mock.patch.object(caldav, "_load_config", return_value=dict(self.cfg)),
                  mock.patch.object(caldav.requests, "request", srv.request),
                  mock.patch.object(caldav.requests, "get", srv.get)):
            p.start()
            self.addCleanup(p.stop)
        return srv

    def events(self, mode="all"):
        out = caldav._query_events("2026-11-10", "2026-11-20", calendars=mode)
        self.assertNotIn("error", out, out)
        return out

    @staticmethod
    def titled(events, word):
        return [e for e in events if word.lower() in e["title"].lower()]


class ParserFixes(Base):
    def test_own_mode_is_one_report_and_unchanged_shape(self):
        srv = self.server()
        out = self.events("own")
        self.assertEqual([c for c in srv.calls if c[0] != "GET"],
                         [("REPORT", "/calendar/dav/metatron@group.calendar.google.com/events")])
        jb = self.titled(out["events"], "john ball")[0]
        self.assertEqual(jb["start"], "2026-11-12T09:15:00")
        self.assertNotIn("calendars", jb)
        self.assertNotIn("read_only", jb)

    def test_alarm_no_longer_overwrites_description(self):
        self.server()
        dentist = self.titled(self.events("own")["events"], "dentist")[0]
        self.assertEqual(dentist["description"], "Bring the form")

    def test_foreign_tzid_converted_to_persona_zone(self):
        self.server()
        jc = [e for e in self.events()["events"] if "jimmy" in e["title"].lower()][0]
        self.assertIn({"value": "2026-11-13T21:00:00", "calendar": "Shared with Mike"},
                      jc["discrepancies"]["start"])

    def test_all_day_value_unchanged(self):
        self.assertEqual(caldav._parse_ical_dt("20261112", "", "Europe/London"), "2026-11-12T00:00:00")


class Merging(Base):
    def test_identical_copies_shown_once(self):
        self.server()
        jb = self.titled(self.events()["events"], "john ball")
        self.assertEqual(len(jb), 1)
        self.assertEqual(jb[0]["calendars"], ["Metatron", "Shared with Mike"])
        self.assertFalse(jb[0]["read_only"])
        self.assertEqual(jb[0]["uid"], "jb-m@ai-life-manager")

    def test_disagreeing_copies_metatron_wins_and_the_other_value_is_kept(self):
        self.server()
        jc = self.titled(self.events()["events"], "jimmy")
        self.assertEqual(len(jc), 1)
        jc = jc[0]
        self.assertEqual(jc["start"], "2026-11-13T21:15:00")
        self.assertEqual(jc["location"], "The London Palladium")
        self.assertEqual(jc["uid"], "jc-m@ai-life-manager")
        self.assertIn("start", jc["discrepancies"])
        self.assertIn("title", jc["discrepancies"])  # capitalisation differs; still one event

    def test_same_uid_on_two_read_only_calendars(self):
        self.server()
        pe = self.titled(self.events()["events"], "parents evening")
        self.assertEqual(len(pe), 1)
        pe = pe[0]
        self.assertTrue(pe["read_only"])
        self.assertEqual(pe["calendars"], ["mike@gmail.com", "Shared with Mike"])
        self.assertEqual(pe["start"], "2026-11-16T17:00:00")  # UTC → London (GMT in November)
        self.assertNotIn("reminder", pe["description"])
        self.assertNotIn("discrepancies", pe)

    def test_account_calendar_is_read_only_but_not_someone_elses(self):
        self.server()
        evs = self.events()["events"]
        pe = self.titled(evs, "parents evening")[0]
        self.assertTrue(pe["read_only"])
        self.assertFalse(pe["shared"])
        self.assertTrue(self.titled(evs, "swim")[0]["shared"])
        self.assertFalse(self.titled(evs, "john ball")[0]["shared"])

    def test_uid_is_stable_when_only_one_copy_is_readable(self):
        self.server()
        uid_all = self.titled(self.events()["events"], "parents evening")[0]["uid"]
        self.server(failing={"shared"})
        uid_partial = self.titled(self.events()["events"], "parents evening")[0]["uid"]
        self.assertEqual(uid_all, uid_partial)

    def test_never_merges_within_one_calendar(self):
        self.server()
        self.assertEqual(len(self.titled(self.events()["events"], "standup")), 2)

    def test_everything_seen_once(self):
        self.server()
        titles = sorted(e["title"].lower()[:10] for e in self.events()["events"])
        self.assertEqual(len(titles), 8, titles)


class Degradation(Base):
    def test_secondary_failure_reported_not_fatal(self):
        self.server(failing={"shared"})
        out = self.events()
        self.assertEqual(out["calendars_failed"], ["Shared with Mike"])
        self.assertEqual(self.titled(out["events"], "john ball")[0]["calendars"], ["Metatron"])

    def test_own_calendar_failure_is_an_error(self):
        self.server(failing={"metatron"})
        out = caldav._query_events("2026-11-10", "2026-11-20", calendars="all")
        self.assertIn("error", out)

    def test_discovery_failure_falls_back_visibly(self):
        self.server(discovery_broken=True)
        out = self.events()
        self.assertTrue(out["discovery"].startswith("discovery failed"))
        self.assertEqual(out["calendars_read"], ["Main calendar"])

    def test_discovery_failure_is_not_cached(self):
        broken = self.server(discovery_broken=True)
        self.events()
        broken.discovery_broken = False
        self.assertEqual(self.events()["discovery"], "ok")

    def test_discovery_switched_off_in_config(self):
        self.cfg = {**CFG, "discover_calendars": False,
                    "extra_calendars": ["shared@group.calendar.google.com"]}
        srv = self.server()
        out = self.events()
        self.assertFalse([c for c in srv.calls if c[0] == "PROPFIND"])
        self.assertEqual(out["discovery"], "off")
        self.assertEqual(len(out["calendars_read"]), 2)
        self.assertEqual(len(self.titled(out["events"], "john ball")), 1)


class EditsAndReads(Base):
    def test_editing_a_read_only_event_says_where_it_is(self):
        self.server()
        out = caldav.update_calendar_event("swim@google.com", title="Swim")
        self.assertIn("does not edit", out["error"])
        self.assertNotIn("Shared with Mike", out["error"])  # owner-set text stays wrapped
        self.assertIn("<untrusted_content", out["calendar"])
        self.assertIn("Shared with Mike", out["calendar"])

    def test_missing_everywhere_is_still_not_found(self):
        self.server()
        self.assertIn("No event found", caldav.delete_calendar_event("nope")["error"])

    def test_read_calendar_carries_sources_and_note(self):
        self.server(failing={"holidays"})
        with mock.patch("tools.obligations.calendar_ledger_notes", return_value=[]):
            out = caldav.read_calendar("2026-11-10", "2026-11-20")
        self.assertEqual(out["count"], 8 - 1)  # the holiday calendar was unreadable
        self.assertIn("Holidays in United Kingdom", out["calendar_sources"])
        self.assertIn("read_only", out["calendar_note"])


class ConflictCheck(Base):
    def conflicts(self, **kw):
        with mock.patch.object(scheduling, "search_contacts", return_value="[]"), \
             mock.patch.object(scheduling, "get_travel_time", side_effect=AssertionError("routed")):
            return scheduling._compute_conflicts(**kw)

    def test_writing_what_is_already_on_a_shared_calendar_is_allowed(self):
        self.server()
        out = self.conflicts(start="2026-11-12T10:30:00", end="2026-11-12T11:30:00", title="Swim class")
        self.assertIsNone(out["exact_duplicate"])
        self.assertEqual(out["existing_elsewhere"][0]["uid"], "swim@google.com")

    def test_duplicate_of_own_calendar_still_refused(self):
        self.server()
        out = self.conflicts(start="2026-11-12T09:15:00", end="2026-11-12T10:15:00",
                             title="John Ball school visit")
        self.assertEqual(out["exact_duplicate"]["uid"], "jb-m@ai-life-manager")

    def test_read_only_all_day_is_not_a_clash(self):
        self.server()
        out = self.conflicts(start="2026-11-12T14:00:00", end="2026-11-12T15:00:00", title="Bank run")
        self.assertFalse([o for o in out["overlaps"] if "holiday" in o["title"].lower()])
        self.assertFalse([c for c in out["near_duplicate_candidates"] if "holiday" in c["title"].lower()])

    def test_utc_stamped_invite_does_not_crash_the_check(self):
        self.server()
        out = self.conflicts(start="2026-11-16T17:30:00", end="2026-11-16T18:30:00", title="Call")
        self.assertEqual([o["title"] for o in out["overlaps"]], ["Parents evening"])

    def test_unchecked_calendar_is_named_in_the_conflict_result(self):
        self.server(failing={"shared"})
        out = self.conflicts(start="2026-11-12T14:00:00", end="2026-11-12T15:00:00", title="X")
        self.assertEqual(out["calendars_not_checked"], ["Shared with Mike"])

    def test_already_shared_note_does_not_claim_one_entry_in_the_users_app(self):
        self.server()
        out = self.conflicts(start="2026-11-12T10:30:00", end="2026-11-12T11:30:00", title="Swim class")
        self.assertIn("will show both", out["existing_elsewhere"][0]["note"])

    def test_read_only_neighbour_triggers_no_route_lookup(self):
        self.server()
        # Swim class (shared, Aquatics Centre) ends 11:30; a write at 11:40 elsewhere would
        # have been a tight transition. get_travel_time raises if it is called.
        out = self.conflicts(start="2026-11-12T11:40:00", end="2026-11-12T12:30:00",
                             title="Lunch", location="Café Rouge")
        self.assertEqual(out["location_transition_flags"], [])


def _series(uid, summary, start, end, rrule, tz="Europe/London", extra=()):
    return _vevent(uid, summary, start, end, tz=tz, extra=[f"RRULE:{rrule}", *extra])


# The real series of the week of 9 Nov 2026 (probed live 2026-10-24), plus the edge cases
# a series can carry. Google sends each as its master: DTSTART is the FIRST occurrence.
SERIES = {
    "metatron": [
        _series("karate@ai-life-manager", "Karate for Manny", "20260914T183000", "20260914T193000",
                "FREQ=WEEKLY"),
        _series("swim@ai-life-manager", "Manny's swim class", "20260918T100000", "20260918T110000",
                "FREQ=WEEKLY;BYDAY=FR"),
        _series("cc@ai-life-manager", "Credit card payment due", "20260815", "20260816",
                "FREQ=MONTHLY;BYMONTHDAY=15", tz="DATE"),
        _series("review@ai-life-manager", "Review Manny's school week", "20260816", "20260817",
                "FREQ=WEEKLY;BYDAY=SU", tz="DATE"),
        _series("budapest@ai-life-manager", "Call with Budapest", "20260917T200000", "20260917T203000",
                "FREQ=WEEKLY;BYDAY=TH", tz="Europe/Budapest"),
        _series("until-z@ai-life-manager", "Course", "20261101T080000", "20261101T090000",
                "FREQ=DAILY;UNTIL=20261111T000000Z"),
        _series("until-date@ai-life-manager", "Course B", "20261101T070000", "20261101T073000",
                "FREQ=DAILY;UNTIL=20261110"),
        _series("bogus@ai-life-manager", "Mystery", "20261101T080000", "20261101T090000", "FREQ=BOGUS"),
        _series("skipped@ai-life-manager", "Piano", "20260917T160000", "20260917T170000",
                "FREQ=WEEKLY;BYDAY=TH", extra=["EXDATE;TZID=Europe/London:20261112T160000"]),
        _series("moved@ai-life-manager", "Tutor", "20260914T170000", "20260914T180000", "FREQ=WEEKLY"),
        _vevent("moved@ai-life-manager", "Tutor", "20261110T170000", "20261110T180000",
                extra=["RECURRENCE-ID;TZID=Europe/London:20261109T170000"]),
    ],
    "primary": [],
    "holidays": [],
    "shared": [
        _series("gan@google.com", "Gan", "20250914T090000", "20250914T130000", "FREQ=WEEKLY;BYDAY=SU"),
        _series("karate@ai-life-manager", "Karate for Manny", "20260914T183000", "20260914T193000",
                "FREQ=WEEKLY"),
    ],
}


class RepeatingEvents(Base):
    def setUp(self):
        p = mock.patch.dict(CALENDARS, SERIES)
        p.start()
        self.addCleanup(p.stop)

    def occurs(self, title, start="2026-11-09", end="2026-11-15"):
        out = caldav._query_events(start, end, calendars="all")
        rows = [e for e in out["events"] if e["title"] == title and "occurs_in_range" in e
                or e["title"] == title and e.get("occurrences_unknown")]
        self.assertEqual(len(rows), 1, rows)
        return rows[0]

    def test_the_weeks_real_series_fall_on_their_real_dates(self):
        self.server()
        self.assertEqual(self.occurs("Karate for Manny")["occurs_in_range"], ["2026-11-09T18:30:00"])
        self.assertEqual(self.occurs("Manny's swim class")["occurs_in_range"], ["2026-11-13T10:00:00"])
        self.assertEqual(self.occurs("Gan")["occurs_in_range"], ["2026-11-15T09:00:00"])

    def test_series_keeps_one_row_and_its_series_uid(self):
        self.server()
        row = self.occurs("Gan")
        self.assertEqual(row["uid"], "gan@google.com")
        self.assertEqual(row["start"], "2025-09-14T09:00:00")  # the master, as before

    def test_all_day_series_get_dates_not_a_silent_fallback(self):
        self.server()
        self.assertEqual(self.occurs("Credit card payment due")["occurs_in_range"], ["2026-11-15T00:00:00"])
        self.assertEqual(self.occurs("Review Manny's school week")["occurs_in_range"], ["2026-11-15T00:00:00"])

    def test_foreign_zone_series_keeps_its_wall_clock_across_dst(self):
        self.server()
        # 20:00 Budapest: 19:00 London in September (CEST/BST) and still 19:00 in November (CET/GMT).
        self.assertEqual(self.occurs("Call with Budapest")["occurs_in_range"], ["2026-11-12T19:00:00"])

    def test_until_in_utc_and_as_a_date(self):
        self.server()
        self.assertEqual(self.occurs("Course")["occurs_in_range"],
                         ["2026-11-09T08:00:00", "2026-11-10T08:00:00"])
        self.assertEqual(self.occurs("Course B")["occurs_in_range"],
                         ["2026-11-09T07:00:00", "2026-11-10T07:00:00"])

    def test_skipped_date_is_left_out(self):
        self.server()
        self.assertEqual(self.occurs("Piano")["occurs_in_range"], [])

    def test_moved_occurrence_shows_once_at_its_new_time(self):
        self.server()
        out = caldav._query_events("2026-11-09", "2026-11-15", calendars="all")
        tutor = [e for e in out["events"] if e["title"] == "Tutor"]
        master = [e for e in tutor if "occurs_in_range" in e][0]
        self.assertNotIn("2026-11-09T17:00:00", master["occurs_in_range"])
        self.assertIn("2026-11-10T17:00:00", [e["start"] for e in tutor])

    def test_date_only_exclusion_on_a_timed_series(self):
        self.server()
        CALENDARS["metatron"] = [_series("x1@x", "Choir", "20260917T160000", "20260917T170000",
                                         "FREQ=WEEKLY;BYDAY=TH", extra=["EXDATE;VALUE=DATE:20261112"])]
        self.assertEqual(self.occurs("Choir")["occurs_in_range"], [])

    def test_unreadable_exclusion_or_move_marks_dates_unknown(self):
        self.server()
        CALENDARS["metatron"] = [
            _series("x2@x", "Chess", "20260917T160000", "20260917T170000", "FREQ=WEEKLY;BYDAY=TH",
                    extra=["EXDATE;TZID=Not/AZone:20261112T160000"]),
            _series("x3@x", "Drama", "20260914T170000", "20260914T180000", "FREQ=WEEKLY"),
            _vevent("x3@x", "Drama", "20261110T170000", "20261110T180000",
                    extra=["RECURRENCE-ID;TZID=Not/AZone:20261109T170000"]),
        ]
        self.assertTrue(self.occurs("Chess")["occurrences_unknown"])
        self.assertTrue(self.occurs("Drama")["occurrences_unknown"])

    def test_unreadable_rule_is_marked_not_guessed(self):
        self.server()
        row = self.occurs("Mystery")
        self.assertTrue(row["occurrences_unknown"])
        self.assertNotIn("occurs_in_range", row)

    def test_same_series_on_two_calendars_is_one_row(self):
        self.server()
        row = self.occurs("Karate for Manny")
        self.assertEqual(row["calendars"], ["Metatron", "Shared with Mike"])

    def test_long_range_is_capped_and_says_so(self):
        self.server()
        CALENDARS["metatron"] = [_series("daily@x", "Vitamins", "20260101T080000", "20260101T080500",
                                         "FREQ=DAILY")]
        row = self.occurs("Vitamins", "2026-11-01", "2027-03-01")
        self.assertEqual(len(row["occurs_in_range"]), caldav._OCCURRENCE_CAP)
        self.assertTrue(row["occurs_in_range_truncated"])

    def test_own_mode_is_untouched(self):
        self.server()
        out = caldav._query_events("2026-11-09", "2026-11-15")
        self.assertFalse([e for e in out["events"] if "occurs_in_range" in e or "occurrences_unknown" in e])

    def conflicts(self, **kw):
        with mock.patch.object(scheduling, "search_contacts", return_value="[]"), \
             mock.patch.object(scheduling, "get_travel_time", return_value={"journeys": []}):
            return scheduling._compute_conflicts(**kw)

    def test_conflict_check_sees_the_occurrence_on_its_day(self):
        self.server()
        out = self.conflicts(start="2026-11-09T18:45:00", end="2026-11-09T19:15:00", title="Call")
        karate = [o for o in out["overlaps"] if o["title"] == "Karate for Manny"]
        self.assertEqual(len(karate), 1)
        self.assertEqual(karate[0]["occurrence_start"], "2026-11-09T18:30:00")
        self.assertIn("Karate for Manny", [d["title"] for d in out["day_digest"]])

    def test_duplicate_of_a_series_occurrence_still_refused(self):
        self.server()
        out = self.conflicts(start="2026-11-09T18:30:00", end="2026-11-09T19:30:00",
                             title="Karate for Manny")
        self.assertEqual(out["exact_duplicate"]["uid"], "karate@ai-life-manager")
        self.assertEqual(len(out["recurring_series_match"]), 1)

    def test_occurrence_enters_the_travel_check(self):
        self.server()
        CALENDARS["metatron"] = [_series("gym@x", "Gym", "20260914T170000", "20260914T180000",
                                         "FREQ=WEEKLY", extra=["LOCATION:Gym"])]
        out = self.conflicts(start="2026-11-09T18:10:00", end="2026-11-09T19:00:00",
                             title="Dinner", location="Restaurant")
        self.assertEqual(out["location_transition_flags"][0]["adjacent_title"], "Gym")


if __name__ == "__main__":
    unittest.main(verbosity=2)
