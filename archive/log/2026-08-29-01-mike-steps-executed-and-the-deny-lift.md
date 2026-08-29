### 2026-08-29 (the three Mike-steps land, and the deny tier gains a plan-scoped lift) — hook uncommitted until this close-out, **nothing to deploy**

**Incoming:** `/metatron-code` on `archive/handoffs/2026-08-28-post-session-two-mike-steps.md`
— walk Mike's three post-session-② steps. Fable throughout (Mike's model split; confirmed the
right tier — the session was verify-and-walkthrough, no Red build).

**All three steps closed, live-verified:**

1. **Travel check un-silenced.** VM `scheduler.yaml` gained `respect_quiet_hours: false` on
   `daily_travel_check` (verified absent first; `core/scheduler.py:320` confirmed the skip
   mechanism), scheduler restarted 10:48 BST. Pass signal owed: tomorrow's 06:45 fire.
2. **Zones file** — home + office written on the VM (Mike's paste; chess club dropped as
   example-only). ~2.8 km apart, no circle overlap.
3. **APK** — synced, built, `check_apk_sync.sh` byte-match PASS; served from the APK's own
   directory (narrower than the handoff's repo-root serve) at `100.70.67.45:8888`.

**The deny tier gained a plan-scoped lift (Mike's ask, generalised from step 1's lift).**
`scripts/hook_deny_lift.py` (PreToolUse, Write|Edit): allows Denied-tier paths listed in a
work-order file written **only on Mike's approval at plan-implementation time**, ≤7-day expiry,
self-deleting. `NEVER_LIFT` floor hardcoded (constitution, `.env*`, keys, `deploy.sh`, both
settings files, the mechanism itself). Logic-tested 8/8 in scratchpad. Docs:
`.claude/rules/deploy.md` § Plan-scoped deny lift; CLAUDE.md pointer (squeezed to 300/300
exactly); lift file gitignored. **It retires per-phase deny-list edits** (standing-machinery
rule). **Rejected:** per-phase settings edits (forgotten restore is silently invisible);
`--dangerously-skip-permissions` (blunt). **UNVERIFIED: hook-allow vs settings deny is
designed from docs, not measured — probe owed at next session start**, instructions in
deploy.md; session ③'s prompt carries it as Step 0.

**Believed true earlier, wrong / notable:** an `allow` rule *cannot* outrank a deny anywhere —
lifting means editing the deny or a hook, which shaped the whole design. And the settings deny
on `config/personas/mike/**` never reached the VM copy at all — an SSH edit is a Bash call,
file-pattern denies don't see inside it; the only mechanical gate there turned out to be the
auto-mode classifier, which blocked this session's remote sed, both settings.json edits, and
the `http.server` — all handed to Mike as pastes. Mike's settings paste dropped the `Agent`
hook block; caught by re-validation, restored by his second paste (all three groups confirmed).

**Also:** deploy cleared for the other chat — nothing here needs the VM, and the post-deploy
`grep respect_quiet_hours` check confirmed the flag survives. Session ③ prompt (the last
planned Red session — email surfacing `[DB-0822-09]`, the `[DB-0822-08]` re-measure-then-fix,
the ritual Red line, judgment gate + Diarist list shape, handoff sweep) delivered:
`archive/handoffs/2026-08-29-red-session-three-prompt.md`. `.claude/rules/deploy.md` is 24
lines over its 100-line ceiling (was ~97 pre-session); probe result will absorb ~6 — trim pass
flagged for next archive.

**Outgoing handoff carried:** session ② had landed all five items deployed; the three Mike-steps
were the block before session ③. Now: steps done, ③ prompt ready, deny-lift probe owed.
