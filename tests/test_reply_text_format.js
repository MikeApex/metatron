/*
 * tests/test_reply_text_format.js — a reply reads as text, with its line breaks, on screen and
 * aloud (2026-10-29).
 *
 * trial_1029's purpose draft arrived as "> **Purpose:**" with the > and ** shown literally, and
 * numbered questions ran together because the assistant bubble collapsed line breaks. The
 * agents now put several questions on bulleted lines; replyText() is what the bubble shows and
 * speechText() is what /tts is sent. This runs the REAL functions, extracted verbatim from
 * static/index.html, as tests/test_location_onsend_default.js does for its section.
 *
 *   node tests/test_reply_text_format.js
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'index.html'), 'utf8');
const a = html.indexOf('  function replyText(md) {');
const b = html.indexOf('  const permissionHelpShown', a);
if (a < 0 || b < 0) {
  console.error('FAIL  could not locate replyText/speechText in static/index.html');
  process.exit(1);
}
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(html.slice(a, b), sandbox);

// The 13:46 reply, as stored.
const REPLY = [
  "Based on what you've shared, I've put together a first draft:",
  '',
  '> **Purpose:**  ',
  '> Reclaim a vibrant, autonomous, and connected daily lifestyle.',
  '',
  'To help me protect your time:',
  '',
  '1. **Focus vs. admin windows:** When are you pulled into meetings?',
  '2. **Fixed routines:** Any standing daily routines?',
  '- When could a first run fit?',
  '* And a second bullet style?',
  '## A heading',
].join('\n');

const results = [];
function check(name, ok, detail = '') { results.push([name, !!ok, detail]); }

const shown = sandbox.replyText(REPLY);
check('no ** survives on screen', !shown.includes('**'), shown);
check('no quote marker survives on screen', !/^\s*>/m.test(shown), shown);
check('no heading marker survives on screen', !/^\s*#/m.test(shown), shown);
check('bullets show as •', shown.includes('• When could a first run fit?')
      && shown.includes('• And a second bullet style?'), shown);
check('numbered lines keep their numbers, each on its own line',
      /\n1\. Focus vs\. admin windows: When/.test(shown) && /\n2\. Fixed routines:/.test(shown), shown);
check('line breaks are kept', shown.split('\n').length === REPLY.split('\n').length);
check('ordinary prose is untouched',
      sandbox.replyText('Plain words, 3 * 4 = 12, and a -dash.') === 'Plain words, 3 * 4 = 12, and a -dash.');
check('empty and missing text are empty', sandbox.replyText('') === '' && sandbox.replyText(null) === '');

const spoken = sandbox.speechText(REPLY);
check('nothing spoken is a marker', !/[•*>#]/.test(spoken) && !/^\s*\d+[.)]\s/m.test(spoken), spoken);
check('each item is still its own line aloud', spoken.includes('\nWhen could a first run fit?'), spoken);
check('no blank lines are sent to the voice', !/\n\n/.test(spoken), spoken);

let failed = 0;
for (const [n, ok, d] of results) {
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${n}`);
  if (!ok) { failed++; console.log(`        ${JSON.stringify(d).slice(0, 300)}`); }
}
console.log(`\n${results.length - failed} passed, ${failed} failed, ${results.length} total`);
process.exit(failed ? 1 : 0);
