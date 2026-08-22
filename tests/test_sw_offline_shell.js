/*
 * tests/test_sw_offline_shell.js — DB-0803-05: a dead server must show the app's
 * own offline page, not the browser's error page.
 *
 * Before this, static/sw.js registered no `fetch` handler at all and `/` is served
 * no-store, so a phone whose server was unreachable got Chrome's dinosaur.
 *
 * This runs the REAL service worker: static/sw.js is evaluated verbatim inside a
 * vm sandbox with fake `self`, `caches`, `fetch`, `Request` and `Response`, and the
 * registered handlers are then invoked with fake events. Re-implementing the
 * handler here would prove nothing — the point is that the shipped file behaves.
 *
 * The two properties that matter, and the two that keep it safe:
 *   - a navigation whose network fetch FAILS is answered with offline.html
 *   - a navigation whose network fetch SUCCEEDS is answered by the network
 *   - non-navigation requests (API, WebSocket upgrade, static assets) are never
 *     intercepted at all — respondWith is not called
 *   - `/` and index.html are never put in the cache, and a stale cache version
 *     is deleted on activate (the recovery lever for a wrong shell)
 *
 *   node tests/test_sw_offline_shell.js
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const SW = path.join(__dirname, '..', 'static', 'sw.js');
const src = fs.readFileSync(SW, 'utf8');

const results = [];
function check(name, fn) {
  return Promise.resolve()
    .then(fn)
    .then(() => results.push([name, true, '']))
    .catch(e => results.push([name, false, `${e.name}: ${e.message}`]));
}
function assert(cond, msg) { if (!cond) throw new Error(msg); }

// --- fakes -----------------------------------------------------------------

class FakeResponse {
  constructor(body, init) { this.body = body; this.status = (init && init.status) || 200; }
}
class FakeRequest {
  constructor(url, init) { this.url = url; this.cache = (init && init.cache) || 'default'; }
}

function makeCaches() {
  const store = new Map();            // cacheName -> Map(url -> Response)
  const api = {
    _store: store,
    open(name) {
      if (!store.has(name)) store.set(name, new Map());
      const entries = store.get(name);
      return Promise.resolve({
        add(req) {
          const url = typeof req === 'string' ? req : req.url;
          api._added.push({ url, cacheOpts: req.cache });
          entries.set(url, new FakeResponse(`BODY:${url}`));
          return Promise.resolve();
        },
        match(url) { return Promise.resolve(entries.get(url)); },
      });
    },
    keys() { return Promise.resolve([...store.keys()]); },
    delete(name) { const had = store.delete(name); api._deleted.push(name); return Promise.resolve(had); },
    _added: [],
    _deleted: [],
  };
  return api;
}

// Loads static/sw.js and returns the sandbox plus its registered handlers.
function loadWorker(opts = {}) {
  const handlers = {};
  const cachesApi = opts.caches || makeCaches();
  const calls = { skipWaiting: 0, claim: 0, fetches: [] };

  const sandbox = {
    caches: cachesApi,
    Response: FakeResponse,
    Request: FakeRequest,
    Promise, JSON, console,
    fetch: (req) => { calls.fetches.push(req); return opts.fetch(req); },
    clients: { matchAll: () => Promise.resolve([]), openWindow: () => {} },
  };
  sandbox.self = {
    addEventListener: (type, fn) => { handlers[type] = fn; },
    skipWaiting: () => { calls.skipWaiting++; },
    clients: { claim: () => { calls.claim++; return Promise.resolve(); } },
    registration: { showNotification: () => Promise.resolve() },
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(src, sandbox, { filename: 'sw.js' });
  return { handlers, caches: cachesApi, calls };
}

// A fetch event that records what the worker answered with, if anything.
function fetchEvent(request) {
  const ev = { request, responded: false, response: undefined };
  ev.respondWith = (p) => { ev.responded = true; ev.response = Promise.resolve(p); };
  return ev;
}
function lifecycleEvent() {
  const ev = { waited: null };
  ev.waitUntil = (p) => { ev.waited = p; };
  return ev;
}

const NEVER = () => Promise.reject(new Error('network down'));
const ALWAYS = () => Promise.resolve(new FakeResponse('FROM-NETWORK'));

// --- tests -----------------------------------------------------------------

async function main() {
  await check('a fetch handler is registered at all', () => {
    const { handlers } = loadWorker({ fetch: ALWAYS });
    assert(typeof handlers.fetch === 'function', 'sw.js registered no fetch handler');
  });

  await check('install caches offline.html — and nothing else', async () => {
    const w = loadWorker({ fetch: ALWAYS });
    const ev = lifecycleEvent();
    w.handlers.install(ev);
    await ev.waited;
    const urls = w.caches._added.map(a => a.url);
    assert(urls.length === 1, `expected exactly 1 cached entry, got ${JSON.stringify(urls)}`);
    assert(/offline\.html$/.test(urls[0]), `cached the wrong thing: ${urls[0]}`);
    assert(w.caches._added[0].cacheOpts === 'reload', 'shell must be fetched with cache:"reload"');
    assert(w.calls.skipWaiting === 1, 'install must skipWaiting');
  });

  await check('neither / nor index.html is ever cached', async () => {
    const w = loadWorker({ fetch: ALWAYS });
    const ev = lifecycleEvent();
    w.handlers.install(ev);
    await ev.waited;
    for (const { url } of w.caches._added) {
      assert(url !== '/', 'sw.js cached "/" — a stale app shell is exactly what this must not do');
      assert(!/index\.html/.test(url), 'sw.js cached index.html');
    }
  });

  await check('navigation + failed network -> offline.html from cache', async () => {
    const w = loadWorker({ fetch: NEVER });
    const inst = lifecycleEvent();
    w.handlers.install(inst);
    await inst.waited;

    const ev = fetchEvent({ url: 'https://host/', mode: 'navigate' });
    w.handlers.fetch(ev);
    assert(ev.responded, 'a navigation was not intercepted');
    const res = await ev.response;
    assert(/offline\.html$/.test(res.body), `served ${res.body}, expected the cached offline shell`);
    assert(res.status === 200, `offline shell came back ${res.status}`);
  });

  await check('navigation + working network -> the network response, not the cache', async () => {
    const w = loadWorker({ fetch: ALWAYS });
    const inst = lifecycleEvent();
    w.handlers.install(inst);
    await inst.waited;

    const ev = fetchEvent({ url: 'https://host/', mode: 'navigate' });
    w.handlers.fetch(ev);
    const res = await ev.response;
    assert(res.body === 'FROM-NETWORK', `served ${res.body} — cache-first would break every update`);
    assert(w.calls.fetches.length === 1, 'the network was not tried first');
  });

  await check('navigation + failed network + empty cache -> a 503, never a throw', async () => {
    const w = loadWorker({ fetch: NEVER });   // note: install never ran
    const ev = fetchEvent({ url: 'https://host/', mode: 'navigate' });
    w.handlers.fetch(ev);
    const res = await ev.response;
    assert(res.status === 503, `expected 503 fallback, got ${res.status}`);
  });

  const passthrough = [
    ['API POST', { url: 'https://host/api/message', mode: 'cors' }],
    ['same-origin XHR', { url: 'https://host/api/state', mode: 'same-origin' }],
    ['WebSocket upgrade', { url: 'wss://host/ws', mode: 'websocket' }],
    ['static asset', { url: 'https://host/static/app.css', mode: 'no-cors' }],
    ['the service worker script itself', { url: 'https://host/sw.js', mode: 'same-origin' }],
  ];
  for (const [label, request] of passthrough) {
    await check(`${label} passes through untouched`, async () => {
      const w = loadWorker({ fetch: NEVER });
      const inst = lifecycleEvent();
      w.handlers.install(inst);
      await inst.waited;

      const ev = fetchEvent(request);
      w.handlers.fetch(ev);
      assert(!ev.responded, `${label} was intercepted — respondWith must not be called`);
      assert(w.calls.fetches.length === 0, `${label} caused the worker to issue its own fetch`);
    });
  }

  await check('activate deletes a stale cache version and keeps the current one', async () => {
    const cachesApi = makeCaches();
    cachesApi._store.set('offline-v0', new Map());
    cachesApi._store.set('v2', new Map());
    cachesApi._store.set('offline-v1', new Map());
    const w = loadWorker({ fetch: ALWAYS, caches: cachesApi });

    const ev = lifecycleEvent();
    w.handlers.activate(ev);
    await ev.waited;
    assert(cachesApi._deleted.includes('offline-v0'), 'stale offline-v0 survived activate');
    assert(cachesApi._deleted.includes('v2'), 'the old v2 cache name survived activate');
    assert(!cachesApi._deleted.includes('offline-v1'), 'activate deleted the current cache');
    assert(w.calls.claim === 1, 'activate must claim clients');
  });

  await check('push and notificationclick handlers survive', () => {
    const { handlers } = loadWorker({ fetch: ALWAYS });
    assert(typeof handlers.push === 'function', 'push handler lost');
    assert(typeof handlers.notificationclick === 'function', 'notificationclick handler lost');
  });

  await check('offline.html is self-contained — no external references', () => {
    const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'offline.html'), 'utf8');
    assert(!/<link\b/i.test(html), 'offline.html has a <link> — it cannot load when offline');
    assert(!/<script[^>]+\bsrc=/i.test(html), 'offline.html loads an external script');
    assert(!/\bhttps?:\/\//i.test(html), 'offline.html references an absolute URL');
    assert(/location\.reload\(\)/.test(html), 'offline.html has no retry that reloads');
  });

  // --- report ---
  let failed = 0;
  for (const [name, ok, err] of results) {
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${err ? `\n      ${err}` : ''}`);
    if (!ok) failed++;
  }
  console.log(`\n${results.length - failed}/${results.length} passed`);
  process.exit(failed ? 1 : 0);
}

main();
