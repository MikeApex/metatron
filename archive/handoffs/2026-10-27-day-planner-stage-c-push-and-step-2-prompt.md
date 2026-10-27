Model: Opus 5.5 — native Android, a new outbound channel and the last day-planner switches; the scheduler and agent-facing pieces are Red, built with Mike present (Red is never delegated).

# Day planner — Stage C (push with the app closed), then step 2 (launch prompt)

**Do not start until the second-user build has landed** (`archive/plans/multi_user_accounts_plan_2026-10-26.md`).
Mike's order, 2026-10-27: second user → Stage C → step 2. Stage C is built on that build's
per-user push (its items 1.6 and 3.2: subscriptions owned by a persona, `send_push(…, persona)`,
`_notify_push` passing it). Not concurrent with it: same `core/push.py`, `core/server.py` routes,
`core/scheduler.py` notify path and APK.

**Budget:** ~1.5–2.5M Opus tokens on the subscription; Mike ~45–60 min (a 15-min Firebase
walkthrough, the APK rebuild and sideload, a live check). Run cost: FCM is free at this volume;
nudges replace today's fixed check-ins, so roughly neutral in model tokens (plan § 12:
~$0.05–0.25/day). **Unseen:** FCM delivery has no meter here; record delivered/failed per send in
the trace or it is invisible.

---

/metatron-code Day planner Stage C, then step 2, Mike present. Read first:
`archive/plans/day_planner_plan_2026-10-24.md` § 7 (nudges and check-ins, § 7.4 the constraint),
§ 14 D1, and the 2026-10-27 entry in `archive/PROJECT_LOG.md`. Confirm the second-user build is on
`main` and read `core/push.py` and `core/scheduler.py:_notify_push` as that build left them.

## 0. First — the model reshuffle: works at 16,384, now a cost and latency question

History, 10-27: cut off at 4,096 (smoke 3/3 unparseable) → 8,192 (`5252661`; smoke passed, then
both live reshuffles cut at ~8,188) → **16,384 (`08ee9d0`, Mike's call): smoke 3/3 parseable and
valid, thinking 9,927 / 11,557 / 13,225, latency 80 / 203 / 69 s, churn 0 / 4 / 0** (run 2 failed
the ≤ 3 churn rule — an equally valid arrangement from the same seed; live reshuffles seed from the
previous result). In every run the model fitted mover claims, the essential the code plan had left
"not placed", by moving lower items — the one thing the code fill cannot do. ~$0.04–0.05 a call;
~$0.20–0.40/day at 4–8 calls, a little over plan § 12.

Check first: `log.jsonl` `"event": "reshuffle"` outcomes since 10-27 — any `unparseable` means a
day ran past 16,384. Then, Mike's call, recommendation first:
1. **Keep as is** if outcomes are clean (recommended 10-27; Mike had not yet decided at close).
2. **Try a thinking cap** (~6,000) on the plain (OpenAI-compat) path — `extra_body` with Google's
   thinking config, or `reasoning_effort`; unverified on Vertex compat, one paid probe with the
   smoke test (`--runs 3`; pass = parseable, churn ≤ 3, and it still fits what the code plan could
   not). 3.8 Flash overshoots a budget (1,024 → 2,664 measured 10-26): keep the 16,384 ceiling.
3. `reshuffle_model: false` — loses the rearrangement above.

## 1. Stage C — native push with the app closed (D1 option b)

Design (plan § 14 D1 b): a **content-free data-only FCM ping** from the VM; the app wakes, fetches
the message text from the VM over its authenticated channel, and shows a native notification with
**Done / Not yet / Skipped** actions that call `/tasks/act`. The text never travels through Google.
In-repo precedent for a notification with actions: `MetatronHeadsetService` in `android/`.
1. **(M) Firebase — a guided walkthrough, steps prepared before the session:** Mike creates the
   Firebase project (or adds Android to the existing GCP project), registers the app id, downloads
   `google-services.json`, and creates a service-account key for the FCM HTTP v1 API. Claude never
   reads or commits either file — `.gitignore` both before he downloads them; the key goes on the
   VM by Mike's own `scp`.
2. APK: the FCM plugin, token registration to the server **with the persona** (the second-user
   build's account), the notification channel, the three actions. `capacitor.plugins.json` is `[]`
   today — this is the first plugin.
3. Server/VM: a sender (`core/push.py` beside Web Push, per persona), token storage per persona,
   pruning of dead tokens, a delivery record in the trace. `scheduler._notify_push` sends both.
4. Tests: sender stubbed (the standing rule — every live meter stubbed); a token for one persona
   never receives another's ping; a dead token is pruned. Then the APK build
   (`docs/INFRASTRUCTURE.md` § APK — `./scripts/check_apk_sync.sh`), Mike sideloads.
5. Live check: with the app **closed**, `POST /push/test` reaches the phone; Done on the
   notification records the task done in the ledger.

## 2. Step 2 — nudges and the plan's check-ins

1. **Check the live check-in job name first** (Mike, on the VM — the read door cannot see persona
   config): `grep -n "^  [a-z_]*:" ~/multi-model-mcp/config/personas/mike/scheduler.yaml`. It must
   be `companion_checkin`, or `replaces_jobs` in `config/modules/day_plan.yaml` changes.
2. Flip `nudges` and `owns_checkins` (`config/modules/day_plan.yaml`, committed, Mike deploys).
3. Live checks (handoff 10-24 § K2): a leave-now nudge arrives with the app closed; a held wake
   leaves no conversation row; no fixed `companion_checkin` fires; an empty-day check-in follows
   three idle hours. Quiet hours hold (nudge_tick gates them itself).

## 3. Still owed from 10-27 — put each to Mike

1. **The boys' school hours and bedtimes → `children_home`.** 10-27's plan put "hang the hooks with
   Manny" at 21:30. Two numbers per child, recorded with `set_day_shape`. Recommend asking first.
2. Handoff 10-24 § J2/J3 not yet exercised: a weekend "I'm free of childcare today" →
   `day_overrides`; "location sharing is on" → `set_day_shape(location_sharing)`.
3. **Three agents wrote the same `set_days` in parallel on 10-27** (Logistics, Finance, the
   Synthesizer); Finance's was `["10","15"]` — two days, wrong — and the record came out right only
   because a correct write landed last. Mike decides whether it is worth a backlog item; the fix
   is likely routing (one owner for a task write per turn), not the ledger.
4. Salience (10-27) — read a morning brief and an evening close with the plan on: only what is
   salient raised, tomorrow still reviewed.

Close with `/archive`. Anything that did not pass is a backlog item with the evidence that failed.
