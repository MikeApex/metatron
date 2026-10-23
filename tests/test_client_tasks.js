/*
 * tests/test_client_tasks.js — the Today panel and the correspondence suggestion bar.
 *
 * Plan: archive/plans/task_ledger_plan_2026-10-23.md § 6. The review's last finding was a
 * swap under the finger: the approval bar's Approve posts whatever `pendingToken` holds at
 * click time, so a suggestion drawn in that bar could have approved a card that arrived
 * between polls. The suggestion therefore has its own bar, and every button carries the id it
 * was drawn for. This runs the REAL section of static/index.html against a minimal fake DOM.
 *
 *   node tests/test_client_tasks.js
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const src = fs.readFileSync(path.join(__dirname, '..', 'static', 'index.html'), 'utf8');
const START = "// --- Today's tasks, and closes suggested by correspondence";
const END = 'setTimeout(() => { refreshProposal(); refreshTasks(); }, 3000);';
const a = src.indexOf(START);
const b = src.indexOf(END, a);
if (a < 0 || b < 0) { console.error('FAIL  could not locate the tasks section'); process.exit(1); }
const SECTION = src.slice(a, b);

class El {
  constructor(tag, id) {
    this.tag = tag; this.id = id || ''; this.children = []; this.parentNode = null;
    this.className = ''; this.textContent = ''; this.dataset = {}; this.disabled = false;
    this.listeners = {};
    const self = this;
    this.classList = {
      add(c) { if (!self.className.split(' ').includes(c)) self.className = (self.className + ' ' + c).trim(); },
      remove(c) { self.className = self.className.split(' ').filter((x) => x && x !== c).join(' '); },
      toggle(c, on) { if (on === undefined ? !this.contains(c) : on) this.add(c); else this.remove(c); },
      contains(c) { return self.className.split(' ').includes(c); },
    };
  }
  set innerHTML(_v) { this.children.forEach((c) => { c.parentNode = null; }); this.children = []; }
  appendChild(c) { c.parentNode = this; this.children.push(c); return c; }
  append(...cs) { cs.forEach((c) => this.appendChild(c)); }
  remove() { if (this.parentNode) this.parentNode.children = this.parentNode.children.filter((x) => x !== this); this.parentNode = null; }
  addEventListener(ev, fn) { (this.listeners[ev] = this.listeners[ev] || []).push(fn); }
  click() { (this.listeners.click || []).forEach((fn) => fn()); }
  cloneNode() { const n = new El(this.tag, this.id); n.className = this.className; n.textContent = this.textContent; return n; }
  replaceWith(n) { byId[this.id] = n; }
  querySelectorAll(sel) {
    const out = []; const walk = (e) => { e.children.forEach((c) => { if (sel === 'button' && c.tag === 'button') out.push(c); walk(c); }); };
    walk(this); return out;
  }
}
const byId = {};
for (const id of ['tasks-toggle', 'tasks-panel', 'tasks-list', 'task-proposal-bar', 'task-proposal-text',
                  'task-proposal-yes', 'task-proposal-no', 'confirm-bar']) {
  byId[id] = new El(id.endsWith('yes') || id.endsWith('no') || id === 'tasks-toggle' ? 'button' : 'div', id);
}

const calls = [];
let nextResponse = { ok: true, body: {} };
const status = [];
const sandbox = {
  document: { getElementById: (id) => byId[id], createElement: (t) => new El(t) },
  currentPersona: 'mike', authToken: 't', pendingToken: 'CARD-TOKEN',
  authFetch: async (url, opts) => {
    calls.push({ url, body: opts && opts.body ? JSON.parse(opts.body) : null });
    const r = nextResponse;
    return { ok: r.ok, json: async () => r.body };
  },
  setStatus: (msg) => status.push(msg),
  setInterval: () => 0, setTimeout: () => 0, console,
};
vm.createContext(sandbox);
vm.runInContext(SECTION + '\nthis.__t = { renderTasks, renderProposal, refreshProposal, actOnTask };', sandbox);
const T = sandbox.__t;
const flush = () => new Promise((r) => setImmediate(r));

const results = [];
async function check(name, fn) {
  try { await fn(); results.push([name, true, '']); } catch (e) { results.push([name, false, e.message]); }
}
function assert(c, m) { if (!c) throw new Error(m || 'assertion failed'); }

(async () => {
  await check('a suggestion\'s Mark done posts the proposal it was drawn for, never a card token', async () => {
    calls.length = 0;
    T.renderProposal({ proposal_id: 'pr_1', task_id: 'ob_1', what: 'Return e-file pages', sender: 'S.A.R.', subject: 'Re: pages', received: '2026-10-24' });
    sandbox.pendingToken = 'A-DIFFERENT-CARD';
    byId['task-proposal-yes'].click();
    await flush();
    const posts = calls.filter((c) => c.body);
    assert(posts.length === 1 && posts[0].url === '/tasks/act', JSON.stringify(calls));
    assert(posts[0].body.proposal_id === 'pr_1', JSON.stringify(posts[0].body));
    assert(!JSON.stringify(posts[0].body).includes('CARD'), 'no confirm token may travel');
  });

  await check('a redraw for a new suggestion leaves no handler from the old one', async () => {
    calls.length = 0;
    T.renderProposal({ proposal_id: 'pr_2', task_id: 'ob_2', what: 'Sirva inspection', subject: 'x' });
    const stale = byId['task-proposal-yes'];
    T.renderProposal({ proposal_id: 'pr_3', task_id: 'ob_3', what: 'Bupa physio', subject: 'y' });
    stale.click();             // the replaced node — it must still answer only pr_2
    byId['task-proposal-no'].click();
    await flush();
    const posts = calls.filter((c) => c.body);
    const ids = posts.map((c) => c.body.proposal_id);
    assert(ids.includes('pr_3') && posts.find((c) => c.body.proposal_id === 'pr_3').url === '/tasks/proposals/decline', JSON.stringify(calls));
    assert(!ids.some((x) => x !== 'pr_2' && x !== 'pr_3'), JSON.stringify(ids));
  });

  await check('the suggestion bar stays hidden while an approval card is showing', async () => {
    calls.length = 0;
    byId['confirm-bar'].classList.add('shown');
    byId['task-proposal-bar'].classList.add('shown');
    await T.refreshProposal();
    assert(!byId['task-proposal-bar'].classList.contains('shown'), 'hidden behind the card');
    assert(calls.length === 0, 'not even fetched while a card is up');
    byId['confirm-bar'].classList.remove('shown');
  });

  await check('Today rows tap with their own task id; a refused close stays on screen as a failure', async () => {
    calls.length = 0; status.length = 0;
    T.renderTasks([
      { task_id: 'ob_a', what: 'Pay Chase bill', label: 'overdue since 2026-10-17', actions: ['done', 'dismissed'] },
      { task_id: 'ob_b', what: 'Stretching', label: 'today', actions: ['done', 'skipped'] },
    ]);
    const list = byId['tasks-list'];
    assert(list.children.length === 2, 'two rows');
    assert(byId['tasks-toggle'].textContent === '✓ Today (2)', byId['tasks-toggle'].textContent);
    nextResponse = { ok: false, body: { detail: 'error: no task with id' } };
    const row = list.children[1];
    row.querySelectorAll('button')[0].click();
    await flush(); await flush();
    assert(calls[0].body.task_id === 'ob_b' && calls[0].body.action === 'done', JSON.stringify(calls[0]));
    assert(row.parentNode === list, 'a refused close is not removed as if done');
    assert(status[0] && status[0].startsWith('error'), JSON.stringify(status));
    assert(!row.querySelectorAll('button')[0].disabled, 'buttons come back for a retry');
    nextResponse = { ok: true, body: {} };
  });

  const passed = results.filter((r) => r[1]).length;
  for (const [n, ok, d] of results) console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${n}${d ? '\n        ' + d : ''}`);
  console.log(`\n${passed} passed, ${results.length - passed} failed, ${results.length} total`);
  process.exit(passed === results.length ? 0 : 1);
})();
