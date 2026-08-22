### 2026-08-22 (`/backlog attack` — offline shell, merge gate + unmerge, venue discovery: three clusters shipped) — `2d7f955`, `e2a7f87`, `fd0aed1`, `8754222`, merge `0b9c82e`, wiring `158cebe` — **not deployed**

**Mike's brief: clear generic fixes from the queue with a minimum of Red tier.** `## Now` gave
one workable item (`[DB-0808-04]`, his #1; `[DB-0820-01]` is Red + blocked on export data), so
the other two came from `## Later` with his authorisation. Coordinated in Fable, built by three
Opus workers in disjoint worktrees; Red edits (grants, agent files) done in this window only.

- **A dead server now shows the app's own page, not the browser error** (`[DB-0803-05]`,
  `2d7f955`+`e2a7f87`). Fallback-only SW: navigations, network-failure catch path, `offline-v1`
  version as recovery lever; `/` never cached. **Found while verifying the worker's report:** SW
  registration lived only inside `initPush()`, gated on PushManager + notification permission —
  a user who declined notifications never got the shell. Now registered unconditionally at
  startup; `initPush` reuses it. The worker correctly rejected my `await …ready` suggestion,
  which would hang forever on a failed registration.
- **Merging two contacts now asks first, shows both people, and is reversible**
  (`[DB-0822-03]`, `fd0aed1`). Confirmation via the existing `confirm.py` two-step; description
  built from resolved records ("a wrong id and a right id look exactly alike"), with
  `spouse_name`/`last_contact` added to `_disambiguation_entry` — the two fields that told the
  three Stevens apart. `"ph"`-class digitless/under-5-digit phone stubs refused. Pre-merge
  snapshot of the *kept* record makes `unmerge_contacts` possible forward; **pre-08-22 merges
  refuse honestly — no snapshot exists**, so Steven's repair stays `[DB-0822-04]`, manual.
- **"Find a café near X" is now answerable** (`[DB-0808-04]`, `8754222`). `find_places` —
  Places API (New) Text Search, provider-agnostic schema, FieldMask pinned to cheap SKU tiers,
  empty results return an error not an empty list. **Corrected from the Opus plan: "rides the
  same key" was wrong** — the Maps key is restricted to `routes.googleapis.com` at creation
  (routing.py's own header), so this uses a separate `GOOGLE_PLACES_API_KEY`, same
  leak-containment rationale. **Key does not exist yet; tool errors honestly until Mike creates
  it** (Places-restricted, ~$0.017–0.032/call, under $2/mo at expected use, inside the $200
  Maps credit).
- **Wiring (`158cebe`, this window):** both tools registered; `find_places` → READ_TOOLS,
  `unmerge_contacts` → ACTION_TOOLS; grants in both routing files (logistics + recreation get
  `find_places`, relationships gets `unmerge_contacts`); named in all three agent files; stale
  "Places — not yet built" backlog notes struck; `merge_contacts` given its durable `_EXECUTORS`
  line (worker's import-side `setdefault` kept as fallback).

**Rejected:** `[DB-0808-11]` (3am push) — pure Red, no non-Red slice; `[DB-0818-04]` (National
Rail) — needs a Darwin key only Mike can register; `[DB-0808-14]` — two-line fix owing a full A4
re-run. Worker estimate ~64k×3 ≈ 190k; actual 59k + 76k + 118k + 60k (C) = ~313k — the A
extension round-trip and B's size ran over; B alone nearly doubled the median.

**Verification:** merge-guard 25/25, dedup 18/18, places 28/28, SW 15/15 (real `vm`-sandbox
execution, mutation-tested), reconnect 5/5, provenance 10/10, `qa_sweep` 9/9. **Needs
`./deploy.sh`** (static/, tools/, core/, config/). Remaining acts: Mike — deploy, Places key,
one online load post-deploy before testing the shell offline. Pre-existing check_agent_tools
findings on relationships/recreation/logistics surfaced during the grant edits are the
`[DB-0810-03]` decision queue — left alone.
