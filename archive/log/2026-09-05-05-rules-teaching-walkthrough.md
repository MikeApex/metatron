### 2026-09-05 (rules-teaching walkthrough — intake goes 1/33 → 11/33, and the direction it was ruled on runs out)

The fifth session of the day, and the (M)-walkthrough the fourth one wrote the prompt for.
Mike present throughout, ruling sender by sender; the session prepared each step and executed
his word. `[DB-0820-03]` closed, `[DB-0905-01]` filed on his explicit go-ahead. Commits
`683d00d`, `859a4c5`. **No deploy — and no restart either**: the rules were written into the
VM's own `config/personas/mike/intake.yaml`, and `load_config()` has no cache, so the running
scheduler picked them up on its next hourly sweep.

**What the tool now does differently.** Six taught `rules:` took the labelled corpus from
**1/33 to 11/33 classified without surfacing**, with `action_required` false negatives at zero
throughout and the domain axis off zero for the first time (0/20 → 4/20). Four Google no-reply
addresses → `notification`/silent; both Prudential advisers → `correspondence`/surface/**finance**,
which is the 09-03 domain-axis work finally overriding a category default in anger. Each rule was
verified firing on its own real corpus mail before the next was taught. `cloudplatform-noreply@`
was deliberately left unmatched so the GCP budget alarm still surfaces.

**Believed true and wrong: the premise the whole session was launched on.** The handoff prompt,
`SESSION.md` and `[DB-0820-03]` all stated the code tier resolved **9/33 with five taught rules**.
The VM's `intake.yaml` had **no `rules:` key at all** — `enabled: true` and a forwarding block,
nothing else, with one entry in the ledger. The 9/33 was a live-mailbox observation written down
without naming its source and then re-quoted across three documents as though it were a corpus
measurement. Real baseline: the same 1/33 the 09-04 eval reported. **A number measured on one
source and recorded without naming it will be re-read as a claim about a different source.**

**Why teach-`rules:` stops at 11/33 — Mike rejected the shape, not the rules.** Asked to rule
sender by sender he said the same thing four ways: **a sender is not a category.** Bupa is
logistics *and* physical_health; a ticketing firm's mail is a recreation booking when it concerns
tickets and a promotion otherwise; George Diamond's message was `action_required` this time and
may not be next time; Samsung sent one `action_required` and one `notification` from one address.
Group B survived only because those four Google addresses genuinely emit one thing. Three
capability gaps were then measured rather than assumed: a rule carries **one** domain
(`_effective_domain()` returns one); **`physical_health` has no `read_intake_queue`** in either
routing file, so routing to it would file into a queue nobody opens; and there is **no sender
class** — the subject-substring workaround was tested against the corpus and fails, since 2 of 4
ticket confirmations contain the word "ticket" and TodayTix's reads *"Order confirmed! Get excited
for The Mousetrap!"*.

**Rejected: teaching A/C/D/E anyway.** Fifteen rules in a shape Mike had just rejected would have
bought a bigger number and taught the system something he does not believe. Prudential was taught
because his objection genuinely does not reach it — disposition `surface` **cannot silence
anything**, so the only load-bearing part is the domain override. That safety property (a
surfacing rule has no downside failure mode) is worth reusing.

**Rejected: closing `[DB-0820-03]` quietly, and rejected: keeping it open.** Its exit was always
"the extractor flips on, citing the eval output", which can never happen — the 09-05 sweep proved
no affordable threshold clears the gate. Mike chose close-plus-file over update-and-keep-open, so
the answered question and the unbuilt capability are two records with one job each rather than one
record carrying both. The extractor is parked **permanently and priced out, not disproven**;
`run_intake_redteam.py` still owes the self-forward-unwrap row and that debt survives the close.

**A test I proposed was wrong, and the correction is the useful part.** I offered
`read_intake_queue("finance")` as the confirming run. It cannot pass: `_record_row()` stamps
`domain` at **sweep time** and records are append-only, so all 26 rows then in the store carried
`domain: None` permanently — a new rule changes the future, never the store. No Prudential mail was
in the live store at all; those four messages exist only in the fixtures.

**Then Mike seeded the inbox and it passed on live mail.** An early manual `sweep()` — an ordinary
function call, notifies nothing — returned `2 new`. `jason.duross@prudential.com` arrived as a
self-forward, **unwrapped**, hit the taught rule and routed to `finance` with `src=rule`; the
finance queue carried an item for the first time. Three separately-built things (forward unwrap,
taught rule, domain override) were observed working together for the first time. I peeked with
`_queue_rows()` rather than `read_intake_queue()` so the cursor did not advance and the finance
agent still gets it.

**The second seeded message is why `[DB-0905-01]` exists.** A Bupa follow-up arrived from
**`no-reply@bupadentalcare.co.uk`** while the corpus holds **`crossrail@email.bupadentalcare.co.uk`**
— same organisation, different sending address. **A sender rule taught from the corpus would not
have fired**, and the second address was discoverable only by receiving mail from it. An
organisation is not an address. It landed `unclear`, and is also a live instance of the
one-domain-per-rule gap.

**Mike's requirement on how the research gate decides, recorded as a constraint.** Before
concluding anything about an unknown sender it must search prior correspondence for the **same or
similar domain, and for keywords** — and **that search runs as code or an API call, never as a
model judgement**, so the evidence stays deterministic and inspectable even where the conclusion
drawn from it is not. Three sources, cheapest first: `read_records()` over the local intake store
(free, and it would have joined the two Bupa addresses immediately); IMAP via the existing
`search_correspondence()` path, which is already the right shape but **matches one exact address**
and needs domain and keyword matching added; external research only for a sender with no history
at all. This reorders the feature from "research an unknown sender" to **evidence first, research
last**, which strengthens the cost argument that made the gate preferable to the extractor — the
gate pays once per new sender rather than per message, and most senders will never reach step 3.

**Two operational notes.** The `teach_intake` confirmations were approved in-process
(`approve(token)` in the same script) rather than through the app, on the reasoning that Mike's
live rulings *are* the approval the two-step exists to capture — flagged to him, not assumed. And
the backlog sync pulled six `USER_CORRECTION` events off the VM into the machine log (`×4`, `×2`,
one flagged `⚠`): this walkthrough's own teaching traffic showing as production signal, the same
class as the eval-traffic growth already noted on 09-05.

**Outgoing handoff (carried from `SESSION.md`):** the day's earlier state is unchanged — thread
identity live and owing one observation, the extractor parked on evidence, the scheduler day-name
typo closed and VM-verified. What this session removes from the "next, all Mike" list is the
rules-teaching walkthrough itself; its prompt is consumed and deleted.

