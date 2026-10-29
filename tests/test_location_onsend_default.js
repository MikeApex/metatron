/*
 * tests/test_location_onsend_default.js — [DB-0815-12]: the on-message location ping
 * must be OFF until the user turns it on, and must send nothing while it is off.
 *
 * Mike's ruling, 2026-08-28: location is extra-sensitive, and the first draft ships two
 * capture modes both traceable to a user action, with the on-message ping defaulting off
 * and the off-default confirmed by test after the build. This is that test.
 *
 * The failure it exists to catch is a one-character one. The alert switches next to this
 * code read `localStorage.getItem(k) !== 'off'` — default ON, which is right for them and
 * catastrophic here: a fresh install, a cleared storage, or any unrecognised stored value
 * would start reporting the user's position with nobody having asked for it. A default
 * arrived at by accident is exactly what a tier ruling above "sensitive" forbids.
 *
 * This runs the REAL code: the location section is extracted verbatim from
 * static/index.html and evaluated against fake browser objects. Testing a
 * re-implementation of the default would prove nothing about the shipped file — the same
 * reasoning as tests/test_ws_reconnect_race.js, whose harness style this mirrors.
 *
 * Everything is asserted through what the code DOES — pings posted, controls rendered,
 * storage written — never by reading its internal variable. `let` at the top of a vm
 * script is not reachable from outside it, and a test that needed an accessor added to
 * the shipped file for its own benefit would be testing the accessor.
 *
 *   node tests/test_location_onsend_default.js
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = path.join(__dirname, '..', 'static', 'index.html');
// The choice is per user since 2026-10-29; the harness is signed in as 'mike'.
const KEY = 'metatron_location_onsend_mike';
const LEGACY = 'metatron_location_onsend';
const START = '// --- Location [DB-0815-12] ---';
const END = '// --- end location ---';

const src = fs.readFileSync(HTML, 'utf8');
const a = src.indexOf(START);
const b = src.indexOf(END, a);
if (a < 0 || b < 0) {
  console.error('FAIL  could not locate the location section in static/index.html');
  process.exit(1);
}
const SECTION = src.slice(a, b);

const results = [];
const pending = [];
function check(name, fn) {
  const rec = [name, true, ''];
  results.push(rec);
  try {
    const out = fn();
    if (out && typeof out.then === 'function') {
      pending.push(out.catch((e) => { rec[1] = false; rec[2] = `${e.name}: ${e.message}`; }));
    }
  } catch (e) { rec[1] = false; rec[2] = `${e.name}: ${e.message}`; }
}

// --- a fake browser: storage, DOM, geolocation, and the auth-wrapped fetch -------------

function makeHarness(opts = {}) {
  const { stored = null, position = null, geolocation = true, refused = false,
          legacy = null, persona = 'mike' } = opts;
  const helps = [];                    // showPermissionHelp calls
  const notes = [];                    // addMessage('system', …) calls

  const store = new Map();
  if (stored !== null) store.set(KEY, stored);
  if (legacy !== null) store.set(LEGACY, legacy);

  const posted = [];
  const elements = new Map();
  const handlers = new Map();          // "id:event" -> fn

  function element(id) {
    if (!elements.has(id)) {
      const el = {
        id,
        checked: false,
        disabled: false,
        textContent: '',
        classes: new Set(),
        classList: {
          toggle(cls, on) { on ? el.classes.add(cls) : el.classes.delete(cls); },
        },
        addEventListener(type, fn) { handlers.set(`${id}:${type}`, fn); },
      };
      elements.set(id, el);
    }
    return elements.get(id);
  }

  const sandbox = {
    console, JSON, Promise, Date, Error,
    setTimeout, clearTimeout,
    currentPersona: persona,
    localStorage: {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => store.set(k, String(v)),
      removeItem: (k) => store.delete(k),
    },
    document: { getElementById: (id) => element(id) },
    navigator: geolocation ? {
      geolocation: {
        getCurrentPosition(ok, fail) {
          if (refused) fail(Object.assign(new Error('denied'), { code: 1 }));   // PERMISSION_DENIED
          else if (position) ok(position);
          else fail(new Error('denied'));
        },
      },
    } : {},
    authFetch: async (p, options) => {
      posted.push({ path: p, body: JSON.parse(options.body) });
      return { ok: true, json: async () => ({ zone: 'home', changed: true }) };
    },
  };

  // Defined outside the location section in index.html; the section calls them by typeof.
  sandbox.showPermissionHelp = (kind) => helps.push(kind);
  sandbox.addMessage = (role, text) => notes.push([role, text]);

  vm.createContext(sandbox);
  vm.runInContext(SECTION, sandbox, { filename: 'index.html:location-section' });

  return {
    sandbox, posted, store, element, handlers, helps, notes,
    fire: (id, type, ev) => handlers.get(`${id}:${type}`)(ev || {}),
    // Everything here is fire-and-forget promise work; one macrotask turn settles it.
    settle: () => new Promise((r) => setTimeout(r, 5)),
  };
}

const FIX = { coords: { latitude: 51.5074, longitude: -0.1278, accuracy: 12 },
              timestamp: 1756400000000 };

// --- the off-default -------------------------------------------------------------------

check('a fresh install sends no location when a message is sent', async () => {
  const h = makeHarness({ position: FIX });      // nothing in localStorage at all
  h.sandbox.maybeSendLocationWithMessage();
  await h.settle();
  if (h.posted.length !== 0) throw new Error(`posted ${h.posted.length} pings while off`);
});

check('a fresh install shows the switch off', () => {
  const h = makeHarness();
  if (h.element('loc-onsend').checked !== false) throw new Error('checkbox rendered on');
  if (h.element('loc-toggle').classes.has('on')) throw new Error('toggle rendered active');
  if (!/^Off\./.test(h.element('loc-note').textContent)) {
    throw new Error(`the panel does not say it is off: "${h.element('loc-note').textContent}"`);
  }
});

check('an unrecognised stored value is off, not on', async () => {
  // 'true', '1' and 'yes' are the plausible shapes of a value written by some other
  // version of this code or a hand-edit. Only the exact string 'on' may enable it.
  for (const v of ['true', '1', 'yes', 'ON', '', 'off', 'enabled', 'on ']) {
    const h = makeHarness({ stored: v, position: FIX });
    h.sandbox.maybeSendLocationWithMessage();
    await h.settle();
    if (h.posted.length !== 0) throw new Error(`stored ${JSON.stringify(v)} sent a ping`);
    if (h.element('loc-onsend').checked) throw new Error(`stored ${JSON.stringify(v)} ticked the box`);
  }
});

// --- turning it on is what turns it on --------------------------------------------------

check('only an explicit "on" enables it', async () => {
  const h = makeHarness({ stored: 'on', position: FIX });
  if (!h.element('loc-onsend').checked) throw new Error('an enabled switch rendered off');
  h.sandbox.maybeSendLocationWithMessage();
  await h.settle();
  if (h.posted.length !== 1) throw new Error(`posted ${h.posted.length}, expected 1`);
});

check('ticking the switch persists it, and sends on the next message', async () => {
  const h = makeHarness({ position: FIX });
  h.fire('loc-onsend', 'change', { target: { checked: true } });
  if (h.store.get(KEY) !== 'on') throw new Error('not persisted');
  h.sandbox.maybeSendLocationWithMessage();
  await h.settle();
  if (h.posted.length !== 1) throw new Error(`posted ${h.posted.length}, expected 1`);
});

check('unticking it persists off and stops the pings', async () => {
  const h = makeHarness({ stored: 'on', position: FIX });
  h.fire('loc-onsend', 'change', { target: { checked: false } });
  if (h.store.get(KEY) !== 'off') throw new Error('not persisted as off');
  h.sandbox.maybeSendLocationWithMessage();
  await h.settle();
  if (h.posted.length !== 0) throw new Error('still sending after being switched off');
});

// --- where a reading is allowed to go ---------------------------------------------------

check('the reading goes to /location and travels nowhere else', async () => {
  const h = makeHarness({ stored: 'on', position: FIX });
  h.sandbox.maybeSendLocationWithMessage();
  await h.settle();
  const [ping] = h.posted;
  if (!ping) throw new Error('nothing was posted');
  if (ping.path !== '/location') throw new Error(`posted to ${ping.path}`);
  if (ping.body.lat !== 51.5074 || ping.body.lon !== -0.1278) throw new Error('coordinate mangled');
  if (h.posted.some((p) => p.path !== '/location')) {
    throw new Error('a coordinate reached another endpoint');
  }
});

check('the button shares one reading without switching the recurring mode on', async () => {
  const h = makeHarness({ position: FIX });
  h.fire('loc-share-btn', 'click');
  await h.settle();
  if (h.posted.length !== 1) throw new Error(`button posted ${h.posted.length}, expected 1`);
  if (h.store.has(KEY)) throw new Error('the button wrote the setting');
  h.sandbox.maybeSendLocationWithMessage();
  await h.settle();
  if (h.posted.length !== 1) throw new Error('the button left on-message pings enabled');
});

check('a refused permission sends nothing and says so', async () => {
  const h = makeHarness();                       // no position — getCurrentPosition fails
  h.fire('loc-share-btn', 'click');
  await h.settle();
  if (h.posted.length !== 0) throw new Error('posted despite having no fix');
  if (!/Could not/.test(h.element('loc-note').textContent)) {
    throw new Error('the button failed without telling the user');
  }
});

check('a device with no geolocation at all does not throw on send', async () => {
  const h = makeHarness({ stored: 'on', geolocation: false });
  h.sandbox.maybeSendLocationWithMessage();      // must not throw synchronously
  await h.settle();
  if (h.posted.length !== 0) throw new Error('posted without geolocation');
});

// --- the interview's answer (day planner plan § 8.2, 2026-10-24) -----------------------
// Mike, F1: location on by default for new users, as an opt-OUT asked in the first interview.
// The server reports the persona's answer; the app adopts it only when nothing is stored, and
// only an explicit true turns it on. The 08-28 property — no default arrived at by accident —
// is what these pin.

function serverSays(h, body, ok = true) {
  h.sandbox.authFetch = async (p) => {
    h.posted.push({ path: p, body: null });
    if (body instanceof Error) throw body;
    return { ok, json: async () => body };
  };
}

check('a fresh install adopts the interview\'s yes — and only then sends with messages', async () => {
  const h = makeHarness({ position: FIX });
  serverSays(h, { on_send: true });
  await h.sandbox.adoptServerLocationDefault();
  if (h.store.get(KEY) !== 'on') throw new Error('the yes was not adopted');
  if (!h.element('loc-onsend').checked) throw new Error('the switch did not render on');
});

check('never asked, a no, an error or an odd value all leave a fresh install off', async () => {
  for (const [label, body, ok] of [['null', { on_send: null }, true], ['false', { on_send: false }, true],
                                   ['string', { on_send: 'true' }, true], ['http error', {}, false],
                                   ['throws', new Error('offline'), true]]) {
    const h = makeHarness({ position: FIX });
    serverSays(h, body, ok);
    await h.sandbox.adoptServerLocationDefault();
    if (h.store.has(KEY)) throw new Error(`${label}: wrote the setting`);
    if (h.element('loc-onsend').checked) throw new Error(`${label}: rendered on`);
  }
});

check('a stored choice always wins over the server — off stays off, and nothing is even asked', async () => {
  const h = makeHarness({ stored: 'off', position: FIX });
  serverSays(h, { on_send: true });
  await h.sandbox.adoptServerLocationDefault();
  if (h.store.get(KEY) !== 'off') throw new Error('the server overrode off');
  if (h.posted.length !== 0) throw new Error('asked the server despite a stored choice');
});

check('the server is asked once per load, not on every refresh', async () => {
  const h = makeHarness({ position: FIX });
  serverSays(h, { on_send: null });
  await h.sandbox.adoptServerLocationDefault();
  await h.sandbox.adoptServerLocationDefault();
  if (h.posted.length !== 1) throw new Error(`asked ${h.posted.length} times`);
});

// --- the yes given mid-interview, and a refused permission (2026-10-29) ------------------
// trial_1029 said yes to location inside the first interview, after the once-per-load ask had
// run, and nothing happened. Each interview reply re-arms one more ask; a stored choice still
// means nothing is asked; and a refusal says where to allow it.

check('a yes given after the first ask is adopted on the next interview turn, with a note', async () => {
  const h = makeHarness({ position: FIX });
  serverSays(h, { on_send: null });
  await h.sandbox.adoptServerLocationDefault();          // on load: not asked yet
  serverSays(h, { on_send: true });
  h.sandbox.recheckLocationAfterInterviewTurn();         // the interview reply that recorded yes
  await h.settle();
  if (h.store.get(KEY) !== 'on') throw new Error('the later yes was not adopted');
  if (!h.notes.some(([role, text]) => role === 'system' && /will ask to share your location/.test(text))) {
    throw new Error('no note telling the user the device will ask');
  }
});

check('an interview turn asks nothing when a choice is already stored', async () => {
  const h = makeHarness({ stored: 'off', position: FIX });
  serverSays(h, { on_send: true });
  h.sandbox.recheckLocationAfterInterviewTurn();
  await h.settle();
  if (h.posted.length !== 0) throw new Error('asked the server despite a stored choice');
  if (h.store.get(KEY) !== 'off') throw new Error('the server overrode off');
});

check('a refused permission on send says how to allow it', async () => {
  const h = makeHarness({ stored: 'on', refused: true });
  h.sandbox.maybeSendLocationWithMessage();
  await h.settle();
  if (h.helps.join() !== 'location') throw new Error(`help shown: ${JSON.stringify(h.helps)}`);
  if (h.posted.length !== 0) throw new Error('posted despite the refusal');
});

check('a failed fix that is not a refusal stays silent on send', async () => {
  const h = makeHarness({ stored: 'on' });                 // no position: a plain failure
  h.sandbox.maybeSendLocationWithMessage();
  await h.settle();
  if (h.helps.length !== 0) throw new Error('help shown for a non-refusal');
});

// --- per user, not per browser (2026-10-29) ---------------------------------------------
// One browser-wide key let one person's choice decide another's on a shared device, and kept
// trial_1029's interview yes from ever taking. The old key moves once to whoever is signed in.

check('an old browser-wide choice moves to the signed-in user, once', async () => {
  const h = makeHarness({ legacy: 'on', position: FIX });
  if (h.store.get(KEY) !== 'on') throw new Error('the old choice did not move to mike');
  if (h.store.has(LEGACY)) throw new Error('the old browser-wide key was left behind');
  if (!h.element('loc-onsend').checked) throw new Error('mike lost his on');
});

check('another user on the same browser does not inherit the choice', async () => {
  const h = makeHarness({ stored: 'off', position: FIX });
  h.sandbox.currentPersona = 'trial_1029';
  h.sandbox.loadLocationChoice();
  serverSays(h, { on_send: true });
  await h.sandbox.adoptServerLocationDefault();
  if (h.store.get('metatron_location_onsend_trial_1029') !== 'on') {
    throw new Error("trial_1029's yes was blocked by mike's stored off");
  }
  if (h.store.get(KEY) !== 'off') throw new Error("mike's own choice was changed");
});

check('signing back in restores that user\'s own choice and stops the other\'s pings', async () => {
  const h = makeHarness({ stored: 'off', position: FIX });
  h.store.set('metatron_location_onsend_trial_1029', 'on');
  h.sandbox.currentPersona = 'trial_1029';
  h.sandbox.loadLocationChoice();
  h.sandbox.currentPersona = 'mike';
  h.sandbox.loadLocationChoice();
  h.sandbox.maybeSendLocationWithMessage();
  await h.settle();
  if (h.posted.length !== 0) throw new Error("mike's off was overridden by the previous user's on");
});

// --- nothing runs on its own ------------------------------------------------------------

check('the section starts no timer and no position watcher', async () => {
  // A poll loop is out of bounds by design ([DB-0815-12] point 4: scans fire on zone
  // transitions or scheduled windows, never a poll). Nothing here may run unprompted.
  // Comments are stripped first: the section's own prose explains that it does not call
  // watchPosition, and matching that sentence would fail the check the sentence describes.
  const code = SECTION.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
  if (/setInterval|watchPosition/.test(code)) {
    throw new Error('the location section polls or watches position');
  }
  const h = makeHarness({ stored: 'on', position: FIX });
  await h.settle();
  if (h.posted.length !== 0) throw new Error('a ping was sent merely by loading the app');
});

(async () => {
  await Promise.all(pending);
  let failed = 0;
  for (const [n, ok, d] of results) {
    console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${n}`);
    if (!ok) { failed++; console.log(`        ${d}`); }
  }
  console.log(`\n${results.length - failed} passed, ${failed} failed, ${results.length} total`);
  process.exit(failed ? 1 : 0);
})();
