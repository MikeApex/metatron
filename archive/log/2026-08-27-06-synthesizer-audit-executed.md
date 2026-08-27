### 2026-08-27 (the synthesizer audit executes: 52 KB → 41.5 KB, conduct injected not carried, and every agent sheds its backlog) — `core/orchestrator.py`, `config/agents/*` (11 files), `config/modules/synthesizer_{scheduled_sessions,onboarding}.md`, `AGENT_ENHANCEMENTS.md`, VM `scheduler.yaml` — **not deployed**

**The 2026-08-18 audit proposal was approved by Mike and executed, nine days after it was
written and after the caching fix had killed its cost case 4×.** The argument that carried it
was adherence: `synthesizer.md`'s own length is the documented cause of rules being ignored,
and six of Mike's six 08-21 complaints were rules already in the file. Landed: **52,397 →
41,939 bytes (~10.3k tokens)**.

**The plan's delivery mechanism turned out never to have existed.** ROADMAP § D2's context-file
pattern says content moves to `config/modules/` and loads "on demand via `read_agent_config` —
no code changes required." That tool reads the per-persona *data* store
(`data/personas/{p}/config/{agent}.json`) and has never read `config/modules/`. Mike chose the
replacement from three options: **code-conditional injection** — `session_kind()` generalised to
every configured schedule prompt, `_synth_conditional_sections()` wired into both pipeline
twins; scheduled-session conduct injects on any scheduler-originated turn, onboarding conduct on
`BASELINE_INCOMPLETE` in the package. **Rejected:** extending `read_agent_config` with a modules
fallback (grafts static instruction onto a sensitive per-persona store, relies on the model
remembering to call, spends an extra thinking round — the newly expensive side); and deferring
the move to the code-dominant rebuild (adherence pain is current, the rebuild has no date).
D2's claim struck through and corrected in `ROADMAP.md`; A8 gains the two new residents.

**Wrong earlier, corrected:** the audit handoff asserted `synthesizer.md`'s `## Enhancement
backlog` "survives verbatim" — the file never had one (verified against full git history).
Mike's ruling went further than the proposal: **all ten agents' backlog sections moved to root
`AGENT_ENHANCEMENTS.md`**, the single copy, indexed from `SESSION.md` and `CODEBASE_INDEX.md`;
known limit recorded there — `check_agent_tools.py` no longer scans those planned-tool names.
Also cut harder than planned: the Social outreach subsection *contradicted*
`relationships.md`'s stricter "no unilateral outreach, no exceptions" (One Home Per Rule
Class) — replaced with the tier row and a routing line.

**Found by probing mike's live scheduler.yaml: `companion_checkin`'s prompt was 9 chars**, under
the 20-char substring floor that guards against ordinary speech matching — so ambient check-ins
(the source of the 08-21 complaints) would have run without the conduct module on the package
path. Two-part fix: an exact-match fallback in `session_kind()` (a turn that IS the prompt is
the scheduler at any length), and the prompt reworded on the VM to 62 chars, kept door-shaped —
the file's own history warns a directive wording caused six same-day repeats of one item.

**Gates, all run:** `tests/test_synth_module_injection.py` 16/16 (new); evening-ritual gate
11/11; **A4 pipeline PASS 3/3** live; **B1 disclosure PASS 15/15** live
(`tests/security_redteam_2026-08-27_disclosure.md`); `qa_sweep` 9/9; `check_agent_tools` exit 0
(the `send_email` reword cleared the one live finding).

**Process corrections from Mike, both binding here:** the live gate runs' ~$3–4 cost was not
stated before running — expected cost gets said first from now on; and the Mac's
`VERTEX_CACHE_DISABLED=1` made every gate call bill full uncached input (~4× the VM's rate) —
that kill switch predates the sliding-TTL fix that bounds the storage risk it guarded against.
Mike is flipping `.env` to `=0` himself (the harness denies this session `.env` in both tool
families).

**Also this session, before the audit:** the `[DB-0822-01]` cache reconcile closed by running
it — five consecutive post-deploy days at 1.02×–1.17× billed÷estimated (bar 1.2×, from ~2.3×);
creation bills on the dedicated `Text Input Caching` SKU; `[DB-0820-01]`'s caps revert now has
its evidence for 09-01. Prose-tightening pass filed as `[DB-0827-06]`, non-urgent, Mike's
worked example applied in place.

**Deploy owed:** `core/orchestrator.py`, eleven agent files, two new modules, tests — the VM
prompt reword is live now, but the injection code that consumes it lands only with the deploy.
