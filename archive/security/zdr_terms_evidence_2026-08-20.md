# Vertex AI ZDR / abuse-monitoring terms — evidence record, 2026-08-20

**Task:** `archive/handoffs/2026-08-20-zdr-verification-prompt.md`. This file is the evidence the
handoff demanded — quotes from Google's current published terms, with URLs and a re-check
procedure, replacing the unverified "verified ZDR" claim corrected in `ROADMAP.md` § Section 0.

**How obtained:** fetched 2026-08-20 from `docs.cloud.google.com` under a per-occasion,
Mike-approved lift of the WebFetch deny, scoped to Google's own domains. Raw HTML archived in the
session scratchpad only; the load-bearing text is quoted verbatim below.

**Sources (both fetched 2026-08-20):**

1. Abuse monitoring — `https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/abuse-monitoring`
   *(the old `cloud.google.com/...` URL 301-redirects here; the product is now branded "Gemini
   Enterprise Agent Platform" in the docs, citing GCP Terms of Service § 4.3)*
2. Data governance / zero data retention — `https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance`

---

## Finding 1 — the abuse-monitoring exception IS obtainable on this account shape

The handoff's step-1 question — whether a self-serve, no-organization account can even request the
exception — is answered **yes** by the terms. The opt-out is scoped to precisely the customers
governed by the standard (self-serve) GCP Terms of Service:

> "**Customers in scope**: Only customers whose use of Google Cloud is governed by the Google Cloud
> Platform Terms of Service. This means that customers with a Google Cloud Master Agreement are
> exempt from prompt logging for this abuse monitoring by default."

> "**Customer opt-out**: Customers may request for an exception by filling out this form. If
> approved, Google won't store any prompts associated with the approved Google Cloud account."

The form link on the page: `https://forms.gle/mtjKKas8a82grYN6A`. No organization, contract, or
support-tier requirement is stated. Approval is discretionary ("If approved"), so the outcome is
not guaranteed — but the route exists and costs nothing to take.

## Finding 2 — the default exposure is narrower than the CORRECTION assumed

The § Section 0 CORRECTION (2026-08-20) said "the default is retention for abuse monitoring for a
limited window," left deliberately unquantified. The actual terms for Google (Gemini) models are
**conditional, not blanket**:

> "**Prompt logging**: If automated safety classifiers detect suspicious activity that requires
> further investigation into whether a customer has violated our policies, then Google may log
> customer prompts solely for the purpose of examining whether a violation of the AUP or Prohibited
> Use Policy has occurred. This data won't be used to train or fine-tune any AI/ML models. This
> data is stored securely for up to 90 days in the same region or multi-region selected by the
> customer for their project…"

So: prompts are logged **only when a safety classifier flags them**, retained **up to 90 days**,
never used for training. Responses are not mentioned in the standard tier (prompt logging only).
Ordinary personal-life traffic — including `tone_profiler`'s correspondence reads — is unlogged
unless a classifier misfires on it. This does not make the exception unnecessary; it corrects the
size of the gap it closes.

*(A stricter "Advanced AI" tier — all prompts AND responses logged for up to 30 days, opt-out "may
not be possible" — exists but covers only designated models: Claude Mythos/Fable and certain
Claude Opus/Sonnet configurations. The runtime path is Gemini 3.1 Pro / Flash-Lite; nothing in
`routing*.yaml` routes runtime traffic to a designated Advanced AI model, so this tier does not
apply to the deployment.)*

## Finding 3 — training use: confirmed, holds by default

> "Google won't use your data to train or fine-tune any AI/ML models without your prior permission
> or instruction. This applies to all managed models on [the platform], including GA and pre-GA
> models." *(Service Specific Terms, "Training Restriction")*

The CORRECTION's one surviving claim is now verified against the published terms, not assumed.

## Finding 4 — ZDR is a checklist, not a single grant

The data-governance page enumerates every retention area and the action each requires. Status for
this deployment:

| Area | Terms say | This deployment | Action |
|---|---|---|---|
| Abuse-monitoring prompt logging | Opt-out by form, if approved | In scope (self-serve ToS) | **Mike submits the form** |
| Grounding with Google Search | Query logs kept **up to 3 days**, "There is no way to disable the storage" | **Used** — the grounded Research path (`run_session_gemini_grounded`) | Accept (path is decontextualized by design) or move to "Web Grounding for Enterprise" later |
| Request-response logging (BigQuery) | Off by default; keep off for ZDR | Not enabled anywhere in repo | None |
| Interactions API (`store=true` default) | Set `store=false` for ZDR | **Not used** — orchestrator calls `generateContent` via the genai SDK | None |
| Gemini Live API session resumption | Off by default | Not used | None |
| In-memory data caching (`cacheConfig`) | 24h TTL, in-memory only, project-isolated — "does not violate zero data retention" | Enabled (default) | None needed |

## Finding 5 — the `cacheConfig` question from the handoff is resolved

The handoff cautioned that `cacheConfig` might not govern abuse-monitoring retention. Confirmed:
it does **not**. It controls the in-memory latency cache described under "In-memory data caching,"
which Google states explicitly "does not violate zero data retention." It is unrelated to abuse
logging and unrelated to the explicit context caches the cost-control work manages. The 2026-08-20
handoff row can be read as: no `disableCache` set = the latency cache is on, which is fine.

## Residency footnote (per the handoff: a footnote, not a deliverable)

Abuse logs are stored "in the same region or multi-region selected by the customer" — with
`GOOGLE_CLOUD_LOCATION=global` that pin is as loose as the endpoint. Unchanged assessment:
residency is the weaker control; the exception is the lever.

---

## How to re-check (greppable procedure)

1. Fetch the two source URLs above; diff the "Customer opt-out" and "Prompt logging" sections
   against the quotes in this file.
2. If the exception has been granted: the grant confirmation (email/case ID) should be recorded in
   `docs/INFRASTRUCTURE.md` § Vertex AI credentials with the grant date. If that row still says
   "not in force," the exception has not landed regardless of what any other doc claims.
3. `gcloud` has no surface that reports the exception's status — the grant record + Google's
   confirmation is the only evidence. Do not infer it from `cacheConfig` (Finding 5).

---

## PROPOSED § Section 0 amendment — SUPERSEDED 2026-08-28, never applied

*Drafted 2026-08-21 before Google's decision. The opt-out was refused 2026-08-26; Mike ruled
2026-08-28 and the applied amendment is in `ROADMAP.md` § Section 0 (Amendment 2026-08-28).
Kept below verbatim as the historical draft.*

Replacing nothing, appended after the CORRECTION block if approved:

> **Amendment 2026-08-2X — corrected basis, exception pending.** Google's published terms
> (verified 2026-08-20, evidence: `archive/security/zdr_terms_evidence_2026-08-20.md`) establish:
> no training use (default, contractual); prompt logging **only on classifier-flagged traffic**,
> ≤90 days, opt-out obtainable by request on this account shape. The abuse-monitoring exception
> was requested on [DATE]; until granted, the sensitive-tier default on the VM continues on this
> corrected, narrower basis for the single-user development phase. Review trigger: the exception's
> grant or refusal, or 2026-10-01, whichever comes first. If refused, the `tone_profiler` question
> (third parties' correspondence) returns to Mike for a narrowing decision. All other conditions
> — fail-closed routing, the north star, the multi-user expiry — unchanged.
