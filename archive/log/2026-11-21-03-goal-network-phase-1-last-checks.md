### 2026-11-21, third (goal–task network phase 1's last two live checks — the prep followed its moved event; the redo question was asked but not recorded) — no code — **nothing deployed; one defect handed to the phase 2 chat**

**Incoming handoff:** log § 11-21 second — the Boots test event had been moved and a read-only
watcher was polling.

**Moved event: PASS.** About three minutes after Mike moved the Boots appointment 22→23 Nov, prep
`ob_261121_b205b1` was re-dated 11-21→11-22 ("its event moved"), its `moot_after` and start
followed, and it left the day's plan in a code repair ("calendar changed", then "a task left the
day") — no model call. Deleting the event closed it moot, "its event was cancelled".

**Redo question: asked, not recorded — a defect.** Mike created a two-step test plan on the VM,
dropped step 1 in the app (Drop opens a reason box and only acts on Save — the first attempt
stopped there), and step 2 closed `moot` and never appeared. Asked a neutral "anything you need me
to decide?", Synth raised it unprompted: *"Step 1 of the TEST B passport sequence was dismissed
earlier, which blocks step 2. Do you want step 1 reopened, or should that test sequence stay
dropped?"* But `cascade.raised` stayed `None`: `_SAID_SIGNALS["cascades"]` matches `reopen` only
as a whole word and has no `block`/`drop`/`dismiss`, so the question will be re-offered for up to
three days. **Handed to the phase 2 chat** (it is editing `tools/day_plan.py`): widen all three
signal patterns to stems, regression-test that exact reply, and consider stamping a cascade when
the reply names the step and asks a question. A word list was always the fragile half of `note_said`.

**Two more for phase 2's intake, found the same way.** Similar titles ("Prepare old passport…" and
"TEST B step 1 – find the old passport" — Claude Code's test naming caused the collision) made the
close gate refuse "dismiss the prep task" as ambiguous, and Synth twice narrated the system
("couldn't match the event description to the task title", "the exact task title wasn't
recognized from your phrasing") instead of asking which one Mike meant.

**Left:** re-run the redo check once the fix is deployed — fold it into phase 2's own live check.
The Boots chat task `ob_261121_e1e579` is still open (Mike's chat drop didn't take).

