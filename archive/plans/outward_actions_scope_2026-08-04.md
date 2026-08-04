# Acting on the user's behalf — scope decision

*Written 2026-08-04, closing item 5 of
[phase5_prompt_2026-08-03_security_web_email.md](phase5_prompt_2026-08-03_security_web_email.md).*
*Status: **proposal — needs Mike's decision on A, B and C before anything is built.***

The plan's instruction was to scope this before building it, and to extend the
Synthesizer's existing autonomy table rather than invent a second framework. This
document does that, and recommends building **one** narrow action.

---

## 1. The framework already exists, and it already covers these cases

`config/agents/synthesizer.md` § *Action tiers* classifies actions by **reversibility and
external effect**, which is the right axis. The three capabilities item 5 names are
already on it — none needs a new category:

| Item 5 capability | Existing tier | Current default |
|---|---|---|
| `send_email` | **Social outreach** | Opt-in, per contact or category |
| Form submission | **Confirm first** / **Expenditure** by what the form does | Confirm first |
| Transactions | **Expenditure** / **Financial action** | Opt-in + per-action confirmation |

And every opt-in in `config/preferences.yaml` is currently `false`:
`expenditure.opt_in`, `financial_actions.opt_in`, `social_outreach.opt_in`,
`bookings.opt_in`. So the effective policy today is already the one item 5 asks for —
*nothing irreversible or outward-facing without explicit per-action confirmation* —
by way of the table's closing line:

> Until opt-in preferences are configured, default to Confirm First for anything beyond
> Inform and autonomous reversible actions.

**Consequence: the policy question is largely settled.** What is not settled is the two
things below, and both are new as of today.

---

## 2. What the table does not cover: **who proposed the action**

The tiers classify actions by *what they do*. They have no axis for *where the intent
came from* — and until today that was fine, because every proposed action originated in
something the user said or in their own logged data.

`fetch_url` and `read_email` change that. Content written by strangers now enters the
pipeline. `<untrusted_content>` marks the **data**, but nothing marks an **action
derived from** that data. By the time a proposal reaches the Synthesizer it is
indistinguishable from an ordinary logistics need:

> An email says *"Your reservation is unconfirmed — reply YES within 24 hours or it will
> be released."* Logistics reads it, correctly identifies a time-sensitive obligation,
> and proposes replying. Every tier in the table is satisfied. The sender wrote the
> urgency, the deadline, and the required reply.

The injection defense shipped today makes this **visible**, not impossible. It is a
boundary marker plus an instruction, and a sufficiently plausible payload can still talk
a model into treating it as a real need — especially one, like the above, that a
legitimate email would word identically.

### Decision A — proposed

> **Provenance modifier.** An action whose *need* is evidenced only by untrusted content
> is **Confirm First**, regardless of which tier it otherwise falls in — including tiers
> that are otherwise autonomous, and including cases where an opt-in is set.
>
> The confirmation must **quote the source**: which email, which page, which invite. The
> user confirms the *evidence*, not just the action. "Shall I reply YES to confirm the
> reservation?" hides exactly the thing they need to see; "This email from
> `bookings@…` says your reservation will be released unless you reply YES — shall I?"
> lets them recognise a message they never expected.
>
> Corollary: an action is **not** externally-originated merely because external content
> is in context. The test is whether the *need* survives without it. "Add milk to the
> list" after the user says they are out of milk is user-originated even if an email was
> read in the same session.

This is one row plus a paragraph in the existing table. No second framework.

---

## 3. The gap that matters more: **the gate is advisory**

Every control described above lives in `config/agents/synthesizer.md`. It is a prompt.
Nothing in Python enforces any of it — verified: no confirmation gate exists in `tools/`
or `core/orchestrator.py`.

This is the same class of control that was already shown not to hold. On 2026-08-03,
`logistics` was not granted `write_agent_config`, its instruction file described the
capability, and it **called the tool three times in production** — the dispatcher
executed each one. Being *told* is not being *prevented*.

`CLAUDE.md` states the principle for the analogous case: *"All sensitive data paths must
be enforced in Python tool code, never in prompts."* Roadmap **B2** requires exactly this
for `write_agent_config` / `write_config` — *"human-in-the-loop confirmation gate in
Python tool code (not a prompt instruction)"*.

### Decision B — proposed

> **No outward-facing tool ships until the confirmation gate is enforced in Python.**
> One choke point, in the tool layer, not per-tool and not in any agent file: an
> outward-facing call returns a `PENDING_CONFIRMATION` token describing what would
> happen, and performs nothing until a subsequent call presents that token plus the
> user's explicit approval from the current conversation.
>
> The gate is what makes the tier table load-bearing. Without it, the tiers are a
> description of intended behaviour that a persuasive email can talk the model out of —
> and the failure is silent, outward-facing and irreversible, which is the combination
> the whole item exists to avoid.

**This is a prerequisite, not a nice-to-have.** It is also small: one function, one token
store, one dispatcher check.

---

## 4. Credentials — explicitly out of scope

The system holds no site credentials. A credential store is its own design question
(storage, encryption at rest under D2's `age` work, scope per site, revocation) and is
**not** a detail of this item. Nothing here should be built in a way that assumes one
arrives later.

Practical consequence: **level-3 agentic browsing — navigate, log in, fill forms,
transact — stays unbuilt.** Not deferred for lack of time; it is gated on a credential
store that does not exist and on Decision B, and it is the capability where a hostile
page stops being able to say things and starts being able to *do* them with the user's
own identity.

---

## 5. Decision C — the one narrow action, proposed

The plan allows *"at most one narrow, confirmed action."* Recommendation:

> **`send_email`, restricted to the user's own address.**

Rationale — it exercises the entire machinery with the blast radius set to zero third
parties:

- **Genuinely useful now.** "Email me that summary", "send me the reading list", "mail
  me the itinerary before I leave" are real requests, and the account is already
  configured and verified for IMAP.
- **Outward-facing enough to be a real test.** It sends mail, leaves the machine, and
  cannot be unsent — so it exercises the Decision B gate honestly rather than rehearsing
  it on something reversible.
- **No third party can be harmed by a mistake, or by a successful injection.** The worst
  outcome of a fully successful prompt injection is that the user receives an email they
  did not ask for. Compare `send_email` to arbitrary recipients, where the same injection
  sends attacker-chosen content, from the user's own address, to anyone.
- **The recipient restriction is enforceable in Python** — a comparison against
  `account_email` in `profile.yaml`, not an instruction an agent can be argued out of.

**Not recommended for this phase:** arbitrary-recipient `send_email`, form submission,
any transaction. Each needs Decision B proven in use first, and the last two need the
credential store.

---

## What this closes, and what it opens

**Closes item 5.** The policy question is answered: the existing tier table already
mandates confirmation for everything item 5 names, and needs one modifier row
(Decision A) to survive the arrival of external content.

**Opens two build items**, in order — filed to `DEV_BACKLOG.md` so they are not lost in
a session narrative:

1. **Python confirmation gate** (Decision B) — prerequisite for any outward action.
   Relates to, and should be built with, B2's `write_agent_config` gate. Same mechanism.
2. **`send_email` to self** (Decision C) — first consumer of the gate.

**Explicitly not opened:** credential store, agentic browsing, arbitrary-recipient mail,
transactions.
