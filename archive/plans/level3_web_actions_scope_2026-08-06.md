# Level 3 web access — scoping decision

*Written 2026-08-06, prompted by the pre-departure travel-check work: `fetch_url` returned
an empty JS app shell for Heathrow's arrivals page and BA's flight-status page, and Mike
asked why the system can't just browse its way to the answer.*
*Status: **proposal — needs a decision on the two phases below before anything is built.***

Same instruction as the 2026-08-04 outward-actions scoping
([outward_actions_scope_2026-08-04.md](outward_actions_scope_2026-08-04.md)): scope before
building, extend the existing action-tier and confirm-gate machinery rather than invent a
second framework, and this document follows that one's shape.

---

## 1. The actual gap is smaller than "Level 3"

`fetch_url` does a plain GET and returns page content — no JS execution. That was sufficient
for email, articles, and static pages, but Heathrow's arrivals page is a client-side app:
1.1 MB of HTML fetched directly and only 3 incidental matches for anything flight-shaped —
the real data loads after the page runs its own JavaScript against an API endpoint that
isn't in the static source. BA's generic flight-status URL behaves the same way.

That is a **rendering** gap, not an **action** gap. Two genuinely different capabilities are
both being called "browsing the way to an answer," and they carry very different risk:

| Capability | What it does | New risk it introduces |
|---|---|---|
| **Rendered read** (call it Level 2.5 — this doc's recommendation) | Load a page in a headless browser, let its JS run, extract the resulting text/DOM. Never clicks, types, or submits anything. | The extracted text is a bigger, JS-generated version of what `fetch_url` already returns — same trust boundary, same `<untrusted_content>` wrapping, no new action surface. |
| **Level 3 proper** (interactive) | Click, type, fill forms, log in, submit, transact — the page can make the model *do* things using the user's identity. | A hostile page stops being limited to *saying* things and can *act*. Needs a credential store, per-action confirmation, and a domain policy — none of which exist. |

**Recommendation: build the rendering half now (scoped below); leave interactive Level 3
explicitly unbuilt**, same disposition the 2026-08-04 document gave it, for the same reason —
gated on a credential store that does not exist. Rendering a public flight-status page needs
no login and no credential story at all.

---

## 2. Decision A — build a rendered-read tool, not full Level 3

> **New tool, `fetch_rendered(url)`** (name to be finalized in `tools/browser.py`): opens the
> URL in a headless browser, waits for the network to go idle (a fixed timeout, not an
> indefinite wait — see §5), extracts visible text from the resulting DOM, and returns it
> wrapped in `<untrusted_content>` exactly like `fetch_url` does today. **Never clicks,
> types, submits, or follows a redirect the user didn't ask for.** No login. No forms.
>
> This is additive to `fetch_url`, not a replacement — `fetch_url` stays the default for
> ordinary pages (cheaper, faster, no browser process); `fetch_rendered` is what an agent
> reaches for when a plain fetch comes back looking like an app shell (e.g. near-empty
> extracted text on a page that should have content).

This is Inform-tier under the existing action table — it only reads, so it needs no
confirmation to run. The output still goes through the same injection-marker scan
(`tools/untrusted.py`) as every other external-content tool, because a JS-rendered page is
written by the same stranger a static one is.

---

## 3. Decision B — the technology choice

**Playwright for Python**, headless Chromium, single global instance rather than
per-request spin-up.

Why, against the alternatives actually available:

- **Selenium** — older, heavier API, weaker built-in network-idle detection (the exact thing
  needed to know when a SPA has finished loading its data).
- **Puppeteer** — Node-only; this codebase is Python end to end, and adding a Node runtime
  for one tool is a second language to operate and patch for a single capability.
- **Playwright** — actively maintained (Microsoft), Python-native async API, built-in
  `wait_for_load_state("networkidle")` which is precisely "wait until the SPA's API calls have
  resolved," and a documented headless mode that keeps memory bounded.

**Resource shape on the VM:** a headless Chromium process runs ~150–300 MB resident. The
current `e2-medium` (4 GB) already carries the server, scheduler, and whatever Ollama-adjacent
processes are live locally. **Before building:** check actual headroom under load
(`free -h` on the VM during a normal session), and enforce a **single global browser instance
with a lock** — one page open at a time, not one per concurrent request — so a burst of
proactive checks can't spawn multiple Chromium processes and starve the server. A hard
per-call timeout (10–15s) prevents one hung page from blocking every other agent indefinitely.

---

## 4. Decision C — what stays out of scope, explicitly

Carried forward unchanged from 2026-08-04, because nothing here changes it:

- **No credential store exists.** `fetch_rendered` therefore only ever reaches pages that need
  no login — public flight-status pages, public transit pages, public product pages. Any page
  behind auth is out of reach until D2's `age`-encrypted credential story is designed and
  built, and that is its own scoping document, not a paragraph here.
- **No clicking, typing, or submitting.** Interactive Level 3 is not "the same tool with a few
  more methods" — every one of those actions needs the confirm-gate wired to it (extending
  `tools/confirm.py`, same mechanism as `send_email`/`write_config`, not a new one), plus a
  domain allowlist so a hostile redirect chain can't walk the browser somewhere unintended,
  plus a decision on whether an in-page action counts as "externally originated" under the
  2026-08-04 provenance modifier (it does, by that document's own test — the need to click
  would be evidenced only by the page itself).
- **No arbitrary navigation from model-generated URLs to sites the user didn't name.** The
  provenance-modifier reasoning applies here too: a page that tells the model "next, go to
  `evil.example/confirm`" is exactly the injection case `<untrusted_content>` exists for. The
  rendered-read tool takes a URL as an argument the same way `fetch_url` does — the caller
  (Logistics, Research) supplies it, the tool does not follow links autonomously.

---

## 5. Failure modes worth naming before building, not after

- **Indefinite hang.** A page that never reaches network-idle (ad-tech pages, infinite
  polling widgets) must time out and return a partial-or-error result, not block the caller.
- **Memory leak across calls.** Reuse one browser context, close pages after each call,
  restart the browser process on a schedule (e.g. daily) rather than trusting long-run
  stability of a Chromium process under a scheduler that fires it repeatedly.
- **CAPTCHA / bot-detection walls.** Some sites will detect headless Chromium and block it
  outright. This is an expected failure, not a bug to chase — the tool should return a clear
  "page would not render, likely bot-blocked" result rather than an opaque timeout, so the
  calling agent can say so honestly (matches the existing "when the tool isn't built yet"
  gap-surfacing pattern in `synthesizer.md`) instead of claiming no data exists.
- **Injection surface is larger, not different in kind.** A rendered page can contain far more
  text (ads, unrelated site chrome, comment sections) than a curated static fetch. The
  existing `contains_injection_markers()` scan still applies, but the false-positive rate
  should be checked against a few real rendered pages before this ships, the same way the
  output filter's Exchange 027 false positive is a documented, accepted gap rather than a
  surprise.

---

## What this closes, and what it opens

**Closes** the immediate question: the flight-status pages don't need interactive Level 3,
they need a rendering capability that stays read-only and inherits every existing
trust-boundary control. That is a much smaller, much lower-risk build than "give Metatron a
browser it can act with."

**Opens one build item**, filed to `DEV_BACKLOG.md` so it isn't lost in a session narrative:

1. **`tools/browser.py` — `fetch_rendered(url)`**, Playwright/headless Chromium, single
   global instance + lock, 10–15s timeout, `<untrusted_content>` wrapping, granted to
   Logistics and Research alongside `fetch_url`. Prerequisite check: confirm actual VM memory
   headroom before installing Chromium's dependency set.

**Explicitly not opened:** interactive Level 3 (click/type/submit/login), a credential store,
a domain allowlist for autonomous navigation. Each is its own decision, gated on work that
doesn't exist yet, same as 2026-08-04 left them.
