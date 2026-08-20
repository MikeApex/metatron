# Handoff — get Vertex AI ZDR actually in force, or record what replaces it

**Raised by Mike, 2026-08-20**, at the close of the Vertex billing reconciliation session. Start a
fresh chat with this file. Run `/metatron-code` first.

---

## Why this exists

The project's binding privacy ruling (`ROADMAP.md` § Section 0) permits sensitive-tier personal
data on the Vertex VM on the strength of **"verified Zero Data Retention."** On 2026-08-20 that was
checked for the first time and **it was never verified and is not in force.** The correction is
written into § Section 0 as `CORRECTION 2026-08-20`; read it before anything else, because it
states precisely which of the three claims survived.

Short version: **"no training use" holds by default. "Prompts/responses cleared before logging"
does not** — that is what an approved abuse-monitoring exception buys, and there is no evidence one
was ever requested.

**The path this most affects is `tone_profiler`**, which reads a large sample of real correspondence
written by *other people*, and which the 2026-08-09 clarification pre-cleared explicitly on this
assumption.

---

## What was already checked — do not redo this

| Check | Result | How |
|---|---|---|
| Organization parent | **none** | `gcloud projects describe metatron-ai-499810 --format="value(parent.type,parent.id)"` → empty |
| Billing account | **"My Billing Account"**, no master/reseller parent | `gcloud billing accounts describe 013F3D-66B5CD-955A3A` |
| Org policies | **0 items** | `gcloud resource-manager org-policies list --project=metatron-ai-499810` |
| Repo record of a ZDR/exception request | **none** | grep across `docs/`, `CLAUDE.md`, `ROADMAP.md`, `archive/PROJECT_LOG.md` |
| Vertex `cacheConfig` | returns only `{"name": ...}` — **no `disableCache` set** | `GET https://aiplatform.googleapis.com/v1/projects/metatron-ai-499810/cacheConfig` |

**A caution on that last row:** it is not established that `cacheConfig` governs abuse-monitoring
retention at all — it may only control the customer-facing context-caching feature. **Do not cite it
as evidence either way until you have confirmed what it governs.** It is listed here so the next
session does not rediscover it and over-read it.

---

## The constraint that shaped this handoff

**`WebFetch` and `WebSearch` are Denied on this project** (`CLAUDE.md` § Nothing about this project
leaves this machine). That is why no session has been able to read Google's current ZDR terms,
retention windows, or exception process — and it is the direct reason the original assumption went
unchecked for two months.

**This is the first thing to resolve with Mike, and it is his call, not yours.** Options, with the
trade-off stated:

1. **Mike reads the terms himself and pastes the relevant text in.** Zero policy change, costs his
   time, and is the default.
2. **Mike lifts the web-fetch deny for this one task**, scoped to Google Cloud terms/docs URLs. The
   deny exists because a session published private content unasked; *reading* a public terms page is
   a different act from *publishing*, but the rule is deliberately blunt and lifting it is his
   decision per-occasion, never yours for convenience.

Do not proceed to research the terms by any other route, and do not guess a retention window — a
number quoted from memory is exactly how the original assumption got in.

---

## The work

### 1. Establish what ZDR actually requires on this account shape
Self-serve billing account, no organization, no support plan of record. Determine whether an
abuse-monitoring exception is even **obtainable** in that configuration, or whether it requires an
organization, a Cloud contract, and/or a paid support tier. **This is the question that decides
whether steps 2–3 are possible at all** — answer it before designing anything.

### 2. If obtainable — get it, and record the evidence
Follow the actual process. When it lands, record it somewhere durable and greppable:
`docs/INFRASTRUCTURE.md` § Vertex AI credentials is the right home, alongside the project and
service-account rows. **The record must include what was granted, when, and how to re-check it** —
the whole failure here was a claim with no evidence behind it.

### 3. If not obtainable — bring § Section 0 into line with reality
This is the branch to plan for properly, because it is the likely one. Section 0 currently
authorises sensitive-tier data on a premise now known to be half false. Produce **options with a
recommendation, not a menu**:

- Accept the corrected basis (no training; limited-window abuse logging) explicitly for the
  single-user development phase, with a stated review trigger.
- Narrow what may run on the VM — e.g. pull `tone_profiler` back until ZDR exists, since it is the
  one path handling third parties' writing.
- Accelerate the north star (private hardware), which Section 0 already names as the destination and
  which makes the question moot.

Whichever is recommended, **the amendment's wording must stop asserting "verified ZDR"** — that
phrase is now banned in this repo until something records a verification.

### 4. Do not conflate residency with retention
`GOOGLE_CLOUD_LOCATION=global` means processing is not pinned to a region. That is real but it is
the **weaker** control: Google is US-incorporated, so US legal process reaches data it controls
wherever it sits, and Gemini 3.x is not served from regional endpoints anyway. Region-pinning would
cost the models and buy little. **Do not let this become the deliverable** — it is a footnote, and
§ Section 0's correction already records it as one.

---

## Boundaries

- **`ROADMAP.md` § Section 0 is the binding privacy ruling.** Propose amendments; do not apply them.
  Mike decides what the permission rests on.
- **Nothing about this project leaves the machine without Mike asking** — see the constraint above.
- This is a research-and-decision task. **No code is expected.** If it produces code, that is a
  signal the scope drifted.

---

## Budget and model

Small — the work is establishing facts and drafting an amendment, not building. **~30–60k tokens,
under $2**, dominated by whatever terms text gets pasted in.

**Model: Fable 5** — plan and review, per Mike's standing split (2026-08-18). This is
architecture-of-a-ruling work with high ambiguity and a real chance of a wrong confident answer,
which is exactly where the split puts Fable. No build model is needed unless step 2 produces
config changes.

---

## Definition of done

One of two outcomes, both of which end with evidence rather than a claim:

1. ZDR is in force and `docs/INFRASTRUCTURE.md` records what was granted and how to re-check it; or
2. It is established that ZDR is not obtainable on this account shape, and § Section 0 carries a
   corrected amendment that Mike has approved, saying what the permission actually rests on.

**"We think ZDR is probably fine" is not an outcome.** That is the state this handoff exists to end.
