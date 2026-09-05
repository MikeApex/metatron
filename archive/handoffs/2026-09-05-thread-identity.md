# Handoff — thread identity across rewording `[DB-0814-02]`

**Shipped.** A conversation thread now keeps its age when Metatron rephrases it, and only loses
it when Mike engages the thread himself. Threads can therefore reach the 7-day cutoff and expire,
which they had not done once in 20 days. Identity is an **anchor-set key**: content tokens,
stopwords and generic action/time words dropped, crudely stemmed, digits kept — two threads are
the same thread if the sets are equal or share 2 anchors (`_anchor_tokens` / `_same_thread`,
modelled on `tools/horizon.py:_norm`; no scores, no model call, nothing semantic).

**Commit:** `a4b64b5` on branch `wt/thread-identity` in the worktree —
`tools/context_tracker.py`, `tests/test_thread_identity.py` (new), `tests/test_open_thread_expiry.py`.
(This file's own SHA correction is the commit on top of it; nothing else differs.)

**Close `[DB-0814-02]`.** Evidence: 16 new checks in `tests/test_thread_identity.py`, and a
before/after probe on the same scenario — on HEAD a thread reworded daily stayed permanently one
day old and never expired; with the fix it carries its birthdate and lands in
`expired_open_threads`. Full suite: **72 pass**. Three failures (`test_action_provenance`,
`test_persona_resolver`, `test_server_auth`) were verified failing on HEAD too — pre-existing,
unrelated, `record_wisdom_response` is unclassified in `core/actions.py`.

**For SESSION.md:** thread expiry is live, not dead — drop the "structurally dead / decision owed"
warning. **Needs a VM deploy** (`tools/`) and then a re-read of `context_audit.jsonl` in ~10 days
to confirm expiries fire in production. Two smaller notes: the audit line gained a fourth field,
`reworded`, alongside `added`/`removed`/`expired` (additive, nothing folded); and
`_user_engages_thread` now stems both sides, so grace survives speech-to-text plurals — it had to,
because user engagement is now the only thing that refreshes a date.

**Left out:** `core/translate.py`'s header still says `open_threads` "is matched by exact text in
`_merge_open_threads`" — stale wording, outside my manifest. Its conclusion (never store a
translated thread) is unchanged and now stronger, since anchors are English-stemmed.
