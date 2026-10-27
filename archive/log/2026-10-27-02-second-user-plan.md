### 2026-10-27 (the second-user plan — accounts, sign-up with approval, a scheduler per user, the in-app interview, Connections, permission, and the server's memory) — `archive/plans/multi_user_accounts_plan_2026-10-26.md`, `archive/plans/adversarial_review_multi_user_accounts_plan_2026-10-26.md`, `archive/handoffs/2026-10-27-multi-user-build-prompt.md` — **planning only; nothing built, nothing to deploy**

**Started 10-26 as "serve the APK for Iva for two hours"; stopped before serving.** The survey found
that one shared password let anyone holding it act as any persona, and that `ROADMAP.md` § 0's Vertex
basis lapsed "the moment the deployment stops being single-user". Mike: forget the two-hour install;
per-user login with in-app sign-up approved by him in a Claude Code chat; the privacy basis extends
to Iva ("she understands I have full access"); Tailscale stays; a scheduler per user (Family mode
will batch groups later); the goals and scheduling interviews merged into one, in the app.

**Survey findings that shaped the plan (each invisible with one user):** every request names its own
persona and unnamed ones become `mike`; `persona_scope()` mirrors identity into the process
environment, so an unscoped thread can read another user's; push subscriptions are global; audio
lands in one folder; `/monitor/*` opens for any token; the WS takes its user from the URL; no
in-app interview exists, and the interviewer had no confidentiality or crisis section.

**Reviewed by Fable (adversarial, high): 22 findings across 13 rounds, all closed.** The structural
ones: the plan ran ahead of the Phase 7 gate without saying so (now § 2a + D7: Iva is a test user
admitted early, isolation at the auth/path layer only); her sign-up consent had nowhere to be stored;
each per-user scheduler would have loaded its own embedder copy.

**Decisions:** D1–D7 (admin password cannot act as an account user; proactive sessions hold until
the interview is finished or paused; Mike-run password reset; "name taken" is said; Stage B first —
satisfied by `9f2eeac`; crisis wording reviewed in the Red session; admitted ahead of Phase 7), D9
(she is told in the app and gives permission herself — enforced in code, withdrawable), D10
(monitor, diagnose, price an upgrade only on measurement), D11 (a permission screen at sign-up too),
D13 (CPU-only PyTorch on the VM), D14 (voice in an on-demand helper process). Open: D8 (her own vs a
dedicated Gmail — her choice), D12 (Mike's own app passwords — recommendation revised to leave
them), the voice helper's idle timeout (recommended 10 min). Connecting Gmail/Calendar in the app
was added after the walkthrough (§ 4.10); work Microsoft 365 accounts wait for Mark 2's OAuth.

**Rejected, with reasons:** one scheduler daemon looping over users (the `schedule` library is
process-global and one user's 20–70 s session would hold the other's brief); the interview through
the pipeline (five turns of history, ~30 s a turn, a second voice); account-changing HTTP endpoints
(approval runs on the VM over SSH — fewer things to protect when the server is ever public); manual
credential setup (her app password would land in the verbatim transcript archive); `--extra-index-url`
for CPU PyTorch (lets the second index supply other packages); a larger VM now (decided by a
week-long whole-VM measurement after the fix).

**The memory diagnosis — believed wrong earlier in this same session, corrected by evidence.** I
first wrote that memory was "not the constraint" (803 MB available at one midday reading) and that
the watchdog kept no record. Its log held **7,875 low-memory warnings since 08-18 and OOM kills on
08-18, 10-15 and 10-22, none ever reported** (its push posts to a route that does not exist and
nothing reads the file). Isolated, capped probes on the VM (Mike approved; server untouched; files
removed): **Kokoro loads at 1,503 MB and one long reply needs 440 MB more**; the embedder (787→903 MB)
and Whisper (662→752 MB) level off. PyTorch is the CUDA build on a GPU-less VM — 169 MB resident,
2.7 GB disk. The scheduler's "69 MB" was a fresh-process figure; its in-process weekly jobs would
load the embedder (twice — `tools/baselines.py` holds a second copy). Fix in the plan: § 4.12. **Mike
can switch 🔊 off in the Mac web app now** — the 10-27 spoken replies came from there.

**Also corrected:** `scripts/metatron-backup.sh` tars four named paths, not `data/`; `systemctl mask`
refuses over a real unit file; the server's `--persona` is not required, contrary to
`docs/INFRASTRUCTURE.md`; my first build estimate (1–1.5 h for a per-user password) became ~4.5–7M
Opus tokens across five stages once self-sign-up, approval and per-user scheduling were in scope.

**Next:** the build, from `archive/handoffs/2026-10-27-multi-user-build-prompt.md`.

