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
