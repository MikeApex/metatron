# Mike's steps after Red session ② (2026-08-28) — three tasks, then confirms on ordinary use

*Written at session ② close. Deploy is DONE (VM on `d750fbb`). The Places API key is DONE
(already in the VM's `.env` since 2026-08-26 — zone suggestion is live, not dormant).
What remains is below, in priority order. All commands run **on the VM** unless marked
MacBook. SSH: `ssh md-homefolder@metatron-vm.tail0acc5d.ts.net` (recovery route: the gcloud
IAP command in `docs/INFRASTRUCTURE.md`).*

---

## 1. URGENT — un-silence the travel check (one line, on the VM)

Since this deploy, function jobs respect quiet hours. Your `scheduler.yaml` defines
`daily_travel_check` at 06:45 — inside your 22:00–07:00 quiet window — without the
opt-out flag, so **it is currently skipped every morning**. Verified 2026-08-28 at
session close.

What the command does: appends `respect_quiet_hours: false` under the
`daily_travel_check:` job in your live scheduler config, which tells the new gate this
job may run pre-07:00. A morning-departure disruption at 06:45 is exactly what you want
to be woken for; the job pushes only on an actual delay or cancellation, so the flag
cannot produce routine early pushes.

```bash
# On the VM. Adds the flag as the last line of the daily_travel_check block.
sed -i '/^  daily_travel_check:/,/^  [a-z_]*:/{s/^    notification: push$/    notification: push\n    respect_quiet_hours: false/}' \
  /home/md-homefolder/multi-model-mcp/config/personas/mike/scheduler.yaml

# Check it landed (should print the job block with the new flag):
grep -A6 'daily_travel_check:' /home/md-homefolder/multi-model-mcp/config/personas/mike/scheduler.yaml

# Restart the scheduler so it re-reads the config:
sudo systemctl restart metatron-scheduler
```

If the `sed` looks fragile to you, just open the file in an editor and add
`    respect_quiet_hours: false` (4-space indent) as a new line inside the
`daily_travel_check:` block. Then restart the scheduler as above.

**Pass signal:** tomorrow's scheduler log shows `daily_travel_check` firing at 06:45
(`journalctl -u metatron-scheduler --since 06:40 | grep travel`), not
`skipping daily_travel_check — quiet hours`.

---

## 2. Zones file on the VM (geolocation knows no places until this exists)

Every ping currently resolves to `away` because `data/personas/mike/zones.yaml` does not
exist. Key places only — home, office, chess club; everywhere else is `away` by design.

1. Get coordinates per place: Google Maps → long-press the spot → copy
   (`51.50735, -0.12776`).
2. On the VM (replace the three values per place; ~150 m absorbs GPS jitter; smallest
   matching circle wins if places are close):

```bash
cat > /home/md-homefolder/multi-model-mcp/data/personas/mike/zones.yaml <<'EOF'
zones:
  - name: home
    lat: 51.50735
    lon: -0.12776
    radius_m: 150
  - name: office
    lat: 51.51234
    lon: -0.09876
    radius_m: 150
EOF
chmod 600 /home/md-homefolder/multi-model-mcp/data/personas/mike/zones.yaml
```

No restart needed — the file is read per ping. Approved zone *suggestions* append to this
same file automatically; your hand-written entries are never touched.

---

## 3. APK rebuild + sideload (phone won't show the 📍 control until this)

On the **MacBook**:

```bash
cd ~/Desktop/multi-model-mcp
npx cap sync android          # copy static/index.html into the Android project
cd android && ./gradlew assembleDebug && cd ..
./scripts/check_apk_sync.sh   # fails loudly if the bundled index.html is stale
python3 -m http.server 8888   # serve the APK to the phone over Tailscale
```

Phone browser → `http://<mac-tailscale-ip>:8888/android/app/build/outputs/apk/debug/app-debug.apk`
("unknown sources" enabled). Kill the `http.server` with Ctrl-C when done.

---

## Confirms that drain on ordinary use (no dedicated time needed)

1. **Scheduler collision:** one morning where the roaming check-in would land near 07:30
   — you get the brief alone, and the check-in returns ~3h later.
2. **Location first draft:** one 📍 ping at a defined zone → next turn's context carries
   "«zone» since HH:MM"; `data/personas/mike/location_transitions.jsonl` holds only
   `{"zone", "entered_at"}` lines; no coordinate anywhere under `data/personas/mike/`.
3. **Zone suggestion (live now — key already in place):** one away ping while a calendar
   event within ~3h names a venue → the app shows a "Lock «place» in?" card; approving
   adds it to `zones.yaml` with the place's own public coordinates.
4. **Grants in use:** any specialist archiving a list item twice (e.g. a book at mention
   and at completion) shows one updated entry, not two.
5. **Medication ranking:** nothing to do — it activates when a `discontinuation_risk: true`
   medication exists in the profile; the profile edit happens in conversation with
   Physical Health whenever relevant.

## Session ③ note (email surfacing, next in the revised order)

Unchanged from the capstone plan: `[DB-0822-09]` + the `[DB-0822-08]` re-measure + the
ritual Red Synthesizer line + judgment gate + Diarist list-shape line (verbatim in the
2026-08-28 handoffs). Tier note from session ②, worth adopting: farm the Amber halves to
Opus workers with Fable reviewing — session ② ran Fable-throughout per its handoff, and
items 3/5's build halves didn't need it.
