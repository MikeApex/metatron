# 2026-08-08 — Memory Race Fix, MUST_SURFACE Decay, Whisper Eval

Three independent backlog items worked in one session (from a `/backlog-attack` cluster prompt).
All three complete. Deployed together.

**Commits:** `7c70cd9` (joint with the parallel cluster session — deployed, live-verified) ·
`08766bb` (deploy markers cleared) · `2195fa9` (backlog close-out).
**Reasoning, rejected options and corrections:** [archive/PROJECT_LOG.md](../PROJECT_LOG.md)
§ 2026-08-08 (memory cross-process race, MUST_SURFACE lifecycle, Whisper STT evaluation).

---

## Item 1 — `search_memory` JSON corruption (cross-process race) — **DONE**

**Root cause (pre-verified before session, confirmed here):** [core/memory.py](../../core/memory.py)'s
`_load_index()` / `_save_index()` did a non-atomic read-modify-write of
`data/personas/{p}/memory/metadata.json` with no lock. Both the server (via
[tools/logger.py:72](../../tools/logger.py#L72)) and the scheduler (via
[tools/diarist.py:76](../../tools/diarist.py#L76)) call `index_entry()` independently. The
single-worker `ThreadPoolExecutor` in [core/background.py](../../core/background.py) serialises
only *within* one process — which is precisely why this stayed invisible.

**Fix:**
1. `filelock.FileLock` around the load/save pair, scoped per persona. Already a pinned
   dependency (`requirements.txt`) — no new requirement. Embedding happens *outside* the lock;
   it is the slow part and touches no shared file.
2. Atomic writes — temp file + `os.replace` — so a lock-free reader never sees a torn file.
3. **Write order is load-bearing:** metadata first, then the index. The transient state is then
   index-old/metadata-new, where every index id still addresses a valid entry. The reverse
   order gives index-new/metadata-old and an `IndexError` in `search_memory`.
4. `search_memory` takes the lock too, so its desync repair can't race a writer.
5. **Self-repair for the damage already on disk:** `_read_metadata()` salvages the leading valid
   JSON document when the error is `Extra data` (the only shape this corruption takes), and
   `_load_index()` truncates an index/metadata length mismatch to the shorter of the two. The
   corrupt VM file heals on next read instead of needing a hand edit.

**Verification** — [tests/test_memory_concurrency.py](../../tests/test_memory_concurrency.py),
new. Spawns 4 real OS processes (not threads — a thread-only test passes against the broken
code) writing 12 entries each.

- **Against pre-fix code: reproduces the production error exactly** — all 4 writers died with
  `JSONDecodeError: Extra data`.
- Against the fix: PASS, 3 consecutive runs. Metadata parses, zero lost writes (48/48),
  index in sync, `search_memory` works, mode still 600.
- Salvage and desync paths unit-checked separately; both repair correctly and return the right
  entry for a query afterwards.

---

## Item 2 — `MUST_SURFACE` decay / resolution — **DONE**

**The finding (B1a red team, 2026-08-04):** an open `SUICIDAL_IDEATION` thread in
`sarah_chen`'s `context.json` caused all 15 unrelated red-team prompts to be answered with an
escalating crisis script. Worse than a stuck flag — it was **self-reinforcing**: the tracker had
recorded `"deflecting acute distress with system architecture questions"` as a *pattern*, i.e.
the file's own record of the contamination became the evidence for continuing it.

**Question put to the user, and the answer.** Asked whether `MUST_SURFACE` is an internal flag
destined for a next-of-kin escalation (⇒ permanent until administratively cleared) or the
simpler user-resolvable kind. Answered from the code: **there is no next-of-kin channel** —
`MUST_SURFACE` means "the Synthesizer must address this in the reply to the user, this turn";
the emergency-contacts store ([tools/wishes.py](../../tools/wishes.py)) is write-only until
Phase 6 and nothing can contact a third party. User's distinction (missed heart medication vs.
missed anti-psychotics) was kept anyway, as a tier split.

**Decision — the bug is prominence, not persistence.** Persistence is correct. Re-leading with
the crisis script on every unrelated turn is not. `status` separates them.

| Tier | Flags | Lifecycle |
|---|---|---|
| **2** | any `CLINICAL_CONCERN: *` | Never user-resolvable, never auto-expires. Reaches `watch` and stays there. `resolved` is **refused in Python**. Closing requires an administrative acknowledgment that does not exist yet — pre-wired for it. |
| **1** | bare `MUST_SURFACE` (`MEDICATION_MISSED_CRITICAL`, `CAREER_CRISIS`, isolation) | Closes when the underlying fact changes. |

**Rejected: time-based expiry (TTL).** Guaranteed to terminate, but a genuinely unresolved
crisis would silently disappear on a timer — the exact failure the flags exist to prevent.

**Implementation** — [tools/context_tracker.py](../../tools/context_tracker.py):
- New `clinical_threads` field: `{flag, tier, raised, status, last_surfaced, note}`, statuses
  `active` / `watch` / `resolved`. Backward-compatible (backfilled like `held_items`).
- **Tier is derived in Python, never taken from the model.** A model that mislabels a crisis as
  tier 1 could otherwise close it; the reverse error is harmless.
- **`raised` is carried over from disk**, so the model can't reset the clock each turn and make
  "this has been open a month" unanswerable.
- **Merge, not replace** — a thread omitted from a write is carried forward. Every other field
  on this tracker is replace-semantics; a clinical thread must not be deletable by omission.
- Refusals and status changes are **reported back in the tool result**, not silent.

**Honouring "don't clog the Synthesizer instructions"** (user's second answer): the lifecycle
protocol is **injected by the tool** — `read_context_tracker()` attaches `_clinical_protocol`
only when a thread is actually open. Zero cost in the normal case, impossible to miss in the
rare one. `synthesizer.md` gained ~3 lines, not a section.

Also wired through `persist_context_block()` in
[core/orchestrator.py](../../core/orchestrator.py) — the live path is the inline `[CONTEXT]`
block, not the tool call, so the field would have been silently dropped without this.

**Verification:**
- [tests/test_clinical_threads.py](../../tests/test_clinical_threads.py), new — **17/17 PASS**.
  Covers tier derivation, the tier-2 resolve refusal, the immovable `raised` date,
  carry-forward on omission, tier-1 resolution, conditional protocol injection, legacy files.
- **A4 regression gate (mandated by ROADMAP.md for any agent-file change): PASS.**
  `clinical` suite 3/3, `pipeline` suite 3/3, against `sarah_chen`/gemini.
  Reports: `tests/a4_safety_rerun_2026-08-08_gemini_clinical.md`, `..._pipeline.md`.
- `sarah_chen`'s contaminated tracker migrated to a single `watch`-state thread (gitignored,
  local test data only) — otherwise the contamination survives as plain strings the new
  mechanism cannot see.

---

## Item 3 — Voice transcription accuracy — **DONE (evaluated, `small.en` rejected)**

Full report: [tests/stt_bench_report_2026-08-08_vm.md](../../tests/stt_bench_report_2026-08-08_vm.md).
Runner: [tests/bench_whisper_stt.py](../../tests/bench_whisper_stt.py), new.
**Measured on the VM (e2-medium, 2 vCPU)**, as the item required — not the Mac.

| config | median | RTF | WER | vs base |
|---|---|---|---|---|
| `base.en` beam=5 vad=off *(was)* | 2.554s | 0.381 | 3.9% | 1.00x |
| **`base.en` beam=5 vad=on** *(now)* | **2.384s** | **0.361** | **3.9%** | **0.93x** |
| `small.en` beam=5 vad=on | 14.860s | 2.233 | 5.0% | 5.82x |

**`small.en` rejected on both axes.** RTF 2.23 — it transcribes *slower than the audio arrives*.
On the single-worker `_STT_EXECUTOR` that is not "a bit slower", it is a queue that grows faster
than it drains. And it is not more accurate: 4 of 6 fixtures are 0% WER on both models, and on
the two that differ `small.en` scores marginally *worse*.

**`beam_size=1` rejected** — 15% faster, measurably worse accuracy; decode time is not the
bottleneck at RTF 0.36.

**VAD adopted** — ~7% faster at identical WER, and it suppresses the filler Whisper hallucinates
on silence, which matters because `record_until_silence()` always submits a 2.5s silent tail.

**Scoring correction made mid-run.** The first sweep reported a flat 8.1% WER for *every*
config — a red flag, not a result. Two references were scoring correct behaviour as error
(Whisper is supposed to turn spoken "dot"/"at" into punctuation). Corrected references
(`_EXPECTED_TRANSCRIPTS`) moved the numbers to 3.9% / 5.0% and made the models distinguishable
at all.

STT settings are now env-overridable (`METATRON_WHISPER_MODEL` / `_BEAM` / `_VAD`) so a future
change is a config edit, not a code edit.

---

---

## Deploy and commit — one commit, two sessions

Nearly got this wrong. I was about to stage only my own hunk of `core/orchestrator.py` and leave
the parallel window's uncommitted work in the tree; Mike stopped it. Two reasons it could not be
split:

1. `core/orchestrator.py` held both sessions' work (my one line for `clinical_threads`, their
   `filter_output()` rebuild and `[CONTEXT]` repair ladder).
2. The file already imported `tools/pollen.py`, which was **untracked**. Because that is a
   *function-level* import inside `register_tools()`, committing without it would have passed
   `py_compile`, passed module import, passed a clean `systemctl` start — and died on the first
   pipeline session. CLAUDE.md deploy-safety rule 1. `routing_cloud.yaml` had already granted
   `get_pollen_forecast`, which is rule 2.

So the post-deploy check had to be a **live `/session` call**, not a service status:

```
{"response":"You have nothing on your calendar for today."}
```

Coherent reply, no `ImportError` in the journal, both services active.

## Backlog close-out (`2195fa9`)

Seven completed entries moved from the Open sections and the Inbox into `## Done`, each carrying
its closing commit. **Open 53 → 48.**

Left open deliberately: ~35 struck-through historical entries (`count_items()` already excludes
`- ~~` lines, so they are not inflating the count, and they carry a live reasoning trail);
`[DB-0806-01]` (proactive half still open); the B1a status marker (B1b open, so B1 is not closed).

**A count that looked like a regression and was not.** Session start reported *45 open*; after
moving seven items *out*, the sync said *48*. Verified against `git show HEAD:DEV_BACKLOG.md`
rather than trusting the delta — the true before/after is **53 → 48**. The 45 was a stale
baseline; the parallel window added entries mid-session.

**ID collision, same cause.** Both windows minted `[DB-0808-07]`. Theirs was already referenced
elsewhere, so mine was renumbered `[DB-0808-14]`.

---

## Decisions

1. **Clinical flags: permanence separated from prominence.** `watch` state, not expiry. Tier 2
   cannot be closed from a session; enforced in Python, not asked for in a prompt.
2. **Rejected TTL expiry for clinical flags** — silently drops an unresolved crisis.
3. **`small.en` rejected for the 2-vCPU VM**, on measurement. Not a statement about the model —
   revisit at D1 on dedicated hardware.
4. **Protocol text injected by the tool, conditionally**, rather than added to `synthesizer.md`.
5. **Audio fixtures gitignored** (1.6 MB, regenerable via `--generate`).

## Deferred / filed

1. **Re-evaluate STT on real captured audio.** Fixtures are synthesized — clean, no noise, no
   accent. The latency verdict is robust; the *accuracy* verdict only covers clean dictation.
2. **Revisit `small.en` at D1** — dedicated hardware changes the RTF arithmetic entirely.
3. **Second STT worker** if concurrent voice use ever becomes real.
4. **Administrative-close mechanism for tier-2 clinical threads** — the schema is pre-wired
   (`resolved` exists and is refused); the mechanism that would legitimately set it does not.
5. **`_thread_tier()` cannot distinguish psychiatric from cardiac medication** — the user's
   heart-med/anti-psychotic split is honoured at the `CLINICAL_CONCERN` boundary, but a
   `MEDICATION_MISSED_CRITICAL` for an anti-psychotic is currently tier 1. Fixable with a
   `psychiatric: true` marker in the stored medication profile.
