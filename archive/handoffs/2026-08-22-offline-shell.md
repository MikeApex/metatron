# Handoff — offline shell (DB-0803-05)

**Shipped.** A phone whose server is unreachable now shows the app's own dark "Can't reach you
right now" page with a Try again button, instead of Chrome's error page. `static/offline.html`
(new, self-contained, inline CSS, no external references) is cached at SW install; `static/sw.js`
gained a `fetch` handler that intercepts **navigations only** and serves the shell **only on the
network-failure catch path**. Never cache-first, never `/`, never `index.html`; API, WebSocket
upgrade and static-asset requests are not intercepted at all. Cache name is `offline-v1` and
`activate` deletes every other cache — bumping that constant is the recovery lever if a shell
ships wrong, which is what the item's "sticky" warning asked for. Push and notificationclick
handlers are byte-identical (verified by diff). `/sw.js` stays `no-store`.

**core/server.py untouched** — `auth.OPEN_PREFIXES` already contains `/static/`, so
`/static/offline.html` is reachable before login and the SW can cache it. Confirmed live with a
TestClient smoke run: 200, no credentials. No new route was needed.

**Tests.** New `tests/test_sw_offline_shell.js` (plain node, `test_ws_reconnect_race.js` pattern).
This is a **real execution test, not a static assertion** — `static/sw.js` is evaluated verbatim in
a `vm` sandbox with fake `self`/`caches`/`fetch`/`Response`, and the registered handlers are
invoked with fake events. 14/14 pass: shell served on a rejected navigation fetch, network
response served when the fetch succeeds, 503 rather than a throw if the cache is empty, five
non-navigation request shapes pass through with `respondWith` never called, `/` and `index.html`
never cached, stale caches deleted on activate. Existing `tests/test_ws_reconnect_race.js` (5/5) and
`tests/test_server_auth.py` (all pass, run standalone — pytest is not installed in the venv) are
unaffected.

**Close DB-0803-05** on this evidence: `node tests/test_sw_offline_shell.js` → 14/14, plus the
manual check below.

**Manual check for Mike (VM must be running first):** open the PWA on the phone, then stop the
server on the VM (`sudo systemctl stop metatron-server`), then pull-to-refresh or relaunch the app.
Pass = the dark "Can't reach you right now" page with a working Try again button. Fail = the
browser's own error page. Restart the server and reload to confirm the live app comes back.

**Needs `./deploy.sh`** — `static/` only (`sw.js`, `offline.html`). Not deployed from here.

**SESSION.md must carry — one open gap, outside my manifest.** The offline shell only reaches a
device once `/sw.js` is registered, and `static/index.html` registers it **only inside `initPush()`
on the notification-permission path** (lines ~2123 and ~2140); a user who declined or never enabled
notifications has no service worker, so they still get the browser error page. Fixing it is one
unconditional `navigator.serviceWorker.register('/sw.js')` on load, but `static/index.html` was not
in this worker's manifest and was not edited. Worth a backlog item — not filed, since it was not
asked for.

**Transcript not captured.** `archive_chats.py` resolves the project root from cwd, finds no JSONL
for `-Users-md-homefolder-Desktop-metatron-wt-offline-shell`, and exits; this session's log lives
under the main tree's project directory, which this worker was told not to write to. The
coordinator should run it from the main tree.

---

## Update — registration gap closed (coordinator follow-up, same session)

The gap named above is fixed; manifest was extended by `static/index.html`. Stated precisely:
`index.html` **did** register `/sw.js`, but only inside `initPush()`, gated on `PushManager`
support and `Notification.permission` (~lines 2104–2145). Users who declined notifications, and
WebViews with no `PushManager`, never registered a worker — so the offline shell never installed
for them.

**Change (minimal, no push/permission UI logic or wording touched).** One unconditional
`navigator.serviceWorker.register('/sw.js')` at script bootstrap, guarded only by
`'serviceWorker' in navigator`, running before and independently of login — both `/sw.js` and
`/static/offline.html` are in `auth.OPEN_PREFIXES`/`OPEN_PATHS`, so it works pre-login. The
registration promise is held in `swRegistration`, and `initPush()`'s two former `register()` call
sites now `await swRegistration` then `await navigator.serviceWorker.ready`.

**Why the promise rather than bare `.ready`:** `navigator.serviceWorker.ready` never settles when
nothing is registered, so awaiting it alone would have left the push UI stuck on "Notifications on
— setting up…" whenever registration failed, where the old code surfaced an error. Awaiting
`swRegistration` first preserves the original failure behaviour through the existing `catch`. The
logging `.catch` is attached to a derived promise so the original still rejects.

**Tests: 15/15** (`node tests/test_sw_offline_shell.js`). The added check is a **static assertion**
— it brace-matches `initPush()`'s body and asserts at least one `/sw.js` registration lies outside
it, none inside, and that the startup call is not gated on `PushManager` or
`Notification.permission` (comments stripped first, since the comment there names PushManager
deliberately). It was **mutation-tested**: deleting the startup registration turns it red (14/15),
so it is not vacuous. The other 14 checks still execute the real `sw.js`. `qa_sweep.sh` 9/9 in this
worktree.

**Manual check is unchanged, but now covers more devices** — including a phone with notifications
declined, which previously could not show the shell at all. Note the first load after deploy still
needs one online visit to install the worker; the shell appears from the *next* failed navigation.

Commits: `2d7f955` "Serve an offline shell when the server is unreachable", then "Register the service worker unconditionally at startup" (this commit — see `git log --oneline -2`; not quoted by hash here, since amending the commit that contains this file would change it). Still needs
`./deploy.sh`, `static/` only.
