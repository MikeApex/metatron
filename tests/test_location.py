"""
tests/test_location.py — [DB-0815-12] a coordinate becomes a place name and stops there.

Location is extra-sensitive, above ordinary sensitive (Mike, 2026-08-28): raw GPS never
enters a model prompt, cloud or local, and no coordinate history is kept. What is asserted
here is that ruling, not the plumbing:

  * a coordinate maps to the zone the user named, and to "away" when it matches nothing —
    an unknown place is a fact about the world, never an error
  * the smallest matching zone wins, so "the office" beats "central London" regardless of
    the order they were written in
  * the boundary is inclusive, because radius_m is the user's declared extent of a place
  * only ZONE CHANGES are stored: pinging from the same place a hundred times appends once,
    which is the difference between a transitions log and a trail with the numbers removed
  * the transitions file is 0600, and contains no coordinate in any form
  * the context line is "home since 14:02" — the arrival time, not the last ping — and
    carries its age when the arrival was on an earlier day, per the [DB-0822-06] pattern
  * NOTHING anywhere in this module's output contains a latitude or a longitude

Every persona directory here is a temp directory. Nothing reads or writes real data, and
nothing reaches a model, the network or the real persona tree.

Run:  python3 -m pytest tests/test_location.py -x -q
      python3 tests/test_location.py            # standalone, no pytest needed
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("METATRON_AUTH_PASSWORD", "test-password-not-the-real-one")
os.environ.setdefault("METATRON_PERSONA", "test_location")

from tools import location  # noqa: E402

# Somewhere in central London, and a point ~1.1 km north of it.
HOME_LAT, HOME_LON = 51.50735, -0.12776
FAR_LAT, FAR_LON = 51.51735, -0.12776

_TMP: list[Path] = []


def _persona_dir(zones: list[dict] | None = None) -> Path:
    """A fresh temp persona tree, wired in as the data dir for the whole module."""
    root = Path(tempfile.mkdtemp(prefix="metatron-location-"))
    _TMP.append(root)
    location.persona_data_dir = lambda persona=None, _r=root: _r          # type: ignore[assignment]
    if zones is not None:
        import yaml
        (root / "zones.yaml").write_text(yaml.safe_dump({"zones": zones}))
    return root


def _clean() -> None:
    for path in _TMP:
        shutil.rmtree(path, ignore_errors=True)
    _TMP.clear()


HOME = {"name": "home", "lat": HOME_LAT, "lon": HOME_LON, "radius_m": 150}


# --- the map from a coordinate to a name -----------------------------------

def test_a_coordinate_inside_a_zone_is_that_zone():
    _persona_dir([HOME])
    assert location.zone_for(HOME_LAT, HOME_LON) == "home"


def test_an_unknown_coordinate_is_away_not_an_error():
    _persona_dir([HOME])
    assert location.zone_for(FAR_LAT, FAR_LON) == location.AWAY == "away"


def test_a_persona_with_no_zones_file_resolves_everything_to_away():
    """Not an error state: a user who has not named anywhere has not named anywhere."""
    _persona_dir()                                  # no zones.yaml at all
    assert location.load_zones() == []
    assert location.zone_for(HOME_LAT, HOME_LON) == "away"


def test_a_malformed_zones_file_degrades_to_away_rather_than_raising():
    root = _persona_dir()
    (root / "zones.yaml").write_text("zones: [this is not: valid: yaml: at all")
    assert location.load_zones() == []
    assert location.zone_for(HOME_LAT, HOME_LON) == "away"


def test_one_bad_entry_does_not_discard_the_rest_of_the_file():
    _persona_dir([
        {"name": "", "lat": HOME_LAT, "lon": HOME_LON, "radius_m": 150},   # no name
        {"name": "nowhere", "lat": HOME_LAT, "radius_m": 150},             # no lon
        {"name": "zero", "lat": HOME_LAT, "lon": HOME_LON, "radius_m": 0}, # no extent
        HOME,
    ])
    assert [z["name"] for z in location.load_zones()] == ["home"]
    assert location.zone_for(HOME_LAT, HOME_LON) == "home"


# --- the boundary ----------------------------------------------------------

def test_a_point_exactly_on_the_radius_is_inside():
    """radius_m is the user's declared extent of a place; its edge belongs to it."""
    _persona_dir([HOME])
    # 150 m due north of home, to within a metre. One degree of latitude is ~111.32 km.
    on_edge = HOME_LAT + 150.0 / 111_320.0
    d = location._haversine_m(on_edge, HOME_LON, HOME_LAT, HOME_LON)
    assert 149 <= d <= 151, f"the fixture is not on the boundary ({d:.1f} m)"
    assert location.zone_for(on_edge, HOME_LON) == "home"


def test_a_point_just_outside_the_radius_is_away():
    _persona_dir([HOME])
    outside = HOME_LAT + 170.0 / 111_320.0
    assert location.zone_for(outside, HOME_LON) == "away"


# --- overlapping zones -----------------------------------------------------

def test_the_smallest_matching_zone_wins_whatever_the_file_order():
    """"the office" inside "central London" must resolve to the office, both ways round."""
    small = {"name": "the office", "lat": HOME_LAT, "lon": HOME_LON, "radius_m": 200}
    large = {"name": "central London", "lat": HOME_LAT, "lon": HOME_LON, "radius_m": 5000}
    for order in ([small, large], [large, small]):
        _persona_dir(order)
        assert location.zone_for(HOME_LAT, HOME_LON) == "the office"


def test_a_point_only_in_the_large_zone_gets_the_large_zone():
    _persona_dir([
        {"name": "the office", "lat": HOME_LAT, "lon": HOME_LON, "radius_m": 200},
        {"name": "central London", "lat": HOME_LAT, "lon": HOME_LON, "radius_m": 5000},
    ])
    assert location.zone_for(FAR_LAT, FAR_LON) == "central London"


# --- the transitions log ---------------------------------------------------

def test_a_first_reading_records_an_arrival():
    root = _persona_dir([HOME])
    out = location.record_position(HOME_LAT, HOME_LON, accuracy=12.0)
    assert out["zone"] == "home" and out["changed"] is True
    lines = (root / "location_transitions.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["zone"] == "home"


def test_pinging_from_the_same_place_appends_nothing():
    """The storage rule: transitions, not a trail. 50 pings from home is one arrival."""
    root = _persona_dir([HOME])
    for _ in range(50):
        location.record_position(HOME_LAT, HOME_LON)
    lines = (root / "location_transitions.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1


def test_a_repeat_keeps_the_original_arrival_time():
    """"since" must mean since arrival, not since the last ping."""
    _persona_dir([HOME])
    first = location.record_position(HOME_LAT, HOME_LON, ts="2026-08-28T14:02:00")
    again = location.record_position(HOME_LAT, HOME_LON, ts="2026-08-28T17:45:00")
    assert again["changed"] is False
    assert again["entered_at"] == first["entered_at"] == "2026-08-28T14:02:00"


def test_leaving_and_returning_records_both_crossings():
    root = _persona_dir([HOME])
    location.record_position(HOME_LAT, HOME_LON, ts="2026-08-28T09:00:00")
    location.record_position(FAR_LAT, FAR_LON, ts="2026-08-28T12:00:00")
    location.record_position(HOME_LAT, HOME_LON, ts="2026-08-28T14:02:00")
    zones = [json.loads(l)["zone"]
             for l in (root / "location_transitions.jsonl").read_text().splitlines()]
    assert zones == ["home", "away", "home"]


def test_the_log_is_append_only():
    """Earlier lines are never rewritten — the file only ever grows at the end."""
    root = _persona_dir([HOME])
    path = root / "location_transitions.jsonl"
    location.record_position(HOME_LAT, HOME_LON, ts="2026-08-28T09:00:00")
    before = path.read_text()
    location.record_position(FAR_LAT, FAR_LON, ts="2026-08-28T12:00:00")
    assert path.read_text().startswith(before)


def test_the_transitions_file_is_owner_only():
    """`age` encryption is Phase 6; until then 0600 is the protection (CLAUDE.md)."""
    root = _persona_dir([HOME])
    location.record_position(HOME_LAT, HOME_LON)
    mode = stat.S_IMODE((root / "location_transitions.jsonl").stat().st_mode)
    assert mode == 0o600, oct(mode)


def test_a_corrupt_line_does_not_break_the_reader():
    root = _persona_dir([HOME])
    path = root / "location_transitions.jsonl"
    path.write_text('{"zone": "home", "entered_at": "2026-08-28T09:00:00"}\n'
                    'not json at all\n'
                    '{"zone": "the gym", "entered_at": "2026-08-28T18:00:00"}\n')
    assert location.current_zone()["zone"] == "the gym"


# --- no coordinate survives the call ---------------------------------------

def _coordinate_traces(text: str) -> list[str]:
    """Any fragment of a coordinate that would identify the point, in any rendering."""
    candidates = [str(HOME_LAT), str(HOME_LON), str(FAR_LAT), str(FAR_LON),
                  "51.507", "-0.127", "51.517", "latitude", "longitude",
                  "lat", "lon", "accuracy"]
    return [c for c in candidates if c in text]


def test_nothing_written_to_disk_contains_a_coordinate():
    """The whole tier ruling, asserted against the bytes rather than against intent."""
    root = _persona_dir([HOME])
    location.record_position(HOME_LAT, HOME_LON, accuracy=8.0, ts="2026-08-28T14:02:00")
    location.record_position(FAR_LAT, FAR_LON, accuracy=8.0, ts="2026-08-28T15:00:00")
    written = (root / "location_transitions.jsonl").read_text()
    assert _coordinate_traces(written) == [], written


def test_the_value_returned_to_the_caller_carries_no_coordinate():
    _persona_dir([HOME])
    out = location.record_position(HOME_LAT, HOME_LON, accuracy=8.0)
    assert set(out) == {"zone", "entered_at", "changed"}
    assert _coordinate_traces(json.dumps(out)) == []


def test_nothing_reaching_a_prompt_contains_a_coordinate():
    """context_block is the only route from this module into a model prompt."""
    _persona_dir([HOME])
    location.record_position(HOME_LAT, HOME_LON, accuracy=8.0)
    for text in (location.context_line(), location.context_block()):
        assert _coordinate_traces(text) == [], text


def test_a_zone_named_after_a_coordinate_is_still_the_users_words():
    """A user may name a place anything; the system adds nothing numeric of its own."""
    _persona_dir([HOME])
    location.record_position(HOME_LAT, HOME_LON)
    assert "51.5" not in location.context_block()


# --- the context line ------------------------------------------------------

def test_the_line_is_the_place_and_the_arrival_time():
    _persona_dir([HOME])
    today = date.today().isoformat()
    location.record_position(HOME_LAT, HOME_LON, ts=f"{today}T14:02:00")
    assert location.context_line() == "home since 14:02"


def test_since_is_arrival_not_the_last_ping():
    _persona_dir([HOME])
    today = date.today().isoformat()
    location.record_position(HOME_LAT, HOME_LON, ts=f"{today}T14:02:00")
    location.record_position(HOME_LAT, HOME_LON, ts=f"{today}T20:31:00")
    assert location.context_line() == "home since 14:02"


def test_an_arrival_on_an_earlier_day_carries_its_age():
    """[DB-0822-06]: stored state read back as current is the failure. Annotate, never filter."""
    _persona_dir([HOME])
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    location.record_position(HOME_LAT, HOME_LON, ts=f"{yesterday}T14:02:00")
    assert location.context_line() == "home since 14:02, yesterday"

    _persona_dir([HOME])
    old = (date.today() - timedelta(days=3)).isoformat()
    location.record_position(HOME_LAT, HOME_LON, ts=f"{old}T08:15:00")
    assert location.context_line() == "home since 08:15, 3 days ago"


def test_an_old_arrival_is_annotated_and_never_dropped():
    _persona_dir([HOME])
    old = (date.today() - timedelta(days=40)).isoformat()
    location.record_position(HOME_LAT, HOME_LON, ts=f"{old}T08:15:00")
    line = location.context_line()
    assert line.startswith("home since 08:15") and "40 days ago" in line


def test_nothing_recorded_means_no_section_at_all():
    """A user who never enables the ping pays nothing for the feature."""
    _persona_dir([HOME])
    assert location.context_line() == ""
    assert location.context_block() == ""


def test_the_block_says_it_is_a_report_and_not_a_live_position():
    _persona_dir([HOME])
    today = date.today().isoformat()
    location.record_position(HOME_LAT, HOME_LON, ts=f"{today}T14:02:00")
    block = location.context_block()
    assert "home since 14:02" in block
    assert "not a live position" in block


def test_an_unusable_timestamp_still_names_the_place():
    root = _persona_dir([HOME])
    (root / "location_transitions.jsonl").write_text(
        '{"zone": "home", "entered_at": "whenever"}\n')
    assert location.context_line() == "home"


def test_away_is_reported_like_any_other_zone():
    """No special case: "away since 12:00" is a true and useful thing to say."""
    _persona_dir([HOME])
    today = date.today().isoformat()
    location.record_position(FAR_LAT, FAR_LON, ts=f"{today}T12:00:00")
    assert location.context_line() == "away since 12:00"


def test_relative_age_phrasing_matches_the_rest_of_the_context():
    assert location._relative_age(0) == "today"
    assert location._relative_age(1) == "yesterday"
    assert location._relative_age(5) == "5 days ago"


# --- the timestamp the client supplies -------------------------------------

def test_a_ping_with_no_timestamp_is_dated_now():
    _persona_dir([HOME])
    out = location.record_position(HOME_LAT, HOME_LON)
    assert (datetime.now() - datetime.fromisoformat(out["entered_at"])).total_seconds() < 30


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:
                failures.append(name)
                print(f"  FAIL  {name}: {exc}")
    _clean()
    print()
    print(f"{len(failures)} failed" if failures else "all passed")
    sys.exit(1 if failures else 0)
