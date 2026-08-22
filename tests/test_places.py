"""
tests/test_places.py — venue discovery, [DB-0808-04].

Pins the five behaviours that decide whether a suggestion the user acts on is real:

1. No key configured → an honest error naming the missing variable, never a guess.
   The key is deliberately a *second* one (GOOGLE_PLACES_API_KEY); the routing key is
   restricted to routes.googleapis.com and a Places call on it fails.
2. Happy path → the compact record the model prompt consumes, parsed from a canned
   Places API (New) response.
3. No venues found → an error, NOT {"places": []}. An empty structure reads as success
   and invites the model to fill the gap with a plausible-sounding café that isn't there.
4. max_results capped at 10 and floored at 1, both in the request and in the response.
5. Network failure / HTTP error → {"error": ...}, never a raised exception into dispatch.

No network: requests.post is stubbed throughout.

Standalone runner (no pytest dependency), matching tests/test_tool_error_flag.py.

Usage:
    python tests/test_places.py

Exits 0 if every test passes, 1 otherwise.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests  # noqa: E402

from tools import places  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, condition, detail))


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


CANNED = {
    "places": [
        {
            "displayName": {"text": "Beans & Ink"},
            "formattedAddress": "12 Example Street, London N1 1AA, UK",
            "rating": 4.6,
            "userRatingCount": 218,
            "priceLevel": "PRICE_LEVEL_INEXPENSIVE",
            "currentOpeningHours": {"openNow": True},
            "location": {"latitude": 51.5372, "longitude": -0.0987},
        },
        {
            # Deliberately sparse: no rating, no hours, no price. Those keys must be
            # absent rather than present-and-null — a null rating displayed as "0" is
            # worse than no rating at all.
            "displayName": {"text": "The Corner Cup"},
            "formattedAddress": "3 Sample Road, London N1 2BB, UK",
        },
    ]
}


def _install_stub(monkeypatched: dict, payload=None, exc: Exception | None = None):
    """Replace requests.post; record the call so the request body can be asserted on."""

    def fake_post(url, headers=None, json=None, timeout=None):
        monkeypatched["url"] = url
        monkeypatched["headers"] = headers or {}
        monkeypatched["body"] = json or {}
        monkeypatched["timeout"] = timeout
        if exc is not None:
            raise exc
        return _FakeResponse(payload if payload is not None else {})

    places.requests.post = fake_post


def run() -> None:
    original_post = requests.post
    original_key_getter = places._places_key
    calls: dict = {}

    try:
        # --- 1. unconfigured key -------------------------------------------------
        places._places_key = lambda: None
        _install_stub(calls, CANNED)
        out = places.find_places("café", "10 Downing Street, London")
        check(
            "unconfigured key returns an honest error",
            out.get("error") == "Venue search requires GOOGLE_PLACES_API_KEY, which is not configured.",
            repr(out),
        )
        check("unconfigured key makes no HTTP call", "url" not in calls, repr(calls.get("url")))

        # Every test below has a key.
        places._places_key = lambda: "test-key-not-real"

        # --- 2. happy path -------------------------------------------------------
        calls.clear()
        _install_stub(calls, CANNED)
        out = places.find_places("café", "10 Downing Street, London")
        got = out.get("places") or []
        check("happy path returns places, no error", "error" not in out and len(got) == 2, repr(out))
        first = got[0] if got else {}
        check("name parsed from displayName.text", first.get("name") == "Beans & Ink", repr(first))
        check(
            "address parsed",
            first.get("address") == "12 Example Street, London N1 1AA, UK",
            repr(first.get("address")),
        )
        check("rating and count carried", first.get("rating") == 4.6 and first.get("rating_count") == 218, repr(first))
        check("open_now carried", first.get("open_now") is True, repr(first.get("open_now")))
        check("price level made readable", first.get("price_level") == "inexpensive", repr(first.get("price_level")))
        check(
            "location rendered as 'lat,lon' for get_travel_time",
            first.get("location") == "51.5372,-0.0987",
            repr(first.get("location")),
        )
        second = got[1] if len(got) > 1 else {}
        check(
            "missing fields are omitted, not null",
            all(k not in second for k in ("rating", "rating_count", "open_now", "price_level")),
            repr(second),
        )
        check(
            "FieldMask is sent and stays inside the basic/pro tier",
            "X-Goog-FieldMask" in calls.get("headers", {})
            and "places.reviews" not in calls["headers"]["X-Goog-FieldMask"]
            and "places.displayName" in calls["headers"]["X-Goog-FieldMask"],
            repr(calls.get("headers", {}).get("X-Goog-FieldMask")),
        )
        check("timeout is TIMEOUT_SECONDS", calls.get("timeout") == places.TIMEOUT_SECONDS, repr(calls.get("timeout")))
        check(
            "query is composed as '<kind> near <address>'",
            calls.get("body", {}).get("textQuery") == "café near 10 Downing Street, London",
            repr(calls.get("body")),
        )

        # --- 3. empty results ----------------------------------------------------
        calls.clear()
        _install_stub(calls, {"places": []})
        out = places.find_places("falconry supplies", "Trafalgar Square")
        check(
            "no results returns an error, not an empty list",
            "error" in out and "places" not in out,
            repr(out),
        )
        check(
            "no-results error names what was searched for",
            "falconry supplies" in out.get("error", "") and "Trafalgar Square" in out.get("error", ""),
            repr(out.get("error")),
        )

        calls.clear()
        _install_stub(calls, {})  # key entirely absent, not just empty
        out = places.find_places("café", "Trafalgar Square")
        check("missing 'places' key treated as no results", "error" in out, repr(out))

        # --- 4. max_results capping ---------------------------------------------
        many = {"places": [{"displayName": {"text": f"Place {i}"}, "formattedAddress": "x"} for i in range(25)]}
        calls.clear()
        _install_stub(calls, many)
        out = places.find_places("café", "Soho", max_results=99)
        check("max_results capped at 10 in the request", calls["body"]["maxResultCount"] == 10, repr(calls["body"]))
        check("max_results capped at 10 in the response", len(out.get("places", [])) == 10, len(out.get("places", [])))

        calls.clear()
        _install_stub(calls, many)
        out = places.find_places("café", "Soho", max_results=0)
        check("max_results floored at 1", calls["body"]["maxResultCount"] == 1, repr(calls["body"]))

        calls.clear()
        _install_stub(calls, many)
        out = places.find_places("café", "Soho")
        check("default max_results is 5", calls["body"]["maxResultCount"] == 5, repr(calls["body"]))

        # --- 5. transport failure ------------------------------------------------
        calls.clear()
        _install_stub(calls, exc=requests.Timeout("timed out"))
        out = places.find_places("café", "Soho")
        check("timeout returns an error dict, not an exception", "error" in out, repr(out))

        calls.clear()
        _install_stub(calls, exc=requests.HTTPError("403 Forbidden"))
        out = places.find_places("café", "Soho")
        check("HTTP error returns an error dict", "error" in out and "403" in out["error"], repr(out))

        # Unparseable body: .json() raises ValueError.
        class _BadJSON(_FakeResponse):
            def json(self):
                raise ValueError("not json")

        def bad_post(url, headers=None, json=None, timeout=None):
            return _BadJSON({})

        places.requests.post = bad_post
        out = places.find_places("café", "Soho")
        check("unparseable response returns an error dict", "error" in out, repr(out))

        # --- input validation ----------------------------------------------------
        calls.clear()
        _install_stub(calls, CANNED)
        check("blank query rejected", "error" in places.find_places("  ", "Soho"))
        check("blank near rejected", "error" in places.find_places("café", "  "))

        # --- schema hygiene -------------------------------------------------------
        schema = places.FIND_PLACES_SCHEMA
        check("schema name matches the function", schema["name"] == "find_places")
        blob = (schema["description"] + str(schema["input_schema"])).lower()
        check(
            "schema names no provider",
            not any(w in blob for w in ("google", "places api", "maps platform")),
            schema["description"],
        )
        check(
            "schema requires query and near only",
            schema["input_schema"]["required"] == ["query", "near"],
            repr(schema["input_schema"]["required"]),
        )

    finally:
        places.requests.post = original_post
        places._places_key = original_key_getter

    failed = [r for r in _results if not r[1]]
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if not ok and detail else ""))
    print(f"\n{len(_results) - len(failed)}/{len(_results)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    run()
