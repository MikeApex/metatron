# Session ② launch prompt — supervised Red: scheduler pair, grants, Step-6/A4, medication, geolocation launch

*Written 2026-08-28 at Mike's instruction. This is the ready-to-paste prompt that starts
session ② (the supervised Red sitting from the revised 2026-08-28 order), with the
geolocation launch folded in — Mike ruled it rides a planned Red session rather than its own.
Paste everything inside the block as the `/metatron-code` arguments. Mike's two hands-on
prerequisites (§ at the bottom) can be done before the session or during it.*

---

```
/metatron-code This chat is supervised Red session ② executing the 2026-08-28
decisions, Mike present. Read archive/plans/capstone_cluster_review_2026-08-27.md
including both § Status update 2026-08-28 sections; each item's binding disposition
is its DEV_BACKLOG.md entry — build to it, do not re-decide. Fable throughout (Red
work is not delegated); every Red edit is shown to Mike before it lands; git diff
every file before staging — other sessions share this tree.

ITEM 1 — scheduler pair (Red, core/scheduler.py, supervised):
  [DB-0822-07] the 07:30/07:37 job collision — suppress the second firing rather
  than merging the jobs (the collision fed the [DB-0815-11] false-claim incident).
  [DB-0808-11] function jobs skip quiet hours — would push at 3am; same
  gate-stack extraction shape, same file, one sitting. Tests for both; the
  scheduler has none of its own gates tested today.

ITEM 2 — grants pass [DB-0810-03] (Red, both routing files + instruction text):
  all 24 live pairs ruled 2026-08-28 — apply exactly the entry's dispositions:
  six clusters granted/refused as recorded; journals route through Diarist with
  the dedup condition (written event travels in the context package + code
  backstop in tools/logger.py: same trace + same event type → no-op);
  goals_interviewer→write_baseline_period and pattern_miner→write_context_tracker
  granted; learning_growth gets write_agent_config NOT write_config (redirect its
  skill-goals line); the two logistics archive refusals dropped from the spec;
  enforce mode STAYS OFF (its flip is a separate decision — re-verify the
  logistics→send_email state at that moment, not from the entry). The Green dedup
  fix + logger backstop land in the same session. A7 check 10 unblocks here.

ITEM 3 — Step-6 caching behind the full A4 run [DB-0820-05 remainder + DB-0818-07]:
  seed a few health-domain knowledge entries on the VM's sarah_chen store
  (seed_medication_fixture precedent; name the machine — stores diverge), one
  entry deliberately contradicting a clinical read where the flag must still win.
  Then the FULL A4 run: tests/run_a4_safety.py, clinical + pipeline, both
  complexity tiers. Gate PASS → the Step-6 commit: mental_wellbeing +
  physical_health onto the cached path at core/orchestrator.py:4019, Flash-Lite
  six included, one commit. Note in the run's report that the suite now measures
  "safe WITH standing knowledge" — old baselines are not compared blind. The Pro
  flip is DECLINED (2026-08-28) — no routing-model changes here.

ITEM 4 — medication ranking Red half [DB-0808-14]: apply the spec at
  archive/plans/medication_ranking_spec_2026-08-27.md to physical_health.md
  (Red, supervised), then its Green follow-up. The owed A4 re-run is already
  PASS 3/3 (2026-08-27); item 3's full run re-covers it in the same session.

ITEM 5 — geolocation launch [DB-0815-12] (Amber build + (M) steps + one possible
  Red line):
  (a) (M) Mike creates the VM zones file and sideloads the rebuilt APK — steps
  and exact commands in the § below this prompt; can be done while items 1–4
  build. Then the first-draft live confirm: one 📍 ping at a defined zone →
  context carries "«zone» since HH:MM"; location_transitions.jsonl holds zone
  lines and no coordinate exists anywhere under data/personas/mike/.
  (b) Zone-suggestion build, option b (Mike's ruling 2026-08-28 — supersedes the
  reverse-geocode note): the vendor NEVER receives the user's position. When a
  place is expected — named in an upcoming calendar event or the current turn —
  code queries Google Places with the place's NAME only (new tools/places.py,
  forward geocode, per-name cache, no polling, fail-soft when the key is absent);
  the returned coordinates are compared LOCALLY against the latest ping; a match
  while the ping's zone is `away` raises the existing confirm card ("lock this in
  as a zone?"); approval → Python appends to data/personas/{p}/zones.yaml — the
  one write path granted to that file. Candidate places come from structured
  sources in code, never from asking a model where the user might be. Tests in
  the first draft's style, including an outbound-payload assertion: the vendor
  request contains no lat/lon. Rejected same ruling, do not build: randomised
  nearby coordinates.
  (c) If voicing the proposal needs a Synthesizer line, it is Red — Mike is
  present: apply it in-session with his approval rather than deferring.
  (d) (M) Mike creates the Places API key (Console → Places API) — feature stays
  dormant without it, by design.

Rules: nothing here re-opens the Pro decision, the ZDR basis, or any 2026-08-28
disposition. The A4 gate must PASS before the Step-6 commit exists — no
gate-then-commit-anyway. Deploy at close is Mike's (./deploy.sh is Denied to
sessions); the scheduler edits also need the VM systemd restart that deploy
performs. Close-out via /archive; anything out of scope or newly decision-shaped
goes to archive/handoffs/, not the backlog.
```

---

## § Mike's hands-on steps (referenced by item 5a — before or during the session)

### Zones file on the VM

1. Coordinates per key place (home, office, chess club — key places only; everywhere else is
   `away` by design): Google Maps → long-press the spot → copy (`51.50735, -0.12776`).
2. On the VM (`ssh md-homefolder@metatron-vm.tail0acc5d.ts.net`; recovery: the gcloud IAP
   command in `docs/INFRASTRUCTURE.md`):

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

Writes the zone list the Python mapper reads and restricts it to your user; ~150 m absorbs
GPS jitter (smallest matching circle wins if places are close). No restart needed — read per
ping.

### APK rebuild + sideload (phone won't show the 📍 control until this)

```bash
cd ~/Desktop/multi-model-mcp
npx cap sync android          # copy static/index.html into the Android project
cd android && ./gradlew assembleDebug && cd ..
./scripts/check_apk_sync.sh   # fails loudly if the bundled index.html is stale
python3 -m http.server 8888   # serve the APK to the phone over Tailscale
```

Phone browser → `http://<mac-tailscale-ip>:8888/android/app/build/outputs/apk/debug/app-debug.apk`
("unknown sources" enabled).
