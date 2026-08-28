# Location launch — Mike's steps + the session prompt [DB-0815-12]

*Written 2026-08-28 at Mike's instruction: everything needed to launch the geolocation piece,
in one place. Part A is his hands-on setup (no Claude session needed). Part B is the prompt
for the build session that adds zone suggestion. The first draft (capture, zone tool,
transitions log, context line) is already deployed server-side.*

---

## Part A — Mike's setup (do these in any order; ~10 minutes)

### A1. Create the zones file on the VM

1. **Get coordinates for each key place** (home, office, chess club — key places only;
   everywhere else is `away` by design): in Google Maps, long-press the spot → the
   coordinates appear in the info card → copy (format `51.50735, -0.12776`).
2. **On the VM** (SSH as usual over Tailscale, e.g.
   `ssh md-homefolder@metatron-vm.tail0acc5d.ts.net`; recovery path is the gcloud IAP command
   in `docs/INFRASTRUCTURE.md`):

```bash
cat > /home/md-homefolder/multi-model-mcp/data/personas/mike/zones.yaml <<'EOF'
zones:
  - name: home
    lat: 51.50735        # replace all three values per place
    lon: -0.12776
    radius_m: 150
  - name: office
    lat: 51.51234
    lon: -0.09876
    radius_m: 150
EOF
chmod 600 /home/md-homefolder/multi-model-mcp/data/personas/mike/zones.yaml
```

What this does: writes the zone list the Python mapper reads (name + centre + radius per
place) and restricts it to your user. ~150 m radius absorbs GPS jitter; use a smaller radius
only where two named places are close together (smallest matching circle wins). No restart
needed — the file is read per ping.

### A2. APK rebuild + sideload (phone won't show the 📍 control until this)

On the MacBook:

```bash
cd ~/Desktop/multi-model-mcp
npx cap sync android          # copy static/index.html into the Android project
cd android && ./gradlew assembleDebug && cd ..
./scripts/check_apk_sync.sh   # fails loudly if the bundled index.html is stale
python3 -m http.server 8888   # serve the APK to the phone over Tailscale
```

Phone browser → `http://<mac-tailscale-ip>:8888/android/app/build/outputs/apk/debug/app-debug.apk`,
install ("unknown sources" enabled).

### A3. Confirm the first draft live

Press the 📍 share button at a defined zone. Pass: the next turn's context reflects
"«zone» since HH:MM"; on the VM,
`/home/md-homefolder/multi-model-mcp/data/personas/mike/location_transitions.jsonl` holds
`{"zone", "entered_at"}` lines and **no coordinates anywhere** under `data/personas/mike/`.
Optionally flip the on-message ping toggle in the app (it ships OFF).

---

## Part B — the build-session prompt (zone suggestion, option b)

> Run as a supervised session (it touches `core/orchestrator.py`/`tools/` — Amber — and may
> propose one Red agent-file line at the end). Copy from here down.

---

Read `archive/handoffs/2026-08-28-location-first-draft.md` and the `[DB-0815-12]` entry in
`DEV_BACKLOG.md` — build to the recorded rulings, do not re-decide. The first draft is
deployed. This session adds **zone suggestion by expected-place lookup (option b, Mike's
ruling 2026-08-28)**:

1. **The vendor never receives the user's position.** When a place is *expected* — named in
   an upcoming calendar event or the current conversation — code may query the Google Places
   API (new module, e.g. `tools/places.py`) with the **place's name/address only** (forward
   geocode). The returned coordinates are compared **locally** against the latest ping.
   Rejected in the same ruling, do not build: sending randomised-nearby user coordinates.
2. **On a local match** (ping within a sane radius of the expected place, and the ping's zone
   is `away`): propose locking it in as a named zone via the existing confirm-card pattern
   (`tools/confirm.py` `request()`/`consume()`, `write_persona`-gate precedent). On approval,
   Python appends the zone to `data/personas/{persona}/zones.yaml` — the one write path this
   grants, and the file stays the VM's otherwise.
3. **Expected-place resolution is code, not model judgment:** candidate names come from
   structured sources (upcoming calendar event location/title fields; a place the user named
   this turn). No model is asked "where might the user be".
4. **Query bounds:** lookups fire only when there is a fresh ping AND a candidate expected
   place — never a poll loop, never a background scan, cache the geocode per place name so a
   repeated event does not re-query.
5. **API key:** a new external dependency — read `.env` handling in `docs/INFRASTRUCTURE.md`;
   the key is Mike's to create (Google Cloud Console → Places API); code must fail soft
   (no key → feature dormant, no error surfaced to the user).
6. **Tier discipline unchanged:** raw coordinates never enter any model prompt and now never
   leave the machine at all; the model sees only zone names and the proposal card text.
7. Tests in the first draft's style: no-coordinate assertions against bytes (vendor request
   payloads included — assert the outbound query contains no lat/lon), match/no-match logic,
   confirm-gate flow, zones.yaml append shape, geocode cache.
8. If any Synthesizer/agent instruction line is needed to voice the proposal naturally, it is
   Red: write it as proposed text in the handoff, do not edit `config/agents/`.

Deliverables: code + tests + a short handoff noting the (M) steps (Places API key; VM deploy;
whether an APK rebuild is needed — it is not, unless `static/index.html` changed).

---

*Cost note (CLAUDE.md § Costs): Places geocoding is pay-per-request on Mike's key — the
per-name cache in point 4 is the cost control; no standing spend is created (no watcher, no
poll). Build cost: one Green/Amber session, Opus.*
