### 2026-10-30 (WhatsApp Phase 0b and the phone probes — the clean-room reader decrypts Mike's real backup; nightly backups turn out to be incremental) — **uncommitted code for Mike's review; nothing deployed, nothing on the VM**

**Incoming handoff:** `archive/handoffs/2026-10-26-whatsapp-phase-0b-clean-room-and-probes-prompt.md`
(clean-room session 2). Started 10-26, paused, resumed 10-30 after a light refresh of the
intervening commits (second-user build merged, day-planner Stage C push).

**Clean-room record (legal check L1).** Before any code: `.venv/bin/pip show wa-crypt-tools` →
not found; `grep -rl wa_crypt_tools .` (excluding `.venv/`) → only the handoff prompt's own
instruction line. Sources used: the format description, the fixtures, the plan — nothing else; no
10-26 transcript opened. **This session's transcript is filed under the session's START date:
`archive/transcripts/2026-10-26 — pasted_content id=7fdd Model Opus 5.5 — a build session.md` — it
is session 2's (clean), not session 1's (which holds the GPL source); do not confuse the two when
assembling L1.** Coverage: every § 7 and § 6 row covered by a passing test or a stated reason
(`android/app/build/reports/whatsapp_backup_coverage.txt`); all 14 vectors pass; 19 tests.

**Built.** `android/app/src/main/java/com/mike/metatron/whatsapp/` — key parsing + HKDF, a minimal
protobuf header reader, **our own streaming GCM** (AES-ECB counter blocks with inc32 + 4-bit-table
GHASH), single-pass MD5-trailer detection holding back the last 32 bytes, zlib with an RFC 1950
header check, temp-then-rename with delete on any failure, free-space and being-written checks,
named errors, a schema check. **Why our own GCM, not `Cipher("AES/GCM")`:** both the JVM provider
and Android's Conscrypt buffer the whole ciphertext until `doFinal` — § 6.5's "never the whole
file in memory" rules them out; BouncyCastle (a new dependency) rejected. Cross-checked against the
platform GCM in tests. Probe in its own **`waprobe` build type** (`src/waprobe/`), not
`src/debug/` as first proposed — **Iva's APK rebuild this weekend uses `assembleDebug` from this
tree**, which would have shipped her the listener and All-files permission. Same app ID (Firebase
config is keyed to it). `allowBackup="false"` (P4). `.gitignore` widened to admit the tests and
`src/waprobe/` — outside the prompt's Amber scope, necessary to commit at all.

**Measured on Mike's phone.** Decrypt 0.9 s, 16.4 → 36.4 MB (2.2×); 50,597 messages, 4,606 chats
(3,842 / 632 lid / 130 groups), oldest 2017-10-23 — the 10-26 Mac counts plus growth. Live: every
message notification carries a chat ID in the shortcut — groups `@g.us`, **one-to-one chats by
hidden ID `@lid`**; 4 of 4 resolve to their chat, all 3 lids mapped by `jid_map`. Dedup key 5 of 5
exact time. Group notifications carry no person key (one sample). Device for LM: Unihertz Jelly
Star, Helio G99, Android 13 (patch 2023-06), 8 GB, **no AICore**.

**Found, not in the plan:** (1) **nightly backups are incremental** —
`msgstore-increment-N-….crypt15` at 02:00; full backups only 10-22, 10-26, and Mike's manual run;
the description does not cover increments, the reader ignores them (conservative), so P3 as
designed lags ~a week. (2) Group-summary notifications are 20 of 26 posts and carry the latest
chat's ID — the listener must skip them. (3) Length-only edit detection misses an equal-length
edit. (4) Android 13 "restricted settings" silently blocked the first notification-access grant.
(5) A `chat_history_backup` channel marks WhatsApp's backup run. (6) History effectively starts
2024.

**Believed earlier, wrong:** the summaries' `@lid` IDs were guessed to be Mike's own — they resolve
to chats. The edit was said to have "arrived with its own time" — all 5 live times then matched
backup rows exactly; unresolved. The waprobe APK's smaller size looked like missing content — it
is incremental-packaging slack in the debug APK; contents identical.

**Open, owed by Mike (`archive/handoffs/2026-10-31-whatsapp-phase-0-close-survival-lm-increments-prompt.md`):**
the 24 h survival read (after 13:22 on 10-31); **LM ruling** — recommended no local model now,
revisit after M2; **increments** — recommended (a) a Phase 0a′ session describes them, a clean
session extends the reader. Neither ruling given this session.

