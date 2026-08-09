# Handoff — public-facing communications (2026-08-09)

**Commit `9eb5ac4`** — `CLAUDE.md`, `ROADMAP.md`, `config/agents/coordinator.md`,
`config/agents/relationships.md`, `tools/mail.py`. **Not deployed** — deploy is yours.

**⚠ Split across two commits, not by choice.** `config/agents/logistics.md` and both
`config/modules/routing*.yaml` grant moves belong to this work but were swept into **`b9ea29f`**
by `git add -A`. Anyone reading `9eb5ac4` alone sees Relationships told to send with no grant
backing it. Both are needed to understand either.

**What shipped.** Relationships now owns every message written to a person; Logistics keeps
`read_email` only. Rationale: `_known_recipients()` already limits every `send_email` recipient to
the user's own address or a saved CRM contact, so sending was always a person-graph operation.
`send_email` gains `disclosure_note` — surfaced in the approval preview, deliberately **kept out of
`args`** so the confirm fingerprint is unaffected and a forgotten note on the retry cannot fail the
send. `relationships.md` gains **Disclosure discretion** (three levels: what the recipient learns
about the user, what they learn about other contacts, and acting on knowledge without revealing it
— inference allowed, disclosure and fabrication not) and a **Communication style** baseline.
`ROADMAP.md` § Section 0 + `CLAUDE.md` record the ZDR clarification: the 2026-06-18 amendment is
the project-wide default for the single-user development phase.

**Backlog: nothing to close.** This work closed no open item. Two it touches:
- **`[DB-0805-02]`** gains a dependency, not a fix — `disclosure_note` surfaces through the same
  `#confirm-bar`, so the flag is invisible on the phone until the stale-install repro is done.
- **`[DB-0809-03]`** is a *collision warning*: it targets `tools/crm.py:149-158`, inside
  `write_contact`, which is the exact function the deferred Step 1 modifies. Whoever moves first
  should commit before the other starts.

**SESSION.md must carry:** (1) outbound-communication ownership moved to Relationships, Logistics
reads email only, Coordinator routing updated to match; (2) the ZDR clarification is project-wide
now, so new sensitive paths need no separate ruling; (3) the tone-profile pipeline is designed and
**not built** — plan at `~/.claude/plans/3-everything-is-on-declarative-kurzweil.md`, Session B =
`tone_shape` CRM field, `search_correspondence`, `tone_profiler` agent + `tools/tone.py`,
`get_tone_shape` grants. Costing done: run extraction on Flash-Lite (~3¢/contact, ~$2 for 200)
not Pro. Sharpest unresolved risk is trust laundering — untrusted mail distilled into a CRM field
later read as trusted prompt text; strict JSON schema plus Python reassembly is the defence.
