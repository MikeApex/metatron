### 2026-09-19 (The headset-button plan reviewed to a clean pass — two rounds by hand, three by the new command)

Review-only session against the plan at `~/.claude/plans/for-the-metatron-app-modular-meerkat.md`
(headset button → talk to Metatron; a media-button trigger, a Bluetooth mic route and a foreground
service on the APK). Nothing built, nothing deployed. One artifact:
`archive/plans/adversarial_review_for-the-metatron-app-modular-meerkat_2026-09-19.md`, which
carries the command's report and three dated `## VERIFY` sections.

**Two rounds by hand first.** Round one returned six findings, then seven after Mike asked whether
the codebase had been consulted fully — it had not (`/metatron-code` was not run), and the full
read added one real finding: `android/` is gitignored except the manifest, so `MainActivity.java`
and any new service file live only on this Mac. Round two, against the revised plan, returned six
new findings, three of them regressions introduced by the fixes — the same shape the phase-3
reviews showed the day before.

**Then `/adversarial-review` landed mid-session (`dac3561`, other window) and took over.** A fresh
reviewer, unanchored on the hand rounds, returned five findings; three `verify` rounds closed all
seven it raised (two new ones surfaced by fixes) and the third round returned `none` in both
blocks. Every `CLOSED` carried a `path:symbol`. **The command's first live use worked as designed:
the resumed reviewer stayed cheap (~3–4k tokens a round), and it caught a defect the hand rounds
had planted.**

**Two things believed true earlier that were wrong — both mine.**

1. *A foreground service does not lift Doze's network suspension.* Stated in hand round two,
   carried into the plan's Step 0 probe and its "catch-up speech is the real Doze mitigation"
   framing. Wrong: Android's network policy admits a UID holding a foreground service through the
   Doze firewall chain. The fresh reviewer overturned it (its finding 4) and the plan now measures
   before/after instead.
2. *Catch-up cannot deliver an own exchange because `shownIds` dedupes it.* True of
   `applyCatchupRow` alone, but every reconnect also receives a `history` frame and `renderHistory`
   rebuilds the conversation because `onclose` has nulled `ownBubble` — so a stored reply is
   rendered today. The reviewer's rank 1 corrected the premise; the plan now keys reconnect speech
   on a single orphaned-own id set in `onclose`, since history rows carry no own-marker.

**What the rounds changed in the plan, at the level worth keeping:** headset mode owns the stop
condition (the silence auto-stop is a verb already taken); the JS↔native bridge is a
`@JavascriptInterface`, not a plugin, because the app is deliberately zero-plugin; the `source`
marker needs a server change or it records nothing; the service is `microphone`-typed, returns
`START_NOT_STICKY`, and is verified with `am crash` because `am kill` refuses a foreground-service
process; swipe-away disarms rather than relaunching, since background activity launch is denied at
targetSdk 36; the `.gitignore` carve-out extends to `android/app/src/main/java/**`.

**Decision on the two-chat loop:** one reviewer, one file. The plan chat revises against the file;
this chat runs `verify`; a second reviewer spawned from the plan chat would start cold and produce
a third opinion to reconcile. Rejected for that reason.

**Next:** the build, in the plan chat, on Opus 5 as the plan states, with the plan and the review
file together. Verbatim transcript captured twice (after the report landed, and at close).

