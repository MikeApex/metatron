# Handoff — location first draft [DB-0815-12] build outcome (2026-08-28)

*From the Green/Amber spinoff chat (Fable review, Opus worker). Merged `029905e`. **Deploys
owed (Mike): VM deploy for `core/` + `tools/` + `config/templates/`, and an APK rebuild +
sideload before the phone sees the 📍 control** (the browser PWA picks it up on the VM
deploy).*

## What the tool now does

Tell Metatron where you are and the next turn's context carries *"home since 14:02"* — a
place the user named, nothing more. Two capture modes, both a deliberate act ("while using
the app" permission): an **on-message ping that DEFAULTS OFF** (strict `=== 'on'` against
localStorage — never-set/cleared/corrupt/`'true'`/`'ON'` all read as off; asserted by
`tests/test_location_onsend_default.js`, 11/11) and a **manual share button**. Background/
scheduled pings are explicitly a later build; a JS test asserts nothing polls.

- **The binding tier ruling is enforced in code:** `POST /location` resolves the coordinate
  to a zone inside the handler and the coordinate stops there — never written to disk, never
  in a conversation row, never in an error detail, never in a prompt. Three tests assert the
  no-coordinate guarantee against bytes (disk, response, context line), not intent.
- **Storage is zone transitions only:** `data/personas/{p}/location_transitions.jsonl`
  (0600, append-only, one line per *change* — same-zone repeats keep the original arrival, so
  "since" means since arrival). No raw trail exists, not even behind a debug flag (a flag can
  be left on — raise it only if Mike wants a debug path).
- **Zones are Mike's to define:** template at
  [config/templates/zones.yaml](../../config/templates/zones.yaml) (name/lat/lon/radius_m;
  smallest matching circle wins; no file or no match → `away`, never an error). **Mike copies
  and edits the live copy at `data/personas/mike/zones.yaml` on the VM** — code only reads it.
- **Context line** reuses the `[DB-0822-06]` age-annotation phrasing and states its own
  limits ("reported by their phone when they last used the app… not a live position").

Tests: 30/30 tool, 10/10 endpoint, 11/11 JS off-default, plus server-auth/attachments/
reconnect/context suites re-run clean.

## Deferred, recorded so it survives

1. Background/stochastic pings and proactive scans on zone transitions — later build; the
   transition record they would fire on now exists.
2. `zones.yaml` not wired into persona provisioning (`scripts/new_persona.sh`) — Mike copies
   the template by hand for now.
3. **No model-callable location tool was registered** — the zone reaches the model only as
   the context line, the tightest reading of the ruling. If a specialist should be able to
   *ask* where the user is, that is a separate grant decision (`[DB-0810-03]` territory).

## Confirmation after deploy + APK sideload

Enable the ping (or press share) near a defined zone → next turn's brief reflects "home since
HH:MM"; grep the VM's `location_transitions.jsonl` for exactly `{"zone", "entered_at"}` lines
and confirm no coordinate appears anywhere under `data/personas/mike/`.
