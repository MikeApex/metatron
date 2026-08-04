# 2026-08-03 — Context-file audit: SESSION.md split, cold-start trim, `/archive` command

*Status: complete. Written early per the session-logging rule; updated as work landed.*

**Outcome: cold-start load ~88k → ~28k tokens.** A live test run, audited from its JSONL, passed every check. Commits `403ecb9`, `7599ed8`, `c4d2c4d`, `3a17f1a`, `b6543f7` — docs and `.claude/` only, **not deployed**.

---

## Why this session happened

User asked how large `SESSION.md` was. Answer: **775 lines / 126,466 bytes / ~31.6k tokens** — far past the "readable in under 2 minutes" target its own convention sets in `CLAUDE.md`.

Pulling that thread found the problem was not one file. Six context files had accreted overlapping jobs with no rule about which owns what. The project already has a doctrine for exactly this failure — `CLAUDE.md` → **One Home Per Rule Class**, written 2026-08-03 — and it had never been applied to the project's own context files.

Scope was expanded twice by the user: first to cover the whole archive protocol and `/metatron-code`, then to a full audit with a nuanced recommendation rather than a byte-count-driven trim.

Approved plan: `~/.claude/plans/yes-the-purpose-of-parallel-glacier.md`.

---

## Audit findings

**Cold-start load measured at ~88k tokens** before the user types anything — roughly 44% of a 200k window.

| File | Loaded | Bytes | Tokens |
|---|---|---|---|
| `CLAUDE.md` | auto, always | 50,706 | ~12.7k |
| `MEMORY.md` + memories | auto, always | 7,721 | ~1.9k |
| `SESSION.md` | `/metatron-code` | 126,466 | ~31.6k |
| roadmap `phase5_to_future_*` | `/metatron-code` | 94,122 | ~23.5k |
| `DEV_BACKLOG.md` | `/metatron-code` | 48,973 | ~12.2k |
| `CODEBASE_INDEX.md` | conditional | 22,675 | ~5.7k |

1. **Four files are 60–80% history, not state.** `SESSION.md`: 620 of 775 lines are 44 `### Also done <date>` sections. `CLAUDE.md`: the Deployment Infrastructure section is 27,308 of 50,706 bytes — **54% of a file auto-loaded into every session**.
2. **Agent enhancement backlogs stored three times** — 9 agent files, roadmap Section 4, and 15,851 bytes of `DEV_BACKLOG.md` (32% of the file) under a heading admitting *"These are mirrors, not moves."*
3. **Two sections named "Key design decisions" with different contents** — `CLAUDE.md` 5 bullets, `SESSION.md` 7, none shared verbatim.
4. **The binding privacy ruling has eight homes**, with nothing marking which is authoritative.
5. **`CLAUDE.md`'s decisions list names a provider and has been wrong twice** — says "Claude API" when the runtime is Vertex Gemini. Rewriting it to say "Vertex" would be wrong again: the local path is live (`core/router.py:43` branches on `DEPLOYMENT_MODE` at call time, `run_session_ollama()` intact, only two non-vendor files mention Vertex). → **Decision-level statements never name a provider.**
6. **Archive protocol is two conflicting documents and two divergent scripts.** Global `~/.claude/tools/archive_chats.py` (353 lines) vs project `tools/archive_chats.py` (295 lines), both writing to the same directory. Diffed: global is a **strict superset** — zero project-only functions. Project copy is a stale ancestor.
7. **Backlog reads 97 open; only 24 are real.** 70 of 94 open bullets are the mirrored agent section.

**One claim of mine corrected mid-audit:** I said `archive/transcripts/` (132 MB) was carried by every clone and VM pull. It is not — already gitignored, 0 files tracked, `.git` is 9 MB. `daily-backup.sh`'s exclude list doesn't cover it, so it *is* in the daily encrypted backup. Nothing to fix.

---

## Decisions made

- **`archive/PROJECT_LOG.md`** (new, append-only) takes the dated history. **`SESSION.md` is replaced each session; the log is appended.** This split is the anti-regrowth rule — without it the file returns to 700 lines.
- **`docs/INFRASTRUCTURE.md`** (new) takes recreate-from-scratch, outage runbooks, Android build. Split line is *what a coding session acts on* vs *what a recovering session needs* — not "reference vs operational".
- **Three things stay in `CLAUDE.md` regardless of byte count**: the persona VM-ownership rule, the external-IP "looks removable and is not" trap, and the billing caps table. Test applied: **anything that must fire unprompted cannot live in an on-demand doc.**
- **`/archive` becomes a real slash command** — the ritual was 4 steps described in two disagreeing documents, triggered by typing a phrase.
- **Rolling handoff paragraph kept** as a deliberate design feature: one paragraph, rewritten not stacked. Four of the five current paragraphs contain a *correction* to a previous one — which is exactly what a status table flattens away.
- **Scope: ~38k this pass, second pass on evidence.** This pass removes only duplication and history — no judgement calls about what's still live.

---

## Work log — complete

| File | Before | After | Change |
|---|---|---|---|
| `SESSION.md` | 126,466 | 16,111 | 775 → 170 lines; history moved out |
| `ROADMAP.md` *(new, abridged)* | 94,122 | 46,746 | full plan untouched at `archive/plans/` |
| `DEV_BACKLOG.md` | 48,973 | 30,085 | mirror deleted, `## Done` moved, 11 items filed |
| `CLAUDE.md` | 50,706 | 44,127 | Deployment Infrastructure 27,308 → 16,100 |
| `CODEBASE_INDEX.md` | 22,675 | 22,771 | archive-script row corrected |
| **Cold-start total** | **350,663** | **167,561** | **~87k → ~41k tokens (52%)** |

**New files (not loaded by default):** `archive/PROJECT_LOG.md` (120,830), `docs/INFRASTRUCTURE.md` (20,131), `.claude/commands/archive.md`.

- [x] Step 1 — triage extraction table, user-reviewed
- [x] Step 2 — `archive/PROJECT_LOG.md` — **verified byte-identical**, 13,336 words both sides
- [x] Step 3 — `docs/INFRASTRUCTURE.md`
- [x] Step 4 — `SESSION.md`, `CLAUDE.md`, `DEV_BACKLOG.md` rewritten; **roadmap left untouched** (see correction below)
- [x] Step 5 — `/archive` command; `tools/archive_chats.py` deleted; both `CLAUDE.md` protocols updated
- [x] Step 6 — `/metatron-code` updated; parsed anchor preserved and re-verified
- [x] Verification — **17/17 cold-start questions pass**; all links resolve

### User corrections during execution

1. **Do not trim the roadmap.** It is a dated, static plan document — editing it rewrites the record. Correct approach: leave it intact and create an abridged live copy. `ROADMAP.md` (root) now carries the binding privacy ruling, open Track A (A7/A8), all of Track B and Track D, phase gates and pre-Alpha streaming items; it names explicitly what it does not carry (Tracks C/E/F, completed A1–A6, Section 4 mirror) and points at the full plan for those.
2. **The abridged file was suggested, then deferred by me.** Corrected — built in this session, not left to a second pass.

### Verified, not assumed

- All 45 dated headings from old `SESSION.md` present in `PROJECT_LOG.md`; 55 of 55 headings accounted for across the split.
- All 9 agent files still carry `## Enhancement backlog` (77 lines) — checked *before* deleting the `DEV_BACKLOG.md` mirror.
- `archive_chats.py`: global copy is a **strict superset** (zero project-only functions) — the project copy was a stale June 19 ancestor.
- The `## Read these before doing anything` anchor that `/metatron-code` parses is byte-identical apart from the intended roadmap repoint.

### Live test run — audited, passed

Session `998a7b0f`, four real questions after `/metatron-code`. Audited with
`scripts/audit_context_load.py`:

- ✓ `SESSION.md` and `ROADMAP.md` read; the 94 KB static plan **not** read — the parsed anchor held, which was the failure mode of most concern
- ✓ `CODEBASE_INDEX.md` correctly skipped
- ✓ **no file the session had to go find** — nothing was cut that it needed
- ✓ answered the billing question completely *and* cited `docs/INFRASTRUCTURE.md` for the runbook **without opening it** — trigger-adjacent pointers working as designed
- ✓ surfaced a pre-sign-off gate at `ROADMAP.md:113` that neither the audit nor the 17-question acceptance test had listed: prefix-caching moved dynamic context out of the system prompt, so the **A4 clinical-flag hard-fails must be re-run against the new assembly order before A7 sign-off**

Two auditor bugs found and fixed by this run: slash-command invocations read as "NO" (the
`<command-name>` wrapper is the same one used to filter system-injected text), and the
`38 open` vs `32` discrepancy — both counts correct, different denominators
(`sync_dev_backlog.py:162` counts every `- ` line including sub-bullets and Inbox).

### Post-test change

**`DEV_BACKLOG.md` removed from the `/metatron-code` autoload** (user's call). It is a work
queue, not project context — ordinary coding takes its task from the user, not the list. The
sync step stays because it writes to disk and costs no context, so the file stays current
whether or not it is read. `/metatron-code` load 91,985 → 61,900 bytes (~22k → ~15k tokens).
This also exposed that `CLAUDE.md`'s Mandatory Pre-Edit Context Check still named the static
plan rather than `ROADMAP.md` — the rule governing every edit in the project, now corrected.

### Second pass — 2026-08-04 (`a5ba388`)

Run after the live `/metatron-code` test audited clean. **Cold start 28k → 26k tokens; 69% below
the original 350,663-byte baseline.** 16/16 checks pass, all links resolve.

| File | Pass 1 | Pass 2 |
|---|---|---|
| `CLAUDE.md` | 44,569 | **40,172** |
| `MEMORY.md` | 7,721 | **7,070** |
| `SESSION.md` | 12,789 | **12,010** |
| `ROADMAP.md` | 47,220 | 47,220 — deliberately untouched |

- Phase Review + Phase Testing conventions → [docs/CONVENTIONS.md](../../docs/CONVENTIONS.md).
- Directory Layout condensed; `CODEBASE_INDEX.md` already does file-level.
- Deployment Infrastructure 16,100 → 14,323 — tightening *first-pass* prose, not moving more out.

**The size rule was wrong.** *"If `SESSION.md` is longer than before, something went in the wrong
file"* is a ratchet — it can only shrink, eventually paring away what's worth keeping, and it
penalises a session for recording a new blocker. **Replaced with a 200-line ceiling**, fixed in
all four places that stated it. User's correction.

**Memory audit, 43 → 39 files. Two were actively wrong, not merely stale:**
`feedback_archive_chats` pointed at `tools/archive_chats.py` — **deleted by this same work**, so
it would have sent a future session to a dead path. `feedback_archive_verbatim_timing` still
mandated the manual `.txt` the protocol had dropped. Three superseded deleted;
`project_gcp_billing_infra` rewritten to *point* at `CLAUDE.md` rather than restate a threshold
that has changed five times.

**`ROADMAP.md` Track D (~14 KB) deliberately not trimmed** — a parallel window committed to it at
00:22 the same day, and the A4 gate filed from this work had already been cleared by that window
(`b3229ff`, PASS 6/6). Live territory. The A6 slip in pass 1 is the warning about trimming that
file by line range.

**Recommendation on the record: stop here.** What remains loaded is load-bearing.

### Known limitation carried forward

One pre-existing dead link — `archive/sessions/2026-07-28 — Persona Unification Plan and Phase 0.md` — was already broken in the original `SESSION.md`. Preserved verbatim in `PROJECT_LOG.md` rather than invented a target for.

---

## Deferred

- Roadmap split into live-tracks + full (would reach ~20–25k) — wants cold-start test results first.
- Dropping `CODEBASE_INDEX.md` from the default load.
- Memory files (43) restate several consolidated rules — separate system, untouched.
- Whether `.claude/commands/` should be force-added to git. It is gitignored entirely, so `/archive` and `/metatron-code` have no backup; `/metatron-troubleshoot` was already lost once this way.
