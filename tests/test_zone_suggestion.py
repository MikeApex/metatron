"""
tests/test_zone_suggestion.py — [DB-0815-12] option b: the vendor never learns where
the user is, and only the user's tap can teach the system a new place.

The ruling under test (Mike, 2026-08-28, superseding the reverse-geocode note): when a
place is expected — named in an upcoming calendar event — code asks Google Places where
that PLACE is, by name only; the comparison against the user's ping happens locally; a
match while the ping is `away` raises the existing confirm card; approval appends to
zones.yaml through the one write path granted to that file. What is asserted here:

  * THE OUTBOUND PAYLOAD CONTAINS NO COORDINATE — body and headers are checked as
    bytes for every lat/lon-shaped key, not by intent
  * the per-name cache means a repeated name never hits the network twice
  * no API key -> error dict -> the whole suggestion path is dormant, and a ping
    still succeeds (fail-soft, item 5(d): the feature waits for the key)
  * a matching away ping raises ONE card whose stored args carry the PLACE's public
    coordinate and nothing resembling the ping's
  * a ping inside a defined zone, a far-away place, an already-defined name, and a
    second attempt inside the throttle window all raise nothing
  * append_zone without an approved token refuses and writes nothing; the approved
    round trip (request -> approve -> execute) appends the zone, 0600, and the zone
    then resolves; a name collision refuses rather than merges

Every persona directory here is a temp directory; nothing reaches the network or the
real persona tree.

Run:  python3 tests/test_zone_suggestion.py
"""

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("METATRON_AUTH_PASSWORD", "test-password-not-the-real-one")
os.environ.setdefault("METATRON_PERSONA", "test_zone_suggestion")

from tools import confirm, location, places  # noqa: E402

# The geocoded "place" and pings near/far from it. The ping shares NO figure with the
# place on either axis, so the "no ping coordinate in the stored card" check cannot be
# satisfied or defeated by coincidence.
PLACE_LAT, PLACE_LON = 51.50735, -0.12776
NEAR_LAT, NEAR_LON = 51.50745, -0.12790       # ~15 m away
FAR_LAT, FAR_LON = 51.51735, -0.12990         # ~1.1 km away

_TMP: list[Path] = []
_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool) -> None:
    _results.append((condition, label))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")


def _persona_dir(zones: list[dict] | None = None) -> Path:
    """A fresh temp persona tree wired into location AND confirm."""
    root = Path(tempfile.mkdtemp(prefix="metatron-zone-suggest-"))
    _TMP.append(root)
    location.persona_data_dir = lambda persona=None, _r=root: _r    # type: ignore[assignment]
    confirm.persona_data_dir = lambda persona=None, _r=root: _r     # type: ignore[assignment]
    if zones is not None:
        import yaml
        (root / "zones.yaml").write_text(yaml.safe_dump({"zones": zones}))
    return root


def _reset_throttle() -> None:
    location._last_suggest_attempt = 0.0


def _geo_ok(name: str) -> dict:
    return {"name": name.split(",", 1)[0], "address": name,
            "lat": PLACE_LAT, "lon": PLACE_LON}


# ---------------------------------------------------------------------------
# Part 1 — the geocode call itself
# ---------------------------------------------------------------------------

def part1() -> None:
    print("geocode_place_name — name out, nothing else")
    places._GEOCODE_CACHE.clear()
    captured: list[dict] = []

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.append({"url": url, "headers": headers, "body": json})
        resp = mock.Mock()
        resp.raise_for_status = lambda: None
        resp.json = lambda: {"places": [{
            "displayName": {"text": "Luigi's"},
            "formattedAddress": "12 High St",
            "location": {"latitude": PLACE_LAT, "longitude": PLACE_LON},
        }]}
        return resp

    with mock.patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "test-key"}), \
         mock.patch.object(places.requests, "post", side_effect=fake_post):
        result = places.geocode_place_name("Luigi's, 12 High St")
        check("a name resolves to the place's coordinate",
              result.get("lat") == PLACE_LAT and result.get("lon") == PLACE_LON)

        wire = json.dumps(captured[0]["body"]) + json.dumps(captured[0]["headers"])
        leaky = [k for k in ("lat", "lon", "latitude", "longitude", "locationBias",
                             "locationRestriction", "circle", "center")
                 if k.lower() in wire.lower()]
        check(f"the outbound payload carries NO coordinate key (found: {leaky or 'none'})",
              not leaky)
        check("the body is exactly the name query and a result cap",
              set(captured[0]["body"].keys()) == {"textQuery", "maxResultCount"})

        places.geocode_place_name("luigi's, 12 high st")
        check("a repeated name (any case) is served from the cache, no second call",
              len(captured) == 1)

    places._GEOCODE_CACHE.clear()
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("GOOGLE_PLACES_API_KEY", None)
        no_key = places.geocode_place_name("Luigi's")
        check("no API key -> an error dict, not an exception (dormant by design)",
              "error" in no_key)


# ---------------------------------------------------------------------------
# Part 2 — the suggestion flow inside a ping
# ---------------------------------------------------------------------------

def part2() -> None:
    print("\nzone suggestion — asks only when the ping sits at an expected place")

    # A matching away ping raises one card.
    _persona_dir(zones=[])
    _reset_throttle()
    with mock.patch.object(location, "_calendar_place_candidates",
                           return_value=["Luigi's, 12 High St"]), \
         mock.patch("tools.places.geocode_place_name",
                    side_effect=lambda n: _geo_ok(n)):
        result = location.record_position(NEAR_LAT, NEAR_LON)
        check("an away ping at an expected place returns a suggestion marker",
              result.get("suggestion", {}).get("zone_suggested") == "Luigi's")
        cards = confirm.pending()
        check("exactly one add_zone card is pending",
              len([c for c in cards if c["action"] == "add_zone"]) == 1)

        stored = json.dumps(confirm._load())
        check("the stored card carries the PLACE's coordinate",
              str(PLACE_LAT) in stored)
        check("the stored card carries nothing resembling the ping's coordinate",
              str(NEAR_LAT) not in stored and str(NEAR_LON) not in stored)

        # Throttled: an immediate second away ping does not attempt again.
        result2 = location.record_position(NEAR_LAT, NEAR_LON)
        check("a second ping inside the throttle window raises nothing",
              "suggestion" not in result2)

    # A far-away expected place raises nothing.
    _persona_dir(zones=[])
    _reset_throttle()
    with mock.patch.object(location, "_calendar_place_candidates",
                           return_value=["Luigi's, 12 High St"]), \
         mock.patch("tools.places.geocode_place_name",
                    side_effect=lambda n: _geo_ok(n)):
        result = location.record_position(FAR_LAT, FAR_LON)
        check("a ping 1.1 km from the expected place raises nothing",
              "suggestion" not in result and not confirm.pending())

    # A ping inside a defined zone never enters the suggestion path.
    _persona_dir(zones=[{"name": "home", "lat": NEAR_LAT, "lon": NEAR_LON,
                         "radius_m": 150}])
    _reset_throttle()
    with mock.patch.object(location, "_calendar_place_candidates",
                           side_effect=AssertionError("must not be called")) :
        result = location.record_position(NEAR_LAT, NEAR_LON)
        check("a ping inside a defined zone never looks for suggestions",
              result["zone"] == "home" and "suggestion" not in result)

    # An expected place whose name is already a zone is skipped.
    _persona_dir(zones=[{"name": "Luigi's", "lat": PLACE_LAT, "lon": PLACE_LON,
                         "radius_m": 30}])
    _reset_throttle()
    with mock.patch.object(location, "_calendar_place_candidates",
                           return_value=["Luigi's, 12 High St"]), \
         mock.patch("tools.places.geocode_place_name",
                    side_effect=lambda n: _geo_ok(n)):
        # Ping outside the tiny zone -> away, but the name is taken.
        result = location.record_position(FAR_LAT, FAR_LON)
        check("an already-defined zone name is never re-suggested",
              "suggestion" not in result and not confirm.pending())

    # Geocode failure (incl. missing key) degrades to nothing.
    _persona_dir(zones=[])
    _reset_throttle()
    with mock.patch.object(location, "_calendar_place_candidates",
                           return_value=["Luigi's"]), \
         mock.patch("tools.places.geocode_place_name",
                    return_value={"error": "no key"}):
        result = location.record_position(NEAR_LAT, NEAR_LON)
        check("a failed geocode degrades to a plain ping (dormant without the key)",
              result["zone"] == "away" and "suggestion" not in result)


# ---------------------------------------------------------------------------
# Part 3 — append_zone: the one write path, and it only opens on approval
# ---------------------------------------------------------------------------

def part3() -> None:
    print("\nappend_zone — nothing writes zones.yaml but the user's own tap")

    root = _persona_dir(zones=[])
    args = {"name": "Luigi's", "lat": PLACE_LAT, "lon": PLACE_LON, "radius_m": 150.0}

    refused = location.append_zone(**args, confirm_token="")
    check("no token -> refused", "error" in refused)
    refused = location.append_zone(**args, confirm_token="forged-token")
    check("an unknown token -> refused", "error" in refused)
    import yaml
    on_disk = yaml.safe_load((root / "zones.yaml").read_text()) or {}
    check("nothing was written by the refused calls", not on_disk.get("zones"))

    # The real round trip: card -> user approves -> server executes.
    card = confirm.request("add_zone", args, "Lock Luigi's in as a zone?")
    token = card["confirm_token"]
    check("the card is pending, nothing performed",
          card["status"] == "PENDING_CONFIRMATION")
    confirm.approve(token)
    outcome = confirm.execute(token)
    check("approval executes the append", outcome.get("status") == "executed")

    zones = location.load_zones()
    check("the zone is on file with the approved values",
          len(zones) == 1 and zones[0]["name"] == "Luigi's"
          and zones[0]["radius_m"] == 150.0)
    mode = stat.S_IMODE(os.stat(root / "zones.yaml").st_mode)
    check("zones.yaml is 0600", mode == 0o600)
    check("the place now resolves as its zone",
          location.zone_for(NEAR_LAT, NEAR_LON) == "Luigi's")

    # Single use: the same token cannot append twice.
    outcome2 = confirm.execute(token)
    check("the spent token cannot be replayed",
          outcome2.get("status") != "executed")

    # A name collision refuses rather than merges.
    card2 = confirm.request("add_zone", args, "again")
    confirm.approve(card2["confirm_token"])
    outcome3 = confirm.execute(card2["confirm_token"])
    check("an existing name is refused, file unchanged",
          (outcome3.get("result") or {}).get("status") == "exists"
          and len(location.load_zones()) == 1)


def main() -> int:
    try:
        part1()
        part2()
        part3()
    finally:
        import shutil
        for p in _TMP:
            shutil.rmtree(p, ignore_errors=True)
    print()
    failed = [label for ok, label in _results if not ok]
    if failed:
        print(f"{len(failed)} check(s) FAILED:")
        for label in failed:
            print(f"  - {label}")
        return 1
    print(f"All {len(_results)} zone-suggestion checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
