/*
 * tests/test_client_outbox.js — a message is kept until its reply arrives, and the
 * voice tray holds recordings until Send.
 *
 * Mike, 2026-10-19: "when the web app is offline, if I type a message and send it it
 * goes to the aether but gets erased". The outbox keeps every message from Send until
 * its reply; the tray holds recordings until Send (2026-10-15); headset recordings send
 * themselves (2026-10-23).
 *
 * This runs the REAL code, extracted verbatim from static/index.html — the WebSocket
 * section, the message handler, the message display, the outbox and the tray — against
 * a fake socket, a fake clock and a minimal fake DOM. Testing a re-implementation here
 * would prove nothing; the bugs this file's WebSocket code has produced were all in the
 * interplay between those sections.
 *
 *   node tests/test_client_outbox.js
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const src = fs.readFileSync(path.join(__dirname, '..', 'static', 'index.html'), 'utf8');

function slice(start, end) {
  const a = src.indexOf(start);
  const b = src.indexOf(end, a + start.length);
  if (a < 0 || b < 0) {
    console.error(`FAIL  could not locate "${start}" … "${end}" in static/index.html`);
    process.exit(1);
  }
  return src.slice(a, b);
}

const SECTIONS = [
  slice('// --- Conversation history display ---', '// --- Attachments ---'),
  slice('// --- WebSocket (cross-device sync) ---', '// Android freezes the WebView when the app is backgrounded'),
  slice('function handleWsMessage(msg) {', '// --- API call ---'),
  slice('// --- Outbox ---', '// --- end voice tray ---'),
].join('\n');

// --- a minimal DOM: only what the extracted code touches -------------------
class El {
  constructor(tag) {
    this.tag = tag; this.children = []; this.parentNode = null;
    this.className = ''; this._text = ''; this.title = ''; this.listeners = {};
    this.style = {};
    const self = this;
    this.classList = {
      add(c) { if (!self.className.split(' ').includes(c)) self.className = (self.className + ' ' + c).trim(); },
      remove(c) { self.className = self.className.split(' ').filter((x) => x !== c).join(' '); },
      toggle(c, on) { if (on === undefined ? !this.contains(c) : on) this.add(c); else this.remove(c); },
      contains(c) { return self.className.split(' ').includes(c); },
    };
  }
  get isConnected() { let n = this; while (n.parentNode) n = n.parentNode; return n.isRoot === true; }
  _detach(c) { this.children = this.children.filter((x) => x !== c); c.parentNode = null; }
  appendChild(c) { if (c.parentNode) c.parentNode._detach(c); c.parentNode = this; this.children.push(c); return c; }
  append(...cs) { cs.forEach((c) => this.appendChild(c)); }
  remove() { if (this.parentNode) this.parentNode._detach(this); }
  after(n) {
    const p = this.parentNode;
    if (n.parentNode) n.parentNode._detach(n);
    p.children.splice(p.children.indexOf(this) + 1, 0, n);
    n.parentNode = p;
  }
  get nextSibling() {
    const p = this.parentNode;
    return p ? p.children[p.children.indexOf(this) + 1] || null : null;
  }
  set textContent(t) { this.children.forEach((c) => { c.parentNode = null; }); this.children = []; this._text = String(t); }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(''); }
  set innerHTML(h) { this.textContent = ''; }
  querySelector(sel) {
    const cls = sel.replace(/^\./, '');
    const q = [...this.children];
    while (q.length) {
      const n = q.shift();
      if (n.className.split(' ').includes(cls)) return n;
      q.push(...n.children);
    }
    return null;
  }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
  click() { (this.listeners.click || []).forEach((f) => f()); }
}

function makeHarness() {
  let now = Date.parse('2026-10-23T10:00:00Z');
  const timers = [];
  const sockets = [];
  const spoken = [];
  const transcribeReplies = [];   // queue of {status, transcript} or 'throw'
  let uuid = 0;

  class FakeWebSocket {
    constructor(url) { this.url = url; this.readyState = 0; this.sent = []; this._listeners = []; sockets.push(this); }
    addEventListener(t, f) { if (t === 'close') this._listeners.push(f); }
    send(d) { this.sent.push(JSON.parse(d)); }
    open() { this.readyState = 1; if (this.onopen) this.onopen(); }
    close() { if (this.readyState === 3) return; this.readyState = 2; timers.push([now + 50, () => this.drop()]); }
    drop() { if (this.readyState === 3) return; this.readyState = 3; if (this.onclose) this.onclose(); this._listeners.forEach((f) => f()); }
    deliver(o) { if (this.onmessage) this.onmessage({ data: JSON.stringify(o) }); }
  }
  FakeWebSocket.CONNECTING = 0; FakeWebSocket.OPEN = 1; FakeWebSocket.CLOSING = 2; FakeWebSocket.CLOSED = 3;

  class FakeDate extends Date {
    constructor(...a) { if (a.length) super(...a); else super(now); }
    static now() { return now; }
  }

  const conversation = new El('div');
  conversation.isRoot = true;
  const byId = { 'voice-tray': new El('div') };
  const store = new Map();

  const sandbox = {
    WebSocket: FakeWebSocket, SERVER: 'http://x', authToken: 't', currentPersona: 'mike',
    JSON, Math, console, Date: FakeDate, Promise, Array, Set, Map, String, Error,
    setTimeout: (fn, ms) => { const h = {}; timers.push([now + (ms || 0), fn, h]); return h; },
    clearTimeout: (h) => { const i = timers.findIndex((t) => t[2] === h); if (i >= 0) timers.splice(i, 1); },
    setInterval: () => 0,
    requestAnimationFrame: () => 0,
    crypto: { randomUUID: () => `uuid-${++uuid}` },
    localStorage: {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => store.set(k, String(v)),
      removeItem: (k) => store.delete(k),
    },
    window: { location: { origin: 'http://x' }, addEventListener() {} },
    document: { createElement: (t) => new El(t), getElementById: (id) => byId[id] || (byId[id] = new El('div')) },
    conversation,
    sendBtn: new El('button'),
    providerSelect: { value: '' },
    FormData: class { append() {} },
    // Everything the sections call but do not define:
    setStatus: () => {}, setLoading: () => {}, scrollToBottom: () => {},
    startWorking: () => {}, stopWorking: () => {}, maybeAlert: () => {},
    renderMessageAttachments: () => {}, showTranscript: () => {},
    speakResponse: (t) => spoken.push(t),
    clearAuth: () => {}, showLogin: () => {}, setLoginError: () => {},
    readyAttachments: () => [], clearAttachments: () => {},
    headsetMode: false,
    authFetch: async (url) => {
      if (url.startsWith('/feedback')) return { ok: true };
      const r = transcribeReplies.shift();
      if (!r || r === 'throw') throw new Error('Failed to fetch');
      return { status: r.status || 200, ok: (r.status || 200) < 400, json: async () => ({ transcript: r.transcript }) };
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(SECTIONS, sandbox, { filename: 'index.html:outbox-sections' });
  vm.runInContext(
    'globalThis.__peek = () => ({ outbox, ownBubble, snippets, foreignBubbles, shownIds });',
    sandbox);

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

  // Open a socket through the real connectWebSocket and complete the handshake.
  const connect = (history = []) => {
    sandbox.connectWebSocket('mike');
    const s = sockets[sockets.length - 1];
    s.open();
    s.deliver({ type: 'auth_ok' });
    s.deliver({ type: 'history', messages: history, last_id: 0 });
    return s;
  };
  const sends = (id) => sockets.flatMap((s) => s.sent).filter((f) => f.type === 'send' && (!id || f.exchange_id === id));
  const flush = () => new Promise((r) => setImmediate(r));

  return {
    sandbox, sockets, advance, connect, sends, spoken, store, transcribeReplies, conversation, flush,
    peek: () => sandbox.__peek(),
    stored: () => JSON.parse(store.get('metatron_outbox_mike') || '[]'),
    tray: () => byId['voice-tray'],
  };
}

// ---------------------------------------------------------------------------

const results = [];
async function check(name, fn) {
  try { await fn(); results.push([name, true, '']); }
  catch (e) { results.push([name, false, `${e.name}: ${e.message}`]); }
}
function assert(cond, msg) { if (!cond) throw new Error(msg); }

(async () => {

await check('a message sent with no connection is kept, not dropped', () => {
  const h = makeHarness();
  h.sandbox.queueMessage('pick up the dry cleaning');
  const [e] = h.peek().outbox;
  assert(e && e.input === 'pick up the dry cleaning', 'not in the outbox');
  assert(h.stored().length === 1, 'not persisted — an app close would lose it');
  assert(h.sends().length === 0, 'sent into no socket');
  assert(h.conversation.textContent.includes('Waiting for connection'), 'no "waiting" status on the bubble');
});

await check('it goes by itself once the connection is back', () => {
  const h = makeHarness();
  h.sandbox.queueMessage('pick up the dry cleaning');
  h.connect();
  const sent = h.sends();
  assert(sent.length === 1 && sent[0].input === 'pick up the dry cleaning', `sends: ${JSON.stringify(sent)}`);
  assert(sent[0].source === 'ui', 'source not carried');
});

await check('accepted, then the reply, clears it from storage', () => {
  const h = makeHarness();
  const s = h.connect();
  h.sandbox.queueMessage('hello');
  const id = h.sends()[0].exchange_id;
  s.deliver({ type: 'accepted', exchange_id: id });
  assert(h.peek().outbox[0].state === 'accepted', 'accepted not recorded');
  s.deliver({ type: 'chunk', exchange_id: id, text: 'hi there' });
  s.deliver({ type: 'done', exchange_id: id });
  assert(h.peek().outbox.length === 0 && h.stored().length === 0, 'still owed after its reply');
  assert(h.conversation.textContent.includes('hi there'), 'reply not drawn');
});

await check('a message answered while away is cleared from history, not resent', () => {
  const h = makeHarness();
  h.sandbox.queueMessage('hello');
  const id = h.peek().outbox[0].id;
  // The send got through on a socket that then died; the reply was stored.
  h.peek().outbox[0].state = 'accepted';
  h.connect([{ id: 5, exchange_id: id, user: 'hello', assistant: 'hi', ts: '2026-10-23T10:00:00Z' }]);
  assert(h.sends(id).length === 0, 'resent a message that already has its answer');
  assert(h.peek().outbox.length === 0, 'not cleared by its history row');
});

await check('an error keeps the message but never retries it by itself', () => {
  const h = makeHarness();
  let s = h.connect();
  h.sandbox.queueMessage('hello');
  const id = h.sends()[0].exchange_id;
  s.deliver({ type: 'error', exchange_id: id, text: 'boom' });
  assert(h.peek().outbox[0].state === 'failed', 'not marked failed');
  s.drop();
  h.advance(5000);
  s = h.sockets[h.sockets.length - 1];
  s.open(); s.deliver({ type: 'auth_ok' }); s.deliver({ type: 'history', messages: [], last_id: 0 });
  assert(h.sends(id).length === 1, `retried automatically (${h.sends(id).length} sends)`);
  h.sandbox.releaseEntry(id);   // the Retry tap
  assert(h.sends(id).length === 2, 'Retry did not send it');
});

await check('a message that keeps losing its socket stops after three automatic sends', () => {
  const h = makeHarness();
  h.sandbox.queueMessage('hello');
  const id = h.peek().outbox[0].id;
  for (let i = 0; i < 5; i++) {
    const s = h.connect();
    s.drop();
  }
  assert(h.sends(id).length === 3, `${h.sends(id).length} automatic sends, expected 3`);
  assert(h.peek().outbox[0].state === 'held', 'not held for a tap');
  assert(h.conversation.textContent.includes('Not sent'), 'no "Not sent" status');
});

await check('a message older than fifteen minutes waits for a tap', () => {
  const h = makeHarness();
  h.sandbox.queueMessage('remind me in ten minutes');
  const id = h.peek().outbox[0].id;
  h.advance(16 * 60 * 1000);
  h.connect();
  assert(h.sends(id).length === 0, 'an hour-old message sent itself');
  assert(h.peek().outbox[0].state === 'held', 'not held');
  h.sandbox.releaseEntry(id);
  assert(h.sends(id).length === 1, 'the Send tap did not send it');
});

await check('a late headset message still sends itself, stamped with when it was said', () => {
  const h = makeHarness();
  const said = Date.parse('2026-10-23T10:00:00Z');
  h.sandbox.queueMessage('turn the heating on', { auto: true, recordedAt: said, source: 'headset' });
  h.advance(20 * 60 * 1000);
  h.connect();
  const [f] = h.sends();
  assert(f, 'a headset message was held for a tap nobody can see');
  assert(f.input.startsWith('[') && f.input.endsWith('turn the heating on'), `not stamped: ${f.input}`);
  assert(f.source === 'headset', 'source lost on resend');
});

await check('no acknowledgement means the socket is dead: it reconnects and resends', () => {
  const h = makeHarness();
  h.store.set('metatron_server_acks', 'on');
  h.connect();
  h.sandbox.queueMessage('hello');
  const id = h.sends()[0].exchange_id;
  const before = h.sockets.length;
  h.advance(8000 + 100);   // OUTBOX_ACCEPT_TIMEOUT_MS, then the close
  assert(h.sockets.length === before + 1, 'no replacement socket after a silent send');
  const s = h.sockets[h.sockets.length - 1];
  s.open(); s.deliver({ type: 'auth_ok' }); s.deliver({ type: 'history', messages: [], last_id: 0 });
  assert(h.sends(id).length === 2, 'not resent on the new socket');
});

await check('a server that never acknowledges is not hammered with reconnects', () => {
  const h = makeHarness();   // no metatron_server_acks: a pre-outbox server
  h.connect();
  h.sandbox.queueMessage('hello');
  const before = h.sockets.length;
  h.advance(20000);
  assert(h.sockets.length === before, 'forced a reconnect against a server with no resend guard');
});

await check('a stored row is the reply when the chunks never come', () => {
  const h = makeHarness();
  const s = h.connect();
  h.sandbox.queueMessage('hello');
  const id = h.sends()[0].exchange_id;
  s.deliver({ type: 'accepted', exchange_id: id });
  s.deliver({ type: 'message', id: 9, exchange_id: id, user: 'hello', assistant: 'late reply', ts: '2026-10-23T10:00:00Z' });
  assert(h.peek().ownBubble === null, 'the reply bubble was left waiting');
  assert(h.conversation.textContent.includes('late reply'), 'reply not drawn');
  assert(h.peek().outbox.length === 0, 'still owed');
});

await check('two queued messages go one at a time, in order, each reply under its own message', () => {
  const h = makeHarness();
  h.sandbox.queueMessage('first');
  h.sandbox.queueMessage('second');
  const s = h.connect();
  assert(h.sends().length === 1 && h.sends()[0].input === 'first', 'not one at a time');
  const a = h.sends()[0].exchange_id;
  s.deliver({ type: 'chunk', exchange_id: a, text: 'reply one' });
  // While 'second' is still queued, reply one must sit directly under 'first'.
  const rows = h.conversation.children.map((r) => r.textContent);
  const iFirst = rows.findIndex((t) => t.startsWith('first'));
  assert(rows[iFirst + 1] && rows[iFirst + 1].includes('reply one'), `reply misplaced: ${JSON.stringify(rows)}`);
  s.deliver({ type: 'done', exchange_id: a });
  assert(h.sends().length === 2 && h.sends()[1].input === 'second', 'second not sent after the first reply');
});

await check('our own resent message is not drawn as another device\'s', () => {
  const h = makeHarness();
  h.sandbox.queueMessage('hello');
  const id = h.peek().outbox[0].id;
  h.sandbox.connectWebSocket('mike');
  const s = h.sockets[0];
  s.open();
  s.deliver({ type: 'auth_ok' });
  s.deliver({ type: 'stream_start', exchange_id: id, user: 'hello' });
  assert(!h.peek().foreignBubbles.has(id), 'drawn as a foreign exchange');
});

await check('a late frame for an earlier message never lands in the current reply', () => {
  // Review finding, 2026-10-23: two of this device's exchanges can be live at once now.
  const h = makeHarness();
  h.sandbox.queueMessage('first');
  h.sandbox.queueMessage('second');
  let s = h.connect();
  const a = h.sends()[0].exchange_id;
  // 'first' keeps losing its socket while the server is still running it, until held.
  for (let i = 0; i < 2; i++) { s.drop(); s = h.connect(); }
  s.drop();
  s = h.connect();
  const b = h.sends().find((f) => f.input === 'second').exchange_id;
  assert(h.peek().outbox.find((e) => e.id === a).state === 'held', 'first not held');
  // The server finishes 'first' and broadcasts it, while 'second' holds the bubble.
  s.deliver({ type: 'chunk', exchange_id: a, text: 'REPLY ONE' });
  s.deliver({ type: 'done', exchange_id: a });
  assert(!h.peek().ownBubble.textContent.includes('REPLY ONE'), 'reply one written into reply two');
  assert(h.spoken.length === 0, 'spoke the wrong reply');
  assert(h.sends(b).length === 1, `second resent (${h.sends(b).length} sends)`);
  s.deliver({ type: 'message', id: 7, exchange_id: a, user: 'first', assistant: 'REPLY ONE', ts: '2026-10-23T10:00:00Z' });
  const rows = h.conversation.children.map((r) => r.textContent);
  const iFirst = rows.findIndex((t) => t.startsWith('first'));
  assert(rows[iFirst + 1] && rows[iFirst + 1].includes('REPLY ONE'), `reply one not under first: ${JSON.stringify(rows)}`);
  assert(!h.peek().outbox.find((e) => e.id === a), 'first still owed after its row');
});

await check('nothing is sent on a socket that has not finished signing in', () => {
  // A send before auth is read by the server as a failed auth frame: signed out.
  const h = makeHarness();
  h.sandbox.connectWebSocket('mike');
  const s = h.sockets[0];
  s.open();                                  // OPEN, but no auth_ok / history yet
  h.sandbox.queueMessage('hello');
  assert(h.sends().length === 0, 'sent before the socket authenticated');
  s.deliver({ type: 'auth_ok' });
  s.deliver({ type: 'history', messages: [], last_id: 0 });
  assert(h.sends().length === 1, 'not sent once authenticated');
});

await check('a recording that hit a server error is retried with the connection still up', async () => {
  const h = makeHarness();
  h.connect();
  h.transcribeReplies.push({ status: 500 });
  h.sandbox.addSnippet({}, Date.now(), false, 'ui');
  h.sandbox.addSnippet({}, Date.now(), false, 'ui');
  await h.flush(); await h.flush();
  const states = h.peek().snippets.map((x) => x.state);
  assert(states.every((x) => x === 'waiting'), `queued recording left "Transcribing…" with nothing in flight: ${states}`);
  h.transcribeReplies.push({ transcript: 'one' }, { transcript: 'two' });
  h.advance(30000);
  for (let i = 0; i < 6; i++) await h.flush();
  const after = h.peek().snippets.map((x) => x.state);
  assert(after.every((x) => x === 'ready'), `not retried without a reconnect: ${after}`);
});

await check('a recording the server keeps failing on stops being re-uploaded, and keeps its audio', async () => {
  const h = makeHarness();
  h.connect();
  for (let i = 0; i < 5; i++) h.transcribeReplies.push({ status: 500 });
  h.sandbox.addSnippet({}, Date.now(), false, 'ui');
  await h.flush(); await h.flush();
  for (let i = 0; i < 6; i++) { h.advance(30000); for (let j = 0; j < 6; j++) await h.flush(); }
  const [sn] = h.peek().snippets;
  assert(sn.state === 'failed' && sn.retryable, `state ${sn.state} after five server errors`);
  assert(h.transcribeReplies.length === 0, 'fewer uploads than the cap');
  h.transcribeReplies.push({ transcript: 'finally' });
  h.advance(5 * 60 * 1000);
  for (let j = 0; j < 6; j++) await h.flush();
  assert(h.peek().snippets[0].state === 'failed', 'kept re-uploading past the cap');
  h.tray().children[0].children[1].click();   // the tap
  for (let j = 0; j < 6; j++) await h.flush();
  assert(h.peek().snippets[0].state === 'ready', 'the tap did not retry it');
});

await check('a message sent into a dead connection says it is waiting, not sending', () => {
  // Mike's phone check 2, 2026-10-23: airplane mode, Send, kill, reopen — "Sending…" throughout.
  const h = makeHarness();
  h.connect();
  h.sandbox.navigator = { onLine: false };   // airplane mode; the socket still reads OPEN
  h.sandbox.queueMessage('hello');
  assert(h.sends().length === 0, 'sent into a connection the device says is offline');
  assert(h.conversation.textContent.includes('Waiting for connection'), 'queued message not labelled waiting');
  h.sandbox.navigator = { onLine: true };
  const h2 = makeHarness();                   // the reopened app, holding an in-flight message
  h2.store.set('metatron_outbox_mike', JSON.stringify([{ id: 'x', input: 'hi', state: 'sent', sends: 1, writtenAt: Date.now(), attachments: [] }]));
  h2.sandbox.loadOutbox();
  assert(h2.conversation.textContent.includes('Waiting for connection'), `reopened app says: ${h2.conversation.textContent}`);
});

await check('a batch is one paragraph per recording, each stamped with when it was recorded', () => {
  const h = makeHarness();
  const t0 = Date.parse('2026-10-23T09:00:00Z');
  const out = h.sandbox.composeBatch(
    [{ recordedAt: t0, text: 'one' }, { recordedAt: t0 + 3600e3, text: 'two' }], 'typed');
  const parts = out.split('\n\n');
  assert(parts.length === 3, `paragraphs: ${JSON.stringify(parts)}`);
  assert(/^\[.+\] one$/.test(parts[0]) && /^\[.+\] two$/.test(parts[1]), `not stamped: ${out}`);
  assert(parts[0] !== parts[1].replace('two', 'one'), 'both stamped with the same time');
  assert(parts[2] === 'typed', 'typed text should follow, unstamped');
  const single = h.sandbox.composeBatch([{ recordedAt: Date.now(), text: 'just this' }], '');
  assert(single === 'just this', `a fresh single recording was altered: ${single}`);
});

await check('a recording lands in the tray, transcribes, and can be deleted', async () => {
  const h = makeHarness();
  h.transcribeReplies.push({ transcript: 'buy milk' });
  h.sandbox.addSnippet({}, Date.now(), false, 'ui');
  await h.flush(); await h.flush();
  const [sn] = h.peek().snippets;
  assert(sn && sn.state === 'ready' && sn.text === 'buy milk', `snippet: ${JSON.stringify(sn)}`);
  assert(h.tray().textContent.includes('buy milk'), 'not shown in the tray');
  assert(h.sends().length === 0, 'an on-screen recording sent itself');
  h.sandbox.removeSnippet(sn);
  assert(h.peek().snippets.length === 0 && !h.tray().textContent.includes('buy milk'), 'not deleted');
});

await check('a headset recording sends itself once transcribed', async () => {
  const h = makeHarness();
  h.connect();
  h.transcribeReplies.push({ transcript: 'what is on today' });
  h.sandbox.addSnippet({}, Date.now(), true, 'headset');
  await h.flush(); await h.flush();
  const [f] = h.sends();
  assert(f && f.input === 'what is on today' && f.source === 'headset', `sends: ${JSON.stringify(h.sends())}`);
  assert(h.peek().snippets.length === 0, 'left in the tray');
});

await check('a headset recording made offline waits, then sends itself on reconnect', async () => {
  const h = makeHarness();
  h.transcribeReplies.push('throw');
  h.sandbox.addSnippet({}, Date.now(), true, 'headset');
  await h.flush(); await h.flush();
  assert(h.peek().snippets[0].state === 'waiting', 'not waiting for the connection');
  h.transcribeReplies.push({ transcript: 'call the plumber' });
  h.connect();
  await h.flush(); await h.flush();
  const f = h.sends().find((x) => x.input === 'call the plumber');
  assert(f, `not sent on reconnect: ${JSON.stringify(h.sends())}`);
});

await check('a busy transcriber is retried, not reported as a failure', async () => {
  const h = makeHarness();
  h.transcribeReplies.push({ status: 503 }, { transcript: 'later' });
  h.sandbox.addSnippet({}, Date.now(), false, 'ui');
  await h.flush(); await h.flush();
  assert(h.peek().snippets[0].state === 'pending', `state after 503: ${h.peek().snippets[0].state}`);
  h.advance(3000);
  await h.flush(); await h.flush();
  assert(h.peek().snippets[0].state === 'ready', 'not retried after the busy reply');
});

let failed = 0;
for (const [n, ok, d] of results) {
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${n}`);
  if (!ok) { failed++; console.log(`        ${d}`); }
}
console.log(`\n${results.length - failed} passed, ${failed} failed, ${results.length} total`);
process.exit(failed ? 1 : 0);
})();
