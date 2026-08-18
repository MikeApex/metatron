---
paths:
  - "SESSION.md"
  - "ROADMAP.md"
  - "DEV_BACKLOG.md"
  - "CODEBASE_INDEX.md"
  - "CLAUDE.md"
  - "archive/**"
  - "docs/**"
  - ".claude/commands/**"
  - ".claude/backlog_inbox/**"
---

# Project records — which file holds what

Relocated from `CLAUDE.md` on 2026-08-14, in full.

**`paths:` is enumerated deliberately, never `*.md`.** That pattern would match every plan, every
archive read, every agent file and the other rule files — making this de-facto always-on, which is
the thing the split exists to prevent.

One job per file. Written 2026-08-03 after an audit found six context files with overlapping jobs
and no rule about ownership — `SESSION.md` had reached 775 lines, 80% of it history.

| File | Owns | Written | Loaded |
|---|---|---|---|
| `CLAUDE.md` | how to work here: rules, conventions, architecture | edited | auto, every session |
| `.claude/rules/*.md` | area rules and their full rationale | edited | on read of a matching path |
| `SESSION.md` | **current state only** | **replaced** | `/metatron-code` |
| `DEV_BACKLOG.md` | **Metatron** work outside the roadmap, in priority order | `## Inbox`/`## Machine log` machine-written, rest curated — ritual in `/backlog` | **on demand** — synced every session, read only when working the backlog |
| `ROADMAP.md` | **live** tracks, phase gates, freezes — abridged | edited | `/metatron-code` |
| `archive/plans/phase5_to_future_roadmap_2026-06-10.md` | the full plan — completed tracks, Phase 6B/7 detail | **never edited — it is dated and static** | never — read when `ROADMAP.md` says it does not carry your area |
| `docs/WORKFLOW.md` | which command to fire, when, and what it costs | edited | never — read when unsure which ritual applies |
| `docs/CONVENTIONS.md` | phase review/testing, file naming, **adding a module, the tool pattern, model-ID maintenance** | edited | never — read when doing one of those |
| `docs/INFRASTRUCTURE.md` | **all** deploy/VM/Vertex/Tailscale/systemd/billing/env/APK detail, outage runbooks | edited | never — consult when deploying or recovering |
| `CODEBASE_INDEX.md` | where things are | edited | on demand |
| `archive/PROJECT_LOG.md` | dated history, reasoning, rejected options | **appended, never rewritten** | never — consult deliberately |
| `archive/backlog_closed_YYYY-MM.md` | closed backlog items with the evidence that closed them | appended, rolls monthly | never — consult before re-filing anything |
| `archive/sessions/` | **historical — pre-2026-08-09 per-session writeups** | no longer written; the log entry replaced it | never |

**The rule in one line: `SESSION.md` has a 200-line ceiling.** Below it, grow freely — recording a
new blocker is exactly what it is for. Crossing it means history is accumulating in the primer
instead of the log. (It hit **775** before the 2026-08-03 split.)

History goes in the log; state goes in `SESSION.md`; work goes in `DEV_BACKLOG.md`. A session that
closes by *appending* to `SESSION.md` has put it in the wrong place — see `/archive`.

---

## Where a new lesson goes

Root `CLAUDE.md` is no longer the default destination. The question is: **what is the smallest set
of files this lesson governs?**

| The lesson governs… | Goes to | Loads |
|---|---|---|
| A specific file's past (this exact file was broken once) | an `archive/log/` fragment | surfaced automatically by the write-time briefing |
| One area (agent files, personas, deploy, records) | the matching `.claude/rules/*.md` | on read of that area |
| A repeatable procedure | a skill / `.claude/commands/` file | on invocation |
| Everything, and it is dangerous to get wrong | root `CLAUDE.md` — **and it must earn a line against the 200 ceiling** | always |
| Nothing anymore (the cause was fixed) | the fragment only | never — it is history |

The standing question for the last row but one: *would removing this cause a mistake in a session
that isn't touching any particular area?* Almost all scar tissue answers no — it is area-specific,
which is why it now has an area to go to.

**Rationale travels with the rule.** A rule in `.claude/rules/` carries its full incident narrative
because it is paid for only by sessions in that area — but **not without limit**: when the rule
fires, the *entire file* injects, so a 400-line rule file recreates the adherence problem for
exactly the highest-stakes sessions. That is what the ceilings below are for. Compression pressure
is what has been mangling rationale; removing it from the always-on tier is the point, not removing
the ceiling.

---

## The single-bin rule

**`DEV_BACKLOG.md` is the single bin for *Metatron* work outside the roadmap, and `/backlog` is how
it is worked.** A second bin may be opened only for one named build, with a stated retirement
condition, and it closes with that build — a backlog that outlives its build has become a second
permanent bin, which is what this rule exists to prevent. **No standing second file.**
*(The one instance, `HARNESS_BACKLOG.md`, 2026-08-13 to 08-14: `archive/PROJECT_LOG.md`.)*

1. **No item is acted on, or re-filed, on the strength of its own description** — open it against
   the current code first. A sweep on 2026-08-05 found roughly a third of checked items stale:
   causes already fixed, cited functions that no longer existed, line numbers hundreds of lines
   out. The cost is not the wasted check. A stale premise *argues for the wrong decision,
   persuasively* — that day one produced a well-reasoned recommendation to hold a tool grant
   pending work that had shipped two days earlier.
2. **File only what a user would notice or what blocks the roadmap.** An incidental nit is fixed on
   the spot or dropped. Between 2026-08-03 and 08-09 the file grew 197 → 1,658 lines while three
   separate sweeps ran, because every session filed everything it saw and `/archive` had no step
   that closed anything. Both halves are fixed; the bar is what keeps it fixed.

---

## Ceilings

**Command files carry procedure, not history.** When an incident teaches something, the lesson goes
to `archive/log/` and the command gets at most a line. Crossing a ceiling is the signal to move
something out, not a licence to trim something useful.

The authority is `CEILINGS` in `scripts/check_claude_md_claims.py` — read the numbers there, not
from prose.

**`DEV_BACKLOG.md` is the exception: it is bounded by ITEMS, not lines** (`ITEM_CEILINGS` in the
same file; Mike's call 2026-08-15, applied 2026-08-18). Item count bounds the **workload** — which
is why `## Now`'s real cap was always its 10-item limit. A line count instead pressures a session to
cut *evidence* out of well-documented entries, and the evidence is the expensive half: no item is
acted on from its own description, which only works if the description says what was checked and
when. The 2026-08-18 inventory measured the real cause of growth — **finished work with no exit**,
11 of 43 items awaiting one ordinary use — which a line ceiling cannot distinguish from verbosity.

→ Which command to fire and when: `docs/WORKFLOW.md`.

---

## Chat archiving

**Run `/archive`.** Five steps — verbatim transcript, one project-log entry, `SESSION.md` refresh,
backlog close-and-file, and a commit of exactly those files — in `.claude/commands/archive.md` so
they are executed, not remembered. It should take minutes. The commit stages an explicit manifest
and pushes for offsite backup, but **never deploys**.

The one rule worth carrying in your head, because it is what keeps `SESSION.md` small:

> **`archive/PROJECT_LOG.md` is appended. `SESSION.md` is replaced.**
> Detail goes in the log; only current state stays in the primer. A session that closes by adding a
> new dated section to `SESSION.md` has put it in the wrong file.

**`PROJECT_LOG.md` is GENERATED** from `archive/log/` fragments — write a fragment, never edit the
log, and a fragment is the collision-safe half of `/archive` when two windows are live.

**Source of truth for transcripts:** `~/.claude/tools/archive_chats.py` (auto-detects the project
root). Run it mid-session at the trigger points in the global archiving protocol. Each run captures
everything written up to that moment, which is the intended result — **do not tell Mike the capture
is partial, that the tail is missing, or that it should be re-run after the session closes.** That
reminder fires on every run, so it distinguishes nothing.

*(No per-session writeup since 2026-08-09; `archive/sessions/` is history. Why, and how the global
`~/.claude/CLAUDE.md` five-step ritual reconciles with this one: `archive/PROJECT_LOG.md`.)*
