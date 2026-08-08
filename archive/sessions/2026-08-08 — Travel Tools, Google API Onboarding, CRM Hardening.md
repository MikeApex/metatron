# 2026-08-08 — Travel Tools, Google API Onboarding, CRM Hardening

Started from a `DEV_BACKLOG.md` quick-scoring pass (importance × difficulty), executed the
top items, then followed the thread into Google API onboarding more broadly. Spans
2026-08-05 through 2026-08-08 by wall-clock date markers, one continuous session.

---

## Built and deployed (commit `c4ff279`)

**Travel/transit tools**
- `tools/tfl_status.py` — `get_tfl_status(lines)`, TfL line/bus/National-Rail status, no key. Renamed from `get_transit_status` (collided in name with an unbuilt Phase 5/6 GTFS-RT placeholder).
- `tools/flights.py` — `get_flight_status(flight_number, date)`, AeroDataBox via RapidAPI (Basic plan, free/unrestricted-duration — first recommendation named the wrong marketplace, corrected same session against AeroDataBox's own pricing page).
- `tools/routing.py` — `get_travel_time(origin, destination, mode, arrive_by)`, Google Maps Routes API, the default router everywhere/every mode. First version wrongly defaulted to TfL for London transit; corrected same session.
- `config/modules/regional_transit.yaml` + `tools/regional_transit.py` — shared, non-persona-scoped library naming which cities have a secondary status/cross-check tool (today: London → `get_tfl_status`), resolved per-query so a traveling persona gets the right city, not their home one.
- Wired into `check_calendar_conflicts`'s `location_transition_flags` (`tools/scheduling.py`) — real routed travel-time feasibility, not just a raw gap flag.

**Google Maps Routes API onboarded** on the existing `metatron-ai-499810` GCP project — `gcloud services enable routes.googleapis.com`, key restricted to that one API via `--api-target`.

**Google Contacts (People API) — built, then reversed same day.** Full OAuth 2.0 integration built (`tools/google_contacts.py`, `scripts/google_contacts_authorize.py`), then challenged and reversed after diagnosing the actual bug was local (no validation in `write_contact` against the user's own identity) and the real need (importing existing contacts) had a portable, non-OAuth answer (vCard). `read_google_contacts` fully unregistered from the orchestrator; code and `.env` credentials left dormant, not deleted.

**CRM/profile hardening** (this is what replaced Google Contacts):
- `tools/crm.py` `write_contact` — refuses an exact match to the user's own email/phone, flags (saves anyway) a near-miss via `difflib`.
- `relationships.md` — standing read-back instruction for every captured contact detail (broader than the code check, per direct feedback).
- `tools/profile.py` `write_profile` — changing an already-set email/phone/address now requires the same confirm-gate as `send_email`; first-time capture still writes immediately.
- `scripts/import_vcard_contacts.py` — bulk `.vcf` import, portable across Google/Apple/Outlook exports, rerun-safe (dedup by email).

**Also:**
- `shownIds` oldest-first eviction fix (`static/index.html`) — was a full `.clear()` past 100 exchanges, duplicate renders.
- `write_config` and `write_agent_config`'s guarded keys extended to the confirm-gate mechanism.

## Researched, documented, not built
- Google Places API and Google Pollen API — noted in `logistics.md`, `recreation_hobbies.md`, `research_agent.md`. Places blocked on a location signal (no GPS capability exists).
- Level 3 web-browsing access — scoped in `archive/plans/level3_web_actions_scope_2026-08-06.md`, not built.
- Real-time GPS + proactive area-scanning (the "lunch recommendation" idea) — raised, explicitly deferred as its own scoping conversation.

## Decisions made, and reversed
1. **AeroDataBox marketplace** — API.Market's Basic plan is a 7-day trial, not ongoing-free; RapidAPI's identically-named Basic plan is. Corrected after checking AeroDataBox's own pricing page directly.
2. **get_travel_time's default backend** — TfL-first-for-London was backwards; Google Maps is the default everywhere, TfL is a secondary cross-check only. Corrected same session at Mike's direction.
3. **Google Contacts OAuth** — built, technically working, then reversed: the actual bug needed local validation, not a third-party integration with a 7-day token-refresh problem. This is the session's highest-value lesson — see the PROJECT_LOG entry.
4. **Traveling-persona regional tools** — a static per-persona cache would have broken for a persona away from home; resolved with a shared library + per-query resolution instead, at no extra cost (confirmed the lookup is a local file read either way).

## Deploy detail
`.env` doesn't travel with `deploy.sh` — the two new API keys had to be appended to the VM's `.env` separately after the code deploy, or the new tools would have silently returned "not configured." Caught and fixed before calling the session done; verified via the systemd journal, not just `systemctl is-active`.

## Commit hygiene
Another window had `ROADMAP.md`, `SESSION.md`, `archive/PROJECT_LOG.md`, and several archive/test files staged or modified throughout. Committed with an explicit file pathspec rather than `git add -A` — verified with `git status` before and after that none of the other window's pending work was touched, staged, or discarded.

## Deferred / open
- Proactive-trigger wiring for `get_tfl_status`/`get_flight_status` (calendar → automatic call) — tools work when called, nothing calls them automatically yet.
- Google Places API build — waiting on a location-signal capability.
- Real-time GPS + area-scanning — its own scoping conversation, not started.
- Google Maps as a `get_travel_time` backend for driving/cycling outside TfL's range — built and live; no further action needed.
