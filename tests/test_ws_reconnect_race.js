/*
 * tests/test_ws_reconnect_race.js — DB-0810-01: a reconnect must never leave two
 * live WebSockets open at once.
 *
 * Observed live twice on 2026-08-10: a streaming reply rendered twice inside one
 * bubble. ensureConnected() called ws.close() and connectWebSocket() on consecutive
 * lines; close() is asynchronous, so both sockets were briefly in the server's
 * per-persona broadcast set and one chunk arrived twice on one device.
 *
 * This runs the REAL code: the WebSocket section is extracted verbatim from
 * static/index.html and evaluated against a fake WebSocket with an asynchronous
 * close, which is precisely the property the old code assumed away. Testing a
 * re-implementation here would prove nothing.
 *
 *   node tests/test_ws_reconnect_race.js
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = path.join(__dirname, '..', 'static', 'index.html');
const START = '// --- WebSocket (cross-device sync) ---';
const END = '// Android freezes the WebView when the app is backgrounded';

const src = fs.readFileSync(HTML, 'utf8');
const a = src.indexOf(START);
const b = src.indexOf(END, a);
if (a < 0 || b < 0) {
  console.error('FAIL  could not locate the WebSocket section in static/index.html');
  process.exit(1);
}
const SECTION = src.slice(a, b);

const results = [];
function check(name, fn) {
  try { fn(); results.push([name, true, '']); }
  catch (e) { results.push([name, false, `${e.name}: ${e.message}`]); }
}

// --- a fake WebSocket whose close() is asynchronous, as the real one is ---
function makeHarness(opts = {}) {
  const { neverClose = false } = opts;
  const sockets = [];
  let now = 0;
  const timers = [];

  class FakeWebSocket {
    static CONNECTING = 0; static OPEN = 1; static CLOSING = 2; static CLOSED = 3;
    constructor(url) {
      this.url = url; this.readyState = 0; this.sent = [];
      this._listeners = [];
      sockets.push(this);
    }
    addEventListener(type, fn) { if (type === 'close') this._listeners.push(fn); }
    send(d) { this.sent.push(d); }
    open() { this.readyState = 1; if (this.onopen) this.onopen(); }
    close() {
      if (this.readyState === 3) return;
      this.readyState = 2;                       // CLOSING — not yet CLOSED
      if (neverClose) return;                    // the frozen-WebView case
      timers.push([now + 50, () => this._finishClose()]);
    }
    _finishClose() {
      if (this.readyState === 3) return;
      this.readyState = 3;
      if (this.onclose) this.onclose();
      this._listeners.forEach((f) => f());
    }
    deliver(obj) { if (this.onmessage) this.onmessage({ data: JSON.stringify(obj) }); }
  }
  FakeWebSocket.OPEN = 1;

  const sandbox = {
    WebSocket: FakeWebSocket,
    SERVER: 'http://x',
    authToken: 't',
    currentPersona: 'mike',
    window: { location: { origin: 'http://x' } },
    JSON, Math, console,
    Date: { now: () => now },
    setTimeout: (fn, ms) => { const h = { fn, at: now + (ms || 0) }; timers.push([h.at, fn, h]); return h; },
    clearTimeout: (h) => { for (let i = 0; i < timers.length; i++) if (timers[i][2] === h) timers.splice(i, 1); },
    setInterval: () => 0,
    requestAnimationFrame: () => 0,
    // Everything the section calls but does not define:
    setStatus: () => {}, setLoading: () => {}, addMessage: () => ({}),
    handleWsMessage: (m) => { sandbox.rendered.push(m); },
    clearAuth: () => {}, showLogin: () => {}, setLoginError: () => {},
    lastSeenId: 0,
    rendered: [],
  };
  vm.createContext(sandbox);
  vm.runInContext(SECTION, sandbox, { filename: 'index.html:ws-section' });

  const advance = (ms) => {
    const target = now + ms;
    for (;;) {
      timers.sort((x, y) => x[0] - y[0]);
      if (!timers.length || timers[0][0] > target) break;
      const [at, fn] = timers.shift();
      now = at;
      fn();
    }
    now = target;
  };

  return { sandbox, sockets, advance, liveCount: () =>
    sockets.filter((s) => s.readyState === 0 || s.readyState === 1).length };
}

// ---------------------------------------------------------------------------

check('a reconnect never has two non-closed sockets at the same time', () => {
  const h = makeHarness();
  h.sandbox.connectWebSocket('mike');
  const first = h.sockets[0];
  first.open();
  h.advance(60000);                    // let the socket go stale (STALE_AFTER_MS)
  h.sandbox.ensureConnected();         // triggers the replacement
  if (h.liveCount() > 1) throw new Error(`two sockets live immediately after ensureConnected`);
  h.advance(40);                       // still inside the async close
  if (h.liveCount() > 1) throw new Error(`two sockets live during the close window`);
  if (h.sockets.length !== 1) throw new Error(`replacement opened before the old socket closed`);
  h.advance(100);                      // close completes
  if (h.sockets.length !== 2) throw new Error(`no replacement socket after close (${h.sockets.length})`);
  if (first.readyState !== 3) throw new Error('old socket not closed');
});

check('a close that never fires still reconnects, via the timeout fallback', () => {
  const h = makeHarness({ neverClose: true });
  h.sandbox.connectWebSocket('mike');
  h.sockets[0].open();
  h.advance(60000);
  h.sandbox.ensureConnected();
  h.advance(1000);
  if (h.sockets.length !== 1) throw new Error('reconnected before the fallback was due');
  h.advance(1000);                     // past CLOSE_WAIT_MS (1500)
  if (h.sockets.length !== 2) throw new Error('client stranded: no reconnect after a missing close');
});

check('a superseded socket delivering a chunk renders nothing (no doubling)', () => {
  const h = makeHarness();
  h.sandbox.connectWebSocket('mike');
  const first = h.sockets[0];
  first.open();
  h.advance(60000);
  h.sandbox.ensureConnected();
  first.deliver({ type: 'chunk', text: 'hello' });
  h.advance(200);
  const second = h.sockets[1];
  second.open();
  second.deliver({ type: 'chunk', text: 'hello' });
  const chunks = h.sandbox.rendered.filter((m) => m.type === 'chunk');
  if (chunks.length !== 1) throw new Error(`chunk rendered ${chunks.length} times, expected 1`);
});

check('repeated ensureConnected calls during the wait do not stack sockets', () => {
  const h = makeHarness();
  h.sandbox.connectWebSocket('mike');
  h.sockets[0].open();
  h.advance(60000);
  h.sandbox.ensureConnected();
  h.sandbox.ensureConnected();
  h.sandbox.ensureConnected();
  h.advance(5000);
  if (h.sockets.length !== 2) throw new Error(`${h.sockets.length} sockets opened, expected 2`);
});

check('a healthy socket is left alone', () => {
  const h = makeHarness();
  h.sandbox.connectWebSocket('mike');
  h.sockets[0].open();
  h.advance(1000);
  h.sandbox.ensureConnected();
  if (h.sockets.length !== 1) throw new Error('a usable socket was replaced');
});

let failed = 0;
for (const [n, ok, d] of results) {
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${n}`);
  if (!ok) { failed++; console.log(`        ${d}`); }
}
console.log(`\n${results.length - failed} passed, ${failed} failed, ${results.length} total`);
process.exit(failed ? 1 : 0);
