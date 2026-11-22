Model: Opus 5.5 — a live walkthrough plus two rulings that need the clean-room rules held precisely; no code.

# WhatsApp Phase 0 — Mike's 25-minute walkthrough and the two rulings

Run **items 0, 2, 3, 4 and (optionally) 5** of
`archive/handoffs/2026-10-31-whatsapp-phase-0-close-survival-lm-increments-prompt.md` as a live
walkthrough with Mike — read that whole prompt first, including its clean-room rules (1–4), which
bind this session too. Prepare each step before he needs it; give exact taps, paths and the
pass/fail line for each.

A separate build session (`archive/handoffs/2026-11-22-whatsapp-phase-0-probe-build-prompt.md`)
writes the hook fence, the probe update and the APK. **Write no code, and make no edit at all
until the hook fence is in the working tree** — check with
`grep -n "reference-reading" scripts/hook_context_gate.py` before your first `Edit`/`Write`. Until
then the edit-time hook would brief you with session 1's reference-reading log fragment.

**Today, in order:**
1. **Item 0** — Mike deletes the `/private/tmp` reference copy (do not look there yourself); he
   confirms.
2. **LM ruling** (item 4) — needs nothing else; put it with the recommendation, record his answer
   and reason once the fence is in.
3. **Install** — when the build session reports the APK path, guide Mike's sideload over the
   current probe (confirm WA probe is still installed first; re-grant notification access if it
   was replaced). Then the **daytime smoke check** (item 1's last bullet): someone sends Mike a
   message while he watches; Refresh must show a line with `rx` filled and a delay of seconds.
   Fail → back to the build session before tonight.
4. **Increment test** (item 3) — Mike taps "5. Try newest increment" and sends the report over
   (Share → Tailscale → the Mac, `~/Downloads`). Read it, then put the **increments ruling**
   (item 4) on that result. On a narrowed 0a′: write its prompt for a separate session; its
   fragment title must say "reference-reading".

**Tonight → tomorrow morning:** item 2, the overnight survival test. Brief Mike before he leaves:
phone idle, Metatron not opened; tomorrow, ≥4 h idle and ≥2 h after the last Metatron push,
someone messages him in an unmuted one-to-one chat and notes the minute; he Refreshes and sends
the report within 72 h. Leave the session ready to resume for the read.

Record both rulings in the plan (§ 4 LM; the increments section) and the log. Close with
`/archive` after the survival read; the fragment title says **"clean-room"**.

**Budget:** ~0.1–0.2M Opus tokens; Mike ~25 minutes today plus ~5 tomorrow morning; someone
else for two planted messages. Run cost: none.
