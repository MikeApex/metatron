"""
tests/test_places_open_at.py — a venue suggested for a later time is checked against its
opening hours for that time, [DB-0902-03].

Live 2026-09-08 Metatron sent Mike to Arôme Bakery on a Tuesday afternoon, when it is closed;
on 2026-08-28 it suggested a shop errand at 9:30 PM. `open_now` only answers for the moment of
the search. `find_places(..., at=…)` now asks for the opening periods and reports
`open_at_time` for the time the user would arrive.

No network: requests.post is stubbed.

    python3 tests/test_places_open_at.py
"""

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests  # noqa: E402

from tools import places  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, condition, detail))


def _p(day, h, m=0):
    return {"day": day, "hour": h, "minute": m}


# Google numbers days 0 = Sunday. A bakery open Wed–Mon 08:00–16:00, CLOSED on Tuesday (2).
BAKERY = {"regularOpeningHours": {"periods": [
    {"open": _p(d, 8), "close": _p(d, 16)} for d in (0, 1, 3, 4, 5, 6)]}}
# A late shop: 09:00 to 01:00 the next day, every day.
LATE = {"regularOpeningHours": {"periods": [
    {"open": _p(d, 9), "close": _p((d + 1) % 7, 1)} for d in range(7)]}}
ALWAYS = {"regularOpeningHours": {"periods": [{"open": _p(0, 0)}]}}
TODAY = date(2026, 9, 1)

tue_afternoon = datetime(2026, 9, 8, 15, 0)        # a Tuesday
wed_afternoon = datetime(2026, 9, 9, 15, 0)
check("the 09-08 case: closed on a Tuesday afternoon",
      places._open_at(BAKERY, tue_afternoon, TODAY) is False)
check("open on Wednesday afternoon", places._open_at(BAKERY, wed_afternoon, TODAY) is True)
check("closed after its closing time", places._open_at(BAKERY, datetime(2026, 9, 9, 16, 0), TODAY) is False)
check("open at 00:30 when it closes at 01:00 the next day",
      places._open_at(LATE, datetime(2026, 9, 9, 0, 30), TODAY) is True)
check("Saturday-into-Sunday close wraps the week",
      places._open_at(LATE, datetime(2026, 9, 6, 0, 30), TODAY) is True)   # a Sunday 00:30
check("closed at 02:00", places._open_at(LATE, datetime(2026, 9, 9, 2, 0), TODAY) is False)
check("a period with no close is open around the clock",
      places._open_at(ALWAYS, datetime(2026, 9, 9, 3, 0), TODAY) is True)
check("permanently closed is closed whatever the hours say",
      places._open_at({**BAKERY, "businessStatus": "CLOSED_PERMANENTLY"}, wed_afternoon, TODAY) is False)
check("no hours on record is unknown, not open",
      places._open_at({}, wed_afternoon, TODAY) is None)
check("an empty current-week record falls back to the regular hours",
      places._open_at({"currentOpeningHours": {"periods": []},
                       "regularOpeningHours": BAKERY["regularOpeningHours"]},
                      datetime(2026, 9, 3, 15), TODAY) is True)


# --- through find_places, with the request stubbed ---
_sent: dict = {}


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._p


def _post(url, headers=None, json=None, timeout=None):
    _sent["mask"] = headers["X-Goog-FieldMask"]
    return _Resp({"places": [{"displayName": {"text": "Arôme Bakery"},
                              "formattedAddress": "9 Example Street", **BAKERY}]})


_orig_post, _orig_key = requests.post, places._places_key
requests.post = _post
places._places_key = lambda: "test-key"
try:
    out = places.find_places("bakery", "Marylebone", at="2026-09-08T15:00")
    check("find_places with `at` reports open_at_time false for the closed bakery",
          out["places"][0].get("open_at_time") is False, repr(out))
    check("and asks for the opening periods", "regularOpeningHours.periods" in _sent["mask"], _sent["mask"])
    out = places.find_places("bakery", "Marylebone")
    check("without `at` the mask is unchanged — no higher-tier fields",
          "Periods" not in _sent["mask"] and "periods" not in _sent["mask"]
          and "open_at_time" not in out["places"][0], _sent["mask"])
    out = places.find_places("bakery", "Marylebone", at="tomorrow afternoon")
    check("a malformed `at` is an error, not a guess", "error" in out, repr(out))
finally:
    requests.post, places._places_key = _orig_post, _orig_key


if __name__ == "__main__":
    failed = [r for r in _results if not r[1]]
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if not ok and detail else ""))
    print(f"\n{len(_results) - len(failed)}/{len(_results)} passed")
    sys.exit(1 if failed else 0)
