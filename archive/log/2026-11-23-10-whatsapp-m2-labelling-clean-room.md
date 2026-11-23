### 2026-11-23 (WhatsApp M2, clean-room — the labelling tools were built and the sample exported; Mike dropped M2 as the gate before any score: real use is the baseline) — **`067b0bc`, pushed; nothing to deploy** (probe is phone-only, the script Mac-only)

**Incoming handoff:** `archive/handoffs/2026-11-23-whatsapp-m2-labelling-prep-prompt.md`. Clean-room rules held:
- no transcript opened;
- WhatsApp log entries read only in fragments titled "clean-room";
- no crypt implementation, no web;
- **no message text, contact name or number entered this conversation.** The export was never read. Two stray files in Downloads were identified by counts-only checks, and the one read in full is the probe's counts-only report.
- The write-time briefing on `SESSION.md` injected excerpts of other fragments (Iva onboarding, the goal network, two clean-room ones). No WhatsApp reference-reading entry was among them.

**Built (Amber/Green; committed `067b0bc` after Mike's own test run passed):**
- **Probe button 8, "Export a labelling sample".** `ProbeM2Sample.java` (platform-free) and `ProbeM2Run.java`, with `ProbeActivity`/`ProbeStore` wiring.
  - It draws about 200 received text messages from the last 30 days: Cyrillic ≥ 30, kinds in proportion, **≤ 15 per chat** (Mike).
  - Rows carry n/kind/time/text only. The share sheet goes through the existing FileProvider `cache-path`.
  - The sample is swept at the next launch after 15 minutes. `ProbeM2SampleTest` 6/6; the waprobe suite passes.
- **`scripts/whatsapp_m2_label.py`.** Calls `intake_whatsapp._analyse` directly, with a neutral "Contact" entry. The verdict is shown first (Mike's choice, accepting the anchoring).
  - The answer key is shown at every question (Mike). The resume file holds no text. Supports `--rescore`.
  - It refuses without the translation model, prints a numbers-only summary, and offers deletion (default yes).
  - A `p` answer (a proposal with a time) is the ground truth for the one-to-one hard gate. Without it, the gate could be checked only against our own typing, where it can never fail.
  - `tests/test_whatsapp_m2_label.py` 10/10. `qa_sweep` 12/12. Waprobe APK built and served (sha `7f763f8a`) and installed.

**Rulings:**
- Transport (a): no ids, Taildrop.
- Bar set before labelling: recall ≥ 95% (*"let's aim for 95% and see how it goes"*), no miss on a one-to-one proposal with a time, precision ≥ 60%.
- **Then dropped:** *"there's not enough information … I don't want to predicate on my message history. Let's run the tool and see how Metatron would handle things, then adjust from that baseline."* Recorded in plan § 4. The bar is void.
- Earlier, Mike refused labelling inside this chat: about 200 third-party texts would go to Anthropic's API and sit in the session log and the transcripts.

**Why a no-ids sample could not decide it:**
- Need depends on the thread. "Have a great day" needs a reply as a sign-off, none as an answer to "talk to you later". The per-chat last-reply time is a candidate signal (unbuilt).
- A reply-need is moot until Metatron can reply on WhatsApp.

**Found:** the window held **0 Cyrillic** of 1,054 received messages with text (330 one-to-one, 724 group; 37 chats sampled; 0 live increments). Ruling D's translation path has nothing to be measured on. Bulgarian in Latin letters would pass as English; Mike was told, and nothing was asked for.

**Wrong at first:**
- The first Taildrop arrival was the probe report shared as text, not the sample. Tailscale names shared text with a hash `.txt`.
- The labelling export's shape check found 0 rows in it.

**Rejected:**
- Labelling in chat (privacy).
- A batch mode (Mike chose the script as is).
- A names-included re-export (more exposure; to be weighed only if skips exceeded 1 in 5).

**Deleted:** the export and its resume file (11-23). Button 8 and the script are kept for re-measuring.

**Next for WhatsApp:**
1. The Fable review of `src/main/…/whatsapp/`.
2. **Phase 2** (the phone posts; nothing reaches the VM before it).
3. M4.

**Ruled at close (Mike):** a "this should have come up" action, now the only measure of misses, is built into Phase 2 (~0.3–0.5M tokens): *"Build it in."* `tests/test_whatsapp_m2_label.py` re-run by Mike in his own terminal: pass.

**The post-deploy intake check is still unsettled — not failed.** Mike's run showed scheduler starts at 13:27 and 14:01 and no sweep: the VM's code counts "every 60 min" from each start, so the 14:01 deploy reset it. Another window holds an uncommitted on-the-clock fix in `core/scheduler.py`. Same check the Phase 1 chat is owed. Re-run after 15:05 with no deploy in between.

**Other commits this session:** `edf2d14` (the Phase 1 deploy chat's uncommitted deploy record, committed on its own after it sat idle half an hour), `cb057c8` and a follow-up (this close-out).

**Next prompt:** `archive/handoffs/2026-11-23-whatsapp-phone-reader-fable-review-prompt.md` (Fable 5.2, read-only) — the gate before Phase 2.

