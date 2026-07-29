# SEQ 026 Chat Rehydration and Persona Goals Gap Audit
**Date:** 2026-07-27 (archived 2026-07-28)
**Session type:** Discussion / research — no code or config edits

---

## What was investigated

### 1. Locating the open-ended "Metatron — Single Exchange Troubleshoot" chat
Five transcripts share the title "Metatron — Single Exchange Troubleshoot" (all 2026-06-26). Compared endings across all five:

- Base (SEQ 026, session `b8009cf4`) — closed via "Archive this chat"
- (2) SEQ 031 (session `054ccb99`) — closed via "Archive this chat"
- (3) SEQ 032 (session `a88b06b0`) — closed via "Archive this chat"
- (5) SEQ 041 (session `4d2ac3bb`) — closed via "Archive this chat"
- **(4) SEQ 026 duplicate (session `f37f081a-693d-4b82-bdcb-b7d6d163b392`)** — **never archived.** Ends mid-thread: user said "Let's address the calendar event now. I don't think this has been built yet," investigation found `tools/caldav.py` is fully built but `config/modules/caldav.yaml` has `enabled: false` and empty credentials. Last message asks which CalDAV service Mike uses (iCloud/Google/Fastmail/Nextcloud) and flags the hardcoded `America/New_York` timezone needing to become `Europe/London`. This is the thread being continued.

Full original prompt template confirmed identical across all five instances (verified against transcripts 2, 3, 5) — the diagnostic script + "what to look for" checklist is reusable boilerplate; only the task-specific line at the top varies per chat.

### 2. Google account setup for CalDAV
User asked blank vs. duplicate-of-existing Google account for a London base (email/calendar/contacts).
**Recommendation given:** blank account — avoids porting US-tied metadata (timezone history, ad profile, saved places); UK region/language set at creation gets correct defaults for free. Contacts/calendar are the only things worth porting (vCard/ICS export), not a full clone. Clarified Claude cannot create the account itself (browser + phone verification required) — user must do that step; Claude can handle `caldav.yaml` config and testing once it exists.

### 3. Value of old account data for jumpstarting Metatron
Reviewed `SESSION.md`, `config/mission.md`, `tools/caldav.py`, `tools/crm.py`, `config/goals.yaml`. Conclusion: **low value, works against the design.** `CLAUDE.md`'s "hypothesis not verdict" principle means goal/relationship data is meant to emerge from Metatron's own interviews, not be inferred from an account history dump. Contacts import is the one low-risk exception (saves typing; CRM's real payload — frequency preference, relationship context — still needs a conversation). No email ingestion tooling exists yet, and any future one would need `<untrusted_content>` wrapping per the deferred indirect-injection section of `CLAUDE.md`.

### 4. Mike persona goals audit
Checked `config/personas/mike.md`, `config/goals.yaml`, `data/baselines/aspirational_baseline.json`, `data/personas/mike/context.json`.

**Gap found:** `mike.md` only carries interaction preferences and a "Goals interview completed 2026-06-26" flag — no goal content. `goals.yaml` (the Tier 3 structured store meant to drive quarterly/weekly/daily tracking) is **still empty** despite the interview being marked complete. The interview's actual qualitative output (good/hard week, peak/floor days) landed in `aspirational_baseline.json` instead — which also has a bug: `"persona": ""` (untagged). Session-level open threads/patterns (Finance pipeline dev, Bulgarian learning, reading list, family routine consistency, health/fitness priority) live only in the ephemeral `context.json` tracker, not durable storage. This matches the pending **A5b** item already flagged in `SESSION.md` (re-run `write_aspirational_baseline` with real interview data) — but there's no equivalent step scoped to backfill `goals.yaml` itself.

---

## Decisions / deferred

- No edits made this session — analysis and discussion only.
- **Deferred to user:** whether to populate `goals.yaml` from `aspirational_baseline.json` + `context.json` content (offered to draft candidate entries for review, not yet actioned).
- **Deferred to user:** create the (recommended blank) Google account; CalDAV config (`config/modules/caldav.yaml`) can be completed once the account and app-specific password exist.
- **Not yet fixed:** `aspirational_baseline.json` has `"persona": ""` — should be tagged `"mike"`.
- A5b (re-run `write_aspirational_baseline`) remains open per `SESSION.md`; this session surfaced that `goals.yaml` backfill is a related but separate gap not yet on the roadmap.
