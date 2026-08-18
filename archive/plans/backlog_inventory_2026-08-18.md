# Backlog inventory — 2026-08-18

**Every open `DEV_BACKLOG.md` item in plain language, grouped by what it would actually take to
close it.** That grouping is the answer to "why does this file keep growing", so it is the
organising principle rather than the existing subsections.

*Local file, deliberately. Not published anywhere.*

---

## The finding: a quarter of the backlog is finished work nobody has used yet

**Eleven of the 43 open items are built, deployed and working.** They stay open because closing
each one needs a single ordinary use — one reconnect, one contact correction, one calendar
booking, one Bulgarian reply — and nothing schedules that. The code ships the same day; the
confirmation never gets a slot.

So the file does not grow because work keeps arriving. It grows because **finished work has no
exit.** Each session adds items at the bottom and cannot remove the completed ones at the top, and
every sweep that verifies an item writes more prose onto it rather than taking it out.

Today is a fair sample: two items closed by *running* something rather than building anything, and
the drop-off bug closed within an hour of being filed — by testing it instead of trusting its
description.

| | |
|---:|---|
| **43** | open items |
| **11** | done, waiting on one use |
| **12** | genuinely unbuilt |
| **7** | need a decision from Mike |
| **13** | watch, hold, housekeeping |

---

## 1. Done — waiting on one ordinary use (11)

Built and deployed. Each needs one real exchange to confirm, then it leaves the file.
**This is the pile to attack.**

| Item | What it is | Closes on |
|---|---|---|
| Answers appeared twice when the connection dropped | The app now closes the dying connection before opening a new one | one live reconnect |
| Corrections about other people were rewriting who *you* are | The profile's name field literally read *"Contact name updated from [name] to [name]"*, and that sentence rode in every prompt as the user's name. Data fixed, guard deployed | one contact-name correction, then check the profile is untouched |
| The same person kept accumulating separate contact records | A merge tool now exists; near-matches are flagged before a new record is created | an agent actually resolving one that way — behaviour, not code |
| Bulgarian replies came back in Latin letters, not Cyrillic | Two of three causes eliminated; the translation prompt now demands native script | one reply with the language set |
| Send in one language, receive in another | The feature works | the two checks above and below |
| Old conversation threads now expire | Shipped and deployed | neither keep-alive signal has been measured against real output |
| Writing tone learned from real correspondence | Built and committed | has never read a real mailbox — every test used stubs |
| The monitoring view's newest fields | Deployed; only ever checked by "does it start" | one successful tool call and one deliberately broken one |
| Double-booking protection | Guards every calendar event the tool creates; all 24 tests use a simulated calendar | **blocked in practice** — confirming it means writing junk events to the real calendar |
| Agents told to use tools they were never given | Audit now covers persona files, where a real instance was hiding | ✅ **confirmed on the VM 2026-08-18** — 17 persona files scanned |
| Usage measurement | Built, with the absorbed-work metric | deliberately not reviewed until real daily use — tuning against test traffic would bake in the wrong shape |

---

## 2. Genuinely unbuilt (12)

The only group where "build it" is the answer.

| Item | What it is | State |
|---|---|---|
| Find a venue near a named address | Suggesting a café near a named place. Parked for months behind a GPS question it never needed | **ranked first**, ready to build |
| Southeastern / Greenwich-line trains | No National Rail source was ever built. The Underground works, which is why transit looks finished. The question falls through to a web search that returns nothing and answers anyway | filed 2026-08-18 |
| Which person did you mean? | Four people can share one spoken name. The tool returned the first match with a footnote — so a note could land on the wrong person | ✅ **fixed 2026-08-18** — refuses to pick, offers what distinguishes them, asks. Short forms now recognised |
| Scheduled background jobs ignore quiet hours | A repeating job with notifications on would push at 3am. One job is pinned to 06:45 purely to dodge this | real defect |
| No offline screen | A dead server shows the browser's error page instead of the app | small |
| No way to close out a serious health concern | A flagged clinical thread can never be marked resolved. **Failure direction is the safe one — do not fix by loosening the refusal** | by design, for now |
| A missed statin and a missed anti-psychotic rank the same | Nothing distinguishes a psychiatric medication when deciding urgency | small, specific |
| Speech input in another language | Speaking *out* works. Listening does not: the accurate model cannot produce Cyrillic; the ones that can are 46% wrong or too slow | **held — no viable option**, revisit on a better model, not on a schedule |
| Nothing measures the opportunities the tool *missed* | Every other failure leaves a trace; this one is an absence, so no extra logging recovers it | needs a method |
| Security hardening remainder | Graceful-failure paths, one regression test, two review waves | last wave gated on integrations |
| Faster speech output | 2.8s per phrase | **don't build** until voice has been used enough to say whether that feels slow |
| Move the server to Europe | ~250ms off every voice reply for ~£2/mo, priced for real | a trade, not a bug |

---

## 3. Waiting on a decision (7)

Not blocked on effort — blocked on a judgement nobody else can make. Each sits here indefinitely
until it gets one.

| Item | The decision |
|---|---|
| 39 tool permissions | 35 named-but-not-granted, 4 newly refused. Each a separate call. **Blocks the agent audit Phase 5 sign-off needs** |
| One unfinished ritual arrives as three or four messages | Cause known: asking a question has no memory it was already asked and never answered. **Two earlier diagnoses were confidently wrong**, so the fix is not being guessed at |
| The system logged a preference change it may never have made | It recorded switching output to Latin script; no such setting exists on the VM. Either it wrote somewhere unexamined, or reported doing something it did not do |
| Mailbox as tickets rather than a stream | Blocked on defining what a ticket *is* and how it relates to two overlapping things that already exist |
| Live location as a signal | Continuous location needs a privacy tier before anything is built on it |
| Where should code replace model judgment? | Raised 2026-08-05, never given its own session. ✅ One strand closed 2026-08-18 (contact name matching); archived-entry dedup is untouched |
| Safety tests have never run with a response language set | ⚠ **Corrected 2026-08-18** — the test looks for English words, so running it as written would have failed a *correct* response. The test needs fixing first. Nothing at risk while no language is set |

---

## 4. Housekeeping and infrastructure (13)

Nothing a user would notice. Several are notes-to-self that arguably should not be here.

| Item | Note |
|---|---|
| The Synthesizer read its own reasoning aloud | ✅ **Fixed 2026-08-18.** Measured: the model's private deliberation arrives in the same channel as its answer — no separate stream exists, so no plumbing fix was ever possible. A reply that opens by announcing its own reasoning is now suppressed |
| The VM lost all networking for four hours | Same signature as an earlier incident but without the cause blamed for it — so either that diagnosis was wrong or there are two ways in. **Unresolved** |
| Backlog items declare whether they are pickable | Built. Only items touched since 2026-08-15 carry markers, so the counts are a floor |
| A session cannot tell its own edits from a parallel window's | Two chats on one working tree collide inside the same file. Current check warns but cannot say whose lines are whose |
| File-size limits measured in lines | One file hit its limit with a third of its weight on five very long lines. **Directly relevant to this document's subject** |
| Scheduler can skip but not postpone | Blocked means gone for the day. Correct as-is unless a fixed-time check-in should wait for a lull |
| Hand-maintained list of protected settings | Adding one requires remembering to; nothing detects that you should have |
| Specialists take more internal turns than expected | One takes eight; most unmeasured. **The previous version of this item rested on a measurement that was wrong** |
| No billing export | Not retroactive — switching it on only helps the next anomaly |
| A rules list incomplete by construction | A clean report does not mean nothing was missed |
| Roadmap loads a large section every session | Pure context cost on every start |
| Semantic search inside a knowledge area | Only worth building when an area hits its cap. It has not |
| One dictation readout needs a live check | Verified in code, never spoken to |

---

## 5. Untriaged — written by the running system (6)

**Read each as a symptom, never as a diagnosis.** Three have now named a real problem and guessed
its cause wrongly.

| Item | Note |
|---|---|
| Mike's own email address keeps being transcribed wrong | ×3, his own report. A guard for exactly this exists, so something captures it on a path that guard does not watch. **Establish which path writes it before changing anything** |
| The system assumes his energy is low; he keeps correcting it | ×3. A standing fact re-derived wrongly each time instead of remembered |
| A stated deadline gets ignored and he is chased early | ×4 — **the single most repeated complaint in the log** |
| 24 of 59 stored "facts" are not facts about him | Writing side guarded; the existing bad entries remain |
| The safety test passes without touching stored knowledge | Coverage means adding health entries to the test persona, which changes what the suite measures. A decision, not a chore |
| On failure, say what he can't have and why | His words: *"I can't do that now because xyz"* rather than an error. Scoped in the roadmap under security hardening, where nobody would look for it |

---

## What to do about the growth

1. **Spend one session closing, not building.** Eleven items need one ordinary use each. Most could
   be cleared in a single evening of normal use with someone watching what closes.
2. **Make "done pending confirmation" a state that expires.** If nothing confirms it within a
   fortnight, the item either closes on the strength of its tests or is deleted. Right now it waits
   forever, which is how eleven accumulated.
3. **Stop writing verification prose onto items.** A sweep that checks an item should shorten it or
   remove it. The 2026-08-18 sweep added 146 lines before they were cut back — that is the growth
   mechanism visible in one session.
4. **Two of the items above are about this file.** Line-count limits that stopped tracking real
   cost, and an Inbox that had accumulated six separate notes recording that it had been *emptied*.
   `DEV_BACKLOG.md` has a 450-line ceiling and sits at 1,321.
