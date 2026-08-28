"""
tests/test_location_endpoint.py — POST /location, against the real FastAPI app.
[DB-0815-12]

The unit-level guarantees are in tests/test_location.py. What is exercised here is the
boundary the tier ruling actually rests on: the coordinate arrives over HTTP, and the
server's job is to turn it into a place name and let go of it. So the assertions are about
what leaves the endpoint and what the endpoint leaves behind —

  * the response names a zone and contains no coordinate in any form
  * the auth gate covers it, like every other endpoint
  * a coordinate matching nothing gets "away" and a 200, not an error
  * nothing is written to the conversation store and nothing is broadcast: a ping is not
    something the user said, and a stream of "you are at home" rows would turn a background
    signal into a conversation nobody started
  * a burst of pings from one place leaves one arrival on disk

The persona data tree is a temp directory. No model call, no network, no real history.

Run:  python3 -m pytest tests/test_location_endpoint.py -x -q
      python3 tests/test_location_endpoint.py     # standalone, no pytest needed
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("METATRON_AUTH_PASSWORD", "test-password-not-the-real-one")
os.environ.setdefault("METATRON_PERSONA", "danny_park")

from fastapi.testclient import TestClient        # noqa: E402

import core.server as server                     # noqa: E402
import tools.location as location                # noqa: E402

PERSONA = "danny_park"
HOME_LAT, HOME_LON = 51.50735, -0.12776
FAR_LAT, FAR_LON = 51.51735, -0.12776

_tmpdir = tempfile.mkdtemp(prefix="metatron-location-api-")
_root = Path(_tmpdir)

# Redirect the persona data tree before anything touches it, and keep the real
# conversation database out of reach.
server.DB_PATH = _root / "conversations" / "metatron.db"
# tools/location.py calls this with no argument — the persona is resolved from the
# thread-local scope the endpoint enters — so the replacement ignores its argument too.
location.persona_data_dir = lambda persona=None: _root / "personas" / PERSONA

_client = TestClient(server.app)
_token: str | None = None


def _auth() -> dict:
    global _token
    if _token is None:
        res = _client.post("/auth/login", json={"password": os.environ["METATRON_AUTH_PASSWORD"]})
        assert res.status_code == 200, res.text
        _token = res.json()["token"]
    return {"Authorization": f"Bearer {_token}"}


def _reset(zones: list[dict] | None = None) -> Path:
    """Empty the temp persona tree, optionally writing a zones file into it."""
    import yaml
    d = _root / "personas" / PERSONA
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    if zones is not None:
        (d / "zones.yaml").write_text(yaml.safe_dump({"zones": zones}))
    return d


def _post(lat: float, lon: float, **extra):
    body = {"lat": lat, "lon": lon, "persona": PERSONA, **extra}
    return _client.post("/location", json=body, headers=_auth())


HOME = {"name": "home", "lat": HOME_LAT, "lon": HOME_LON, "radius_m": 150}


def test_a_ping_comes_back_as_a_place_name():
    _reset([HOME])
    res = _post(HOME_LAT, HOME_LON, accuracy=12.0, ts="2026-08-28T14:02:00")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["zone"] == "home"
    assert body["changed"] is True
    assert body["entered_at"] == "2026-08-28T14:02:00"


def test_the_response_carries_no_coordinate():
    """The endpoint's whole contract: a coordinate goes in and a name comes out."""
    _reset([HOME])
    text = _post(HOME_LAT, HOME_LON, accuracy=12.0).text
    for fragment in ("51.507", "-0.127", "lat", "lon", "accuracy"):
        assert fragment not in text, f"{fragment!r} came back out of /location: {text}"


def test_an_unknown_coordinate_is_away_and_not_an_error():
    _reset([HOME])
    res = _post(FAR_LAT, FAR_LON)
    assert res.status_code == 200, res.text
    assert res.json()["zone"] == "away"


def test_a_persona_with_no_zones_file_still_gets_a_working_endpoint():
    _reset()                                       # no zones.yaml
    res = _post(HOME_LAT, HOME_LON)
    assert res.status_code == 200
    assert res.json()["zone"] == "away"


def test_the_endpoint_is_behind_the_auth_gate():
    _reset([HOME])
    res = _client.post("/location", json={"lat": HOME_LAT, "lon": HOME_LON, "persona": PERSONA})
    assert res.status_code == 401, res.text


def test_a_burst_of_pings_from_one_place_leaves_one_arrival():
    d = _reset([HOME])
    for _ in range(20):
        assert _post(HOME_LAT, HOME_LON).status_code == 200
    lines = (d / "location_transitions.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["zone"] == "home"


def test_leaving_and_returning_is_recorded_as_two_more_arrivals():
    d = _reset([HOME])
    _post(HOME_LAT, HOME_LON, ts="2026-08-28T09:00:00")
    _post(FAR_LAT, FAR_LON, ts="2026-08-28T12:00:00")
    _post(HOME_LAT, HOME_LON, ts="2026-08-28T14:02:00")
    zones = [json.loads(l)["zone"]
             for l in (d / "location_transitions.jsonl").read_text().splitlines()]
    assert zones == ["home", "away", "home"]


def test_nothing_is_written_to_disk_that_contains_a_coordinate():
    d = _reset([HOME])
    _post(HOME_LAT, HOME_LON, accuracy=9.0)
    _post(FAR_LAT, FAR_LON, accuracy=9.0)
    written = (d / "location_transitions.jsonl").read_text()
    for fragment in ("51.507", "-0.127", "51.517", "lat", "lon", "accuracy"):
        assert fragment not in written, f"{fragment!r} was persisted: {written}"


def test_a_ping_is_not_a_message_and_is_not_broadcast():
    """No conversation row, no WebSocket frame — a ping is a signal, not something said."""
    _reset([HOME])
    sent: list = []
    saved: list = []
    real_broadcast, real_save = server.manager.broadcast, server._save_exchange

    async def _spy_broadcast(*a, **k):
        sent.append(a)

    async def _spy_save(*a, **k):
        saved.append(a)
        return 0

    server.manager.broadcast = _spy_broadcast          # type: ignore[assignment]
    server._save_exchange = _spy_save                  # type: ignore[assignment]
    try:
        assert _post(HOME_LAT, HOME_LON).status_code == 200
    finally:
        server.manager.broadcast = real_broadcast      # type: ignore[assignment]
        server._save_exchange = real_save              # type: ignore[assignment]
    assert sent == [], "a location ping was broadcast to connected clients"
    assert saved == [], "a location ping was written to the conversation"


def test_a_malformed_body_is_rejected_without_recording_anything():
    d = _reset([HOME])
    res = _client.post("/location", json={"lat": "somewhere", "persona": PERSONA},
                       headers=_auth())
    assert res.status_code == 422, res.text
    assert not (d / "location_transitions.jsonl").exists()


def _clean() -> None:
    shutil.rmtree(_tmpdir, ignore_errors=True)


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
