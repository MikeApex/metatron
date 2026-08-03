# 2026-08-03 — Check-in Restraint, Persona Config Ownership, Profile Capture

Continuation of [2026-08-02 — Synth Self-Development Awareness and Dev Backlog](2026-08-02%20—%20Synth%20Self-Development%20Awareness%20and%20Dev%20Backlog.md), same session. That file covers the backlog mechanism; this one covers everything after it.

Not to be confused with the parallel session's [2026-08-03 — SEQ 021 Logistics Turn Burn, Clock Injection, Tool Error Hints](2026-08-03%20—%20SEQ%20021%20Logistics%20Turn%20Burn,%20Clock%20Injection,%20Tool%20Error%20Hints.md).

**Commits:** `ae252ab`..`35e53ee` (mine: check-in restraint, backlog ledger, persona config ownership, `write_profile`/`read_profile`, and one revert).

---

## 1. The backlog captured its first real request

`INSTRUCTION_CHANGE_REQUEST` logged at 09:11:56 from an ordinary conversation, not a test probe — *"proactive check-ins very brief and do not include long summaries of pending tasks, especially when the user has not been actively responding."*

**But the live notification never fired, and could not have.** The confirmation line went through `_trace()`, which is a no-op unless `AI_TRACE` is set — and the service never sets it. So the one path whose entire purpose is a silent background record was itself invisible. Fixed, then caught that the first fix was also wrong (the module logger is pinned to `WARNING`, so `logger.info` emitted nothing either). Now a dedicated logger at INFO, verified emitting on both the success and discard paths before claiming it worked.

## 2. Check-in restraint — root cause was not an agent file

Four complaints, one cause. `companion_checkin`'s **own prompt** instructed it to *"lead with the most useful outstanding item… be specific about which one and why it matters now"* — every 180 minutes, all day. An unresolved calendar item was therefore correctly surfaced six times. Editing `synthesizer.md` would not have fixed it.

This produced the layer model the user then asked to formalise:

| Layer | Owns | Scope |
|---|---|---|
| `config/agents/*.md` | judgement | all personas |
| `config/personas/{p}/scheduler.yaml` | *when*, and the opening prompt | one persona |
| `core/scheduler.py` | mechanism only — the gate stack | all personas |
| `config/personas/{p}.md` | style preferences | one persona |

**Shipped:**
- Prompt rewritten in `config/templates/scheduler.yaml` (the baseline every new persona inherits — which also hardcoded "Mike" in a file used to provision *other people*) and mike's copy. Template cadence corrected 90 → 180.
- Two opt-in gates in `core/scheduler.py`: `quiet_after_user_minutes: 60` (don't interrupt a live conversation) and `min_gap_minutes: 180` (never more often, however quiet). `interval_minutes` becomes the poll rate, not the send rate.
- Five rules in `synthesizer.md`: raise a thing once · explain a recommendation the first time and not every time · never tell the user to enjoy things · beware the loudest available signal · **and where the record is thin, ask for the missing data** (the user's addition).

**Cost:** strictly lower than before. Polling is local file reads with no model call, and `min_gap` preserves the old ceiling of ~5/day. On a conversational day it may fire zero times — which the user confirmed is by design.

**Order mattered.** Gate code deployed before the config numbers moved; dropping `interval_minutes` to 30 first would have fired check-ins every 30 minutes, 6× the rate, at ~$0.025 a pipeline.

**Two bugs caught by testing rather than by review:**
1. The gate read `entry["timestamp"]`; conversation records key on **`ts`** (`timestamp` is the *quality-event* key). It would have matched nothing, failed open, and left check-ins firing exactly as before while appearing to work.
2. `timedelta` used but not imported — `py_compile` passes, and this is the same `NameError` class that crash-looped the scheduler on 2026-07-28.

Verified in production at 12:09: *118 minutes since last real message → WOULD FIRE*; blocks at 12 minutes idle, proceeds at 75.

## 3. The sync script re-added everything it had resolved

Dedup keyed on "does this timestamp appear anywhere in `DEV_BACKLOG.md`" — so the moment an entry was curated out of Inbox, the next sync brought it straight back. Every resolved item would have resurfaced forever. Hit it immediately on closing the check-in cluster. Replaced with a `.dev_backlog_seen` ledger that decouples *pulled* from *still written down*.

Also fixed at deploy time: the script defaulted to `http://` on the raw Tailscale IP. **The server runs HTTPS** behind a Tailscale cert. Because the script fails silent by design, it would have reported `0 new` forever rather than erroring.

## 4. Ten legacy requests recovered

Crawled `data/personas/mike/conversations/2026-08-0{1,2,3}.jsonl` and the quality-event stream for asks predating automatic capture. Notable: check-ins during live dialogue; repetition of pending items; over-indexing on one disrupted night; *"stop telling me to enjoy things"*; calendar delivery; transcription timeouts; dictated email errors; transcript line length; and a request to act on an external website — which carries a real security surface, since the same message handed over an email, postal address and phone number.

The 2026-08-01 timestamp request turned out to have been closed by the SEQ 008 fix the next day — filed under Done, not reopened.

## 5. Persona config: the VM owns it

**I was about to add a persona push to `deploy.sh`. It would have been destructive.**

`write_persona()` and `write_config()` edit those files *on the VM* at runtime. The VM's `mike.md` already held five interaction preferences Synth had recorded that morning — the route-1 mechanism working on a real conversation — which the Mac copy had never seen. A push would have erased all five.

So the fix is directional, not a closed gap:

| Direction | Mechanism | When |
|---|---|---|
| Mac → VM | one-off `scp`, deliberately | authoring a genuinely new file |
| VM → Mac | `scripts/metatron-backup.sh` → `backups/vm/` | routine |

- Stale Mac copies moved out of `config/personas/` (retained under `backups/`, and present in the 12:16 VM pull). Only git-tracked dev personas remain, which are never written to at runtime. Silent no-op edits are now impossible because the files aren't there.
- `deploy.sh` carries the reasoning at the exact point someone would add the push; CLAUDE.md documents both directions.
- `.claude/commands/*.md` is now **tracked** — project tooling, no personal data, and being ignored already cost one file that survived only in a chat transcript. Needed `.claude/*` rather than `.claude/`, since git will not descend into an excluded directory and a later `!` rule never matches.
- **Secrets:** a `.env` backup with live keys was sitting in the repo directory (moved to `~/.metatron-secrets-backup`, 0700/0600), and `.env` itself was mode **0644** — now 0600.

## 6. Identity data — over-corrected, then corrected properly

The contact details Mike gave while asking for a booking had been filed into `mike.md` under an invented `## Contact Information` heading, so they rode in **every** system prompt. Moved on the VM into `profile.yaml` under a `contact:` block that `load_profile()` deliberately does not render.

Then I restricted `write_persona` to a section whitelist to prevent recurrence — **and broke the actual requirement.** The user pushed back correctly: users give biographical data in conversation and the tool must capture it; Synth, Logistics and others need access to do their jobs. Reverted (`8659c4d`).

**Built the real answer** (`35e53ee`) — `tools/profile.py`:

| Where | What |
|---|---|
| `profile.yaml` | stable facts about who the user is — **new** |
| `{persona}.md` | how they want to be dealt with |
| `context.json` | this week's threads |

Read is a separate tool from write on purpose: `load_profile()` renders a summary into every head-layer prompt, and the contact block is excluded from it. Agents needing a value (Logistics booking, Physical Health checking a standing condition) call `read_profile` at the point of use. Verified: email/phone/address absent from the rendered prompt, occupation present.

Granted to synthesizer, logistics, physical_health, relationships, work_vocation and finance — in **both** routing files so they cannot drift. Unknown fields are refused rather than absorbed, since an invented key is exactly how `mike.md` acquired a section no code knew about.

---

## Deferred — the Rule Redundancy plan (agreed, not started)

The user asked to commence all four. Live debt exists: their five complaints currently sit in **both** `mike.md` (Synth self-applied them) and `synthesizer.md` (added the same afternoon), and nothing detected the overlap.

1. **Repeat-detection** — a repeated instruction is evidence a rule isn't working, not a new rule. Highest value; it is what would have caught *"once again, you're making too much of the sleep disruption."* Today Synth would simply write it twice.
2. **One home per rule class**, documented and checkable.
3. **Promotion deletes the original** — when a dev session generalises a persona rule into an agent file, remove the persona copy in the same pass. Has live debt now.
4. **Reconciliation script** reporting overlaps and contradictions across persona file, agent files and scheduler prompts.

## Also open

- **No `write_profile` for the *user*'s own confirmation loop** — capture is silent; there is no review of what has been stored about them.
- Data breadth remains the root cause behind the sleep over-weighting; the `synthesizer.md` rules are mitigation only.
- The `SessionStart` hook now runs the backlog sync (0.99s reachable, 0.11s with the VM down) after being declined earlier and then requested.
