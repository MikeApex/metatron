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
  const { stored = null, position = null, geolocation = true } = opts;

  const store = new Map();
  if (stored !== null) store.set('metatron_location_onsend', stored);

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
    currentPersona: 'mike',
    localStorage: {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => store.set(k, String(v)),
      removeItem: (k) => store.delete(k),
    },
    document: { getElementById: (id) => element(id) },
    navigator: geolocation ? {
      geolocation: {
        getCurrentPosition(ok, fail) {
          if (position) ok(position);
          else fail(new Error('denied'));
        },
      },
    } : {},
    authFetch: async (p, options) => {
      posted.push({ path: p, body: JSON.parse(options.body) });
      return { ok: true, json: async () => ({ zone: 'home', changed: true }) };
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(SECTION, sandbox, { filename: 'index.html:location-section' });

  return {
    sandbox, posted, store, element, handlers,
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
  if (h.store.get('metatron_location_onsend') !== 'on') throw new Error('not persisted');
  h.sandbox.maybeSendLocationWithMessage();
  await h.settle();
  if (h.posted.length !== 1) throw new Error(`posted ${h.posted.length}, expected 1`);
});

check('unticking it persists off and stops the pings', async () => {
  const h = makeHarness({ stored: 'on', position: FIX });
  h.fire('loc-onsend', 'change', { target: { checked: false } });
  if (h.store.get('metatron_location_onsend') !== 'off') throw new Error('not persisted as off');
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
  if (h.store.has('metatron_location_onsend')) throw new Error('the button wrote the setting');
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
