#!/usr/bin/env python3
"""
Has Google shipped a Gemini model newer than the ones this fleet runs, and can we
actually call it?

A DEV TOOL, RUN ON DEMAND — DELIBERATELY NOT A SCHEDULED JOB
-------------------------------------------------------------
This was first built as a `function:` job in `core/scheduler.py`. **That was the wrong
layer** (Mike, 2026-09-01). The scheduler runs the *product*: jobs that serve the user's
life management, on the user's VM. Model availability is a development concern — the
finding is actionable only by a developer making a Red-tier routing edit, it does not
change anything for the user, and putting it in the scheduler would have meant a new
`monthly` cadence in Red-tier shared scheduling logic for a single non-product job, plus
a runtime `tools/` module that no agent ever calls. `.claude/rules/deploy.md` already
warns that dev-process machinery outnumbers product machinery here; that is the ratio
this decision protects.

The recurrence lives in `DEV_BACKLOG.md` as a `due:` item instead — an existing
convention ("blocked on this, re-check on that date"), no new mechanism, and it surfaces
in `/backlog` triage where a routing decision would actually get made.

WHY IT DOES NOT JUST READ A CATALOGUE
--------------------------------------
On 2026-09-01 both `gemini-3.8-flash` and `gemini-3.5-pro` returned `200 GA` from the
Vertex publisher-model *metadata* endpoint and `404` from `generateContent` on the
`global` endpoint this deployment uses. **A catalogue listing is not availability.** A
check that only enumerated the catalogue would have recommended migrating to 3.8 Flash
and the migration would have 404'd in production — the same shape as the `us-central1`
trap in CLAUDE.md § Infrastructure traps, where the wrong endpoint returns empty rather
than erroring. Every candidate is therefore confirmed with a real call.

DISCOVERY: TWO SOURCES, BECAUSE NEITHER IS SUFFICIENT
------------------------------------------------------
There is no `publishers/google/models` LIST endpoint (404 as of 2026-09-01), so:

1. **Cloud Billing SKU catalogue** — every Gemini model with a *price* has a SKU. Free,
   and finds models under names we would not think to guess.
2. **Generated version ids** walked forward from the fleet. Needed because a model gets
   a SKU when it gets a price, and the newest do not have one yet: `gemini-3.8-flash`
   was live in the model catalogue on 2026-09-01 with no SKU anywhere in the billing
   service. **SKU-only discovery is blind to exactly the releases this exists to catch**
   — found by running it, not by reasoning about it.

Both feed one funnel: id -> free metadata lookup -> live call. Only the last is billable.

COST
----
SKU listing and metadata lookups are free and cost ZERO model tokens. Live probes are
~10 tokens each; a typical run makes one or two, so a run costs well under $0.001. **No
standing cost** — nothing is cached, created, reserved or left running, which is part of
why on-demand is the right shape for it. A run takes ~20s, nearly all in the free filter.

USAGE
    python3 scripts/check_model_availability.py            # human-readable report
    python3 scripts/check_model_availability.py --json     # machine-readable
    python3 scripts/check_model_availability.py --quiet    # print only if something is new
    python3 scripts/check_model_availability.py --all      # probe every candidate

Exit codes: 0 = ran (whether or not anything was found), 1 = the check itself failed.
A newer model being available is NOT an error. THIS REPORTS; IT NEVER EDITS ROUTING.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Vertex AI in the Cloud Billing catalogue. Confirmed 2026-09-01.
_VERTEX_BILLING_SERVICE = "services/C7E2-9256-1C43"
_BILLING_API = "https://cloudbilling.googleapis.com/v1"
_AIPLATFORM_API = "https://aiplatform.googleapis.com/v1"

# "Gemini 3.7 Flash Global Text Input - Predictions" -> ("3.7", "Flash")
_SKU_RE = re.compile(r"\bGemini\s+(\d+(?:\.\d+)?)\s+(Pro|Flash(?:\s+Lite)?)\b", re.IGNORECASE)

# SKUs that are not a general text model we would ever route to.
_SKU_EXCLUDE = (
    "codemender", "tuning", "robotics", "embedding", "imagen", "veo",
    "computer use", "native audio", "live", "transcribe", "translate", "tts",
)


# ---------------------------------------------------------------- plumbing

def _token() -> str:
    import google.auth
    import google.auth.transport.requests

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _project() -> str:
    proj = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not proj:
        import google.auth

        _, proj = google.auth.default()
    if not proj:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT unset and ADC has no default project")
    return proj


def _location() -> str:
    """Mirrors core.orchestrator._vertex_location(): default `global`, never a region."""
    return os.environ.get("GOOGLE_CLOUD_LOCATION") or "global"


def _get(url: str, token: str, project: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            # Required: ADC has no default quota project; without this the aiplatform
            # API returns 403 rather than the resource.
            "X-Goog-User-Project": project,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


# ---------------------------------------------------------------- discovery

def _tier_of(model_id: str) -> str:
    if model_id.endswith("-flash-lite"):
        return "flash-lite"
    if model_id.endswith("-pro"):
        return "pro"
    if model_id.endswith("-flash"):
        return "flash"
    return "other"


def _version_key(model_id: str) -> tuple:
    """Sortable (major, minor) so 3.10 > 3.9. Unparseable sorts lowest."""
    m = re.match(r"gemini-(\d+)(?:\.(\d+))?", model_id)
    if not m:
        return (-1, -1)
    return (int(m.group(1)), int(m.group(2) or 0))


def discover_models(token: str, project: str) -> set[str]:
    """Every gemini-<ver>-<tier> id that has a billing SKU. Zero model tokens."""
    found: set[str] = set()
    page = None
    while True:
        url = f"{_BILLING_API}/{_VERTEX_BILLING_SERVICE}/skus?pageSize=5000"
        if page:
            url += f"&pageToken={page}"
        data = _get(url, token, project)
        for sku in data.get("skus", []):
            desc = sku.get("description", "")
            if any(x in desc.lower() for x in _SKU_EXCLUDE):
                continue
            m = _SKU_RE.search(desc)
            if not m:
                continue
            found.add(f"gemini-{m.group(1)}-{m.group(2).lower().replace(' ', '-')}")
        page = data.get("nextPageToken")
        if not page:
            break
    return found


def generate_candidates(fleet: set[str]) -> set[str]:
    """Guess forward from what we run: next minors, and the next major. See header."""
    out: set[str] = set()
    tiers = {_tier_of(m) for m in fleet if _tier_of(m) != "other"} or {"flash", "flash-lite", "pro"}
    majors = {_version_key(m)[0] for m in fleet if _version_key(m)[0] > 0} or {3}
    for tier in tiers:
        for major in sorted(majors):
            for minor in range(0, 13):
                out.add(f"gemini-{major}.{minor}-{tier}")
            for minor in range(0, 5):
                out.add(f"gemini-{major + 1}.{minor}-{tier}")
            out.add(f"gemini-{major + 1}-{tier}")
    return out


def current_fleet() -> set[str]:
    """Model ids this deployment routes to, read from the routing files themselves."""
    fleet: set[str] = set()
    for name in ("routing_cloud.yaml", "routing.yaml"):
        path = REPO / "config" / "modules" / name
        if not path.exists():
            continue
        for match in re.finditer(r'model:\s*"(?:models/)?(gemini-[^"]+)"', path.read_text()):
            fleet.add(match.group(1))
    return fleet


def exists_in_catalogue(model_id: str, token: str, project: str) -> bool:
    """Free metadata lookup. NOT sufficient alone — see header."""
    try:
        _get(f"{_AIPLATFORM_API}/publishers/google/models/{model_id}", token, project)
        return True
    except Exception:  # noqa: BLE001
        return False


def probe_live(model_id: str, token: str, project: str, location: str) -> tuple[bool, str]:
    """One real generateContent call — the only thing that proves availability."""
    url = (f"{_AIPLATFORM_API}/projects/{project}/locations/{location}"
           f"/publishers/google/models/{model_id}:generateContent")
    body = json.dumps({"contents": [{"role": "user", "parts": [{"text": "hi"}]}]}).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Authorization": f"Bearer {token}", "X-Goog-User-Project": project,
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60):
            return True, "live"
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False, "in catalogue, not served on this endpoint"
        detail = ""
        try:
            detail = json.loads(exc.read().decode()).get("error", {}).get("message", "")[:90]
        except Exception:  # noqa: BLE001
            pass
        return False, f"HTTP {exc.code}: {detail}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def run(probe_all: bool = False) -> dict:
    token, project, location = _token(), _project(), _location()
    fleet = current_fleet()
    catalogue = discover_models(token, project)

    # Newest version we run, per tier. A new Pro is not evidence about Flash routing.
    best: dict[str, tuple] = {}
    for model in fleet:
        key = _version_key(model)
        if key > best.get(_tier_of(model), (-1, -1)):
            best[_tier_of(model)] = key
    # Floor for a tier we do NOT run. Without this, dropping Pro from the fleet made
    # every Pro that ever existed look new — the first run duly reported gemini-2.5-pro
    # as newer than gemini-3.7-flash.
    overall = max(best.values(), default=(-1, -1))

    pool = set(catalogue) | generate_candidates(fleet)
    interesting = [
        m for m in sorted(pool, key=lambda x: (_tier_of(x), _version_key(x)))
        if m not in fleet and _tier_of(m) != "other"
        and (probe_all or _version_key(m) > best.get(_tier_of(m), overall))
    ]
    # Free filter first, so the billable probe only ever sees real models.
    candidates = [m for m in interesting if exists_in_catalogue(m, token, project)]

    results = []
    for model in candidates:
        ok, note = probe_live(model, token, project, location)
        results.append({"model": model, "tier": _tier_of(model), "available": ok, "note": note})

    return {
        "location": location,
        "fleet": sorted(fleet),
        "catalogue_size": len(catalogue),
        "ids_considered": len(interesting),
        "candidates_probed": len(candidates),
        "available": [r for r in results if r["available"]],
        "unavailable": [r for r in results if not r["available"]],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Check for newer callable Gemini models.")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--quiet", action="store_true", help="print only if something is available")
    ap.add_argument("--all", action="store_true",
                    help="probe every candidate, not just newer-than-fleet")
    args = ap.parse_args()

    try:
        report = run(probe_all=args.all)
    except Exception as exc:  # noqa: BLE001
        print(f"check_model_availability: FAILED — {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    if args.quiet and not report["available"]:
        return 0

    print(f"Endpoint: {report['location']}   "
          f"SKU catalogue: {report['catalogue_size']} models   "
          f"considered: {report['ids_considered']}   probed live: {report['candidates_probed']}")
    print(f"Fleet:    {', '.join(report['fleet']) or '(none found)'}")

    if report["available"]:
        print("\nNEWER AND CALLABLE — worth considering:")
        for r in report["available"]:
            print(f"  * {r['model']:<28} ({r['tier']})")
        print("\n  Routing is deliberately NOT changed by this script. To adopt one, edit\n"
              "  config/modules/routing_cloud.yaml (Red tier) AND add a pricing entry to\n"
              "  config/modules/spend_guard.yaml — an unpriced model bills at the `default`\n"
              "  rate, and a model entry missing cache_storage_per_hour bills storage at zero.\n"
              "  Re-check the cache token floor as well; it is per-model, not universal.")
    else:
        print("\nNothing newer is callable on this endpoint.")

    if report["unavailable"]:
        print("\nNewer, but NOT callable here (catalogue presence is not availability):")
        for r in report["unavailable"]:
            print(f"  x {r['model']:<28} {r['note']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
