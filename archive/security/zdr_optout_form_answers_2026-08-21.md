# Vertex AI abuse-monitoring opt-out — field-by-field answers, 2026-08-21

**Form:** "Prompt Logging for Abuse Monitoring Exception" (`forms.gle/mtjKKas8a82grYN6A`).
Submitted from `diamond.mike@gmail.com`. Basis: `archive/security/zdr_terms_evidence_2026-08-20.md`.
Review takes ~2 weeks; allowlisting a further 5–7 business days if approved.

**Standing rule for every field: answer truthfully as an individual.** A placeholder or a defunct
company is a misrepresentation on a compliance request, and a dead website is exactly what a
reviewer checks. "No entity" is not disqualifying — the form's own scope line is customers on the
self-serve GCP Terms of Service, which is what an individual developer is.

| Field | Answer |
|---|---|
| Email | `diamond.mike@gmail.com` |
| Organization Name * | `Mike <surname> (individual developer — no incorporated entity)` |
| Organization Website * | A URL Mike actually controls — personal domain or public GitHub profile. If none: `None — personal, non-commercial single-user project` |
| GCP Project number * | `211460608583` |
| GCP Project ID | `metatron-ai-499810` |
| Email Address (Business only) * | `diamond.mike@gmail.com` — no business domain exists |
| Use cases * | **Both**: generation of new content (text) and understanding/augmentation of existing content (summarization, extraction, classification) |
| Who sees the output * | **Users internal to your organization** — the only user is the developer |
| Child protection * | **N/A: not directed toward individuals under 18** |
| Sensitive domains * | See § Sensitive domains below — a judgement call |
| Individual monitoring outputs * | **Yes** |

## "Explain why you want to request prompt logging exception?"

> This is a single-user personal assistant built and run by me, for myself. The prompts contain my
> own private life record — daily notes, goals, health and finance details — and, in one feature,
> private correspondence written to me by family and friends who have not consented to their
> writing being stored by a third party. My own privacy design permits this data to reach a hosted
> model only where prompts are not retained; storage of flagged prompts, even briefly and for
> legitimate abuse review, is the single condition it cannot accommodate. I am asking only that
> prompts associated with this account not be stored. I am not asking for abuse detection or
> classification to be relaxed, and I accept full responsibility for AUP and Prohibited Use Policy
> compliance across all traffic on this project. There are no other users, no external output, and
> no public-facing surface.

## Sensitive domains — the one real decision

The application does track health and medication notes, does arithmetic on personal finances, and
does act as a companion offering emotional support. Read literally, three boxes apply:
**Healthcare and medicine**, **Financial services and banking**, and **Therapy, wellness,
relationship coaching… companionship, emotional support**.

Read as the form almost certainly intends — *what industry does your product serve* — none apply:
nothing is offered to any other person, so there is no patient, no client and no customer.

**Recommendation: tick Therapy/wellness/companionship only, and let the free-text answer carry the
context.** It is the one that genuinely describes the product's character rather than a data type
it happens to hold, and declaring it is what keeps the answer honest if a reviewer reads the use
case. Ticking all three invites scrutiny for services that are not being provided to anyone;
ticking "None" is the answer most likely to look wrong later.

## After submitting

1. Record the submission date and any case/confirmation ID in `docs/INFRASTRUCTURE.md`
   § Vertex AI credentials — that row is the authority on whether the exception is in force.
2. The proposed § Section 0 amendment at the bottom of
   `archive/security/zdr_terms_evidence_2026-08-20.md` has a `[DATE]` placeholder for this
   submission; it still needs Mike's ruling, granted or not.
3. Grounding with Google Search (3-day query logs, no opt-out) is **not** covered by this form —
   accepted as recorded in Finding 4, because that path is decontextualized.
