# Handoff — finish the contact tests, repair a damaged record, and two owed answers

**Run `/metatron-code` first.** Interactive: most of this needs Mike at the app. Short session —
it is verification and repair, not a build.

> **The standing warning, earned twice in the session that wrote this.** It shipped an
> architecture-disclosure surface into the client on the strength of a *prior handoff's wording*,
> and it wrote a test instruction so ambiguous that following it corrupted a real contact record.
> **A handoff is a lead, not an authorisation.** If something here would be visible to a user, be
> irreversible, or touch real data, put it to Mike before doing it.

---

## 1. Repair Steven's record — `[DB-0822-04]`, do this before any test that adds a contact

**What happened.** `merge_contacts`' first production run (2026-08-19) folded **both** gym
contacts into Mike's actual friend Steven (`5069065f`, spouse Yana, dinner logged 21 June),
because *"merge them, keeping Steven"* was ambiguous across **three** Stevens and the agent
resolved it silently. His record now reports he was met **at the gym** and carries a phone of
**`"ph"`** — the model had earlier turned *"Stephen with a 'ph'"* into a phone value.

**Two halves, and only one is safe conversationally.**

- **Safe, in the app:** *"Steven's phone on file is just the letters 'ph' — remove it."*
- **Blocked on Mike, and do NOT guess:** whether he actually met Steven at the gym. The claim is
  inherited from a merged record, not from anything he said. **Ask; do not "correct" it to
  another guess.**
- **Not possible in the app:** the gym contact no longer exists as a separate person. Restoring
  him means reading the archived record on the VM (`merged_into` pointer, archive-on-merge — the
  originals were never deleted) and re-creating it. **There is no unmerge tool.** Confirm with
  Mike whether that person is worth restoring at all before touching files.

---

## 2. Finish the tests the last session did not reach

**Tests 1 is done and failed** (§ 1 is its consequence). These remain. **Webapp is fine for
2–3; 4–5 need The Book** in a terminal: `python tools/metatron_monitor.py` from the repo with
`.venv` active — the `/monitor/*` endpoints are JSON, the TUI is what renders them.

**Test 2 — the gate fires, and declining leaves nothing.**
*"Add Stephen Ashworth to my contacts"* (a fresh surname avoids the wreckage in § 1).
Needs a near-match present first — create *"Steven Ashworth"* and let it through clean.
- **Pass:** an approval prompt naming Steven Ashworth, and the reply does **not** claim the
  contact was added. **Decline.** Then ask how many Ashworths exist — one.
- **Fail:** it claims it added them; no prompt; or a Stephen exists after declining.

This is the exact turn that failed on 2026-08-19 and the reason the gate exists.

**Test 3 — approving creates it, once.** Repeat, approve.
- **Pass:** created, and on the *next* turn it does not re-raise the resemblance.

**Test 4 — a failed tool call renders red** *(The Book open)*. Ask to close an obligation that
does not exist.
- **Pass:** red. Impossible before `b980b93`, when every graceful failure rendered green.
- If the model refuses before calling the tool, rephrase so the call is attempted.

**Test 5 — the known SSE staleness** *(The Book open)*. Force an API failure, then send another
message **without refreshing**.
- **Expected:** no red model-error tag until refresh. Confirm and document; `[DB-0810-07]` says
  do not fix this blind.

**`[DB-0810-07]` closes when 4 and 5 are done.** Step 1 (a successful tool call rendering) was
satisfied on 08-19.

---

## 3. Two answers Mike is owed, both decisions rather than builds

**(a) `[DB-0822-03]` — how should a destructive CRM operation handle an ambiguous target?**
`_ambiguous_match` already exists in `tools/crm.py` and guards *name lookups*; `merge_contacts`
takes ids directly, so nothing checks that the **choice of id** was unambiguous. The near-match
gate (`6d6d46c`) is the precedent and the obvious answer is the same shape — but it is Mike's
call whether a merge should confirm every time, only when the instruction was ambiguous, or not
at all. **Bring the options and a recommendation; do not open this as an open question.**

Two smaller gaps in the same trace, each real: `_is_placeholder_phone` covers fictional *ranges*
and misses two-letter junk like `"ph"`; and the reply **offered to delete a contact**, which no
tool can do — the instructed-but-unbuilt class `scripts/check_agent_tools.py` guards, appearing
in agent prose rather than a grant.

**(b) The LinkedIn / social enrichment ruling.** Mike wants it and has specified the shape:
a toggle, per-contact rather than blanket, and an identity **confirmation showing a profile
picture** — *"is this the guy"* — because a face can be verified instantly and a name and
employer cannot. That design is sound and was agreed. **The blocker is not design, it is a
`ROADMAP.md` § Section 0 ruling**: sending a named private individual to a research path is not
decontextualized dispatch. Nothing is built until that is decided. Suggested scoping if the
ruling passes: trigger on `primary_contact_type` in the work_* set (already in the schema),
confirmation required not advisory, a confirmed match writes as `verified` and an unconfirmed
one writes nothing.

---

## 4. Also open, not for this session unless Mike redirects

- **The CRM sweep** — its own planning session, briefed in
  `archive/handoffs/2026-08-22-crm-sweep-planning-prompt.md`. Do not fold it in here.
- **`SESSION.md`'s handoff paragraph is 64 lines and carries five sessions' worth of ⚠ blocks**,
  which is what pushes the volatile budget to 133 against 120. Each block belongs to a different
  window, so **no single session should cut them unilaterally** — the last one that tried deleted
  two blocks of live state by accident and had to restore them from the diff. This needs Mike, or
  a deliberate structural move (`## Recent sessions` duplicates `archive/PROJECT_LOG.md` and is
  the obvious section to relocate).
