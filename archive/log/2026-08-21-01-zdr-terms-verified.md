### 2026-08-21 (ZDR terms verified: the exception is obtainable, and the default is narrower than feared) — `docs/INFRASTRUCTURE.md`, `archive/security/zdr_terms_evidence_2026-08-20.md`, **not deployed**

**The 2026-08-20 ZDR handoff ran, and it ended in its better branch.** Google's published terms
(fetched 2026-08-20 from `docs.cloud.google.com`) establish that the abuse-monitoring exception —
the thing "Vertex AI ZDR" actually is — **is obtainable on this exact account shape**: the opt-out
form is scoped to customers on the standard self-serve GCP Terms of Service, which is what
`metatron-ai-499810` is; Master Agreement customers don't even need it. No organization, contract
or support tier required. Evidence with verbatim quotes, URLs, the form link and a re-check
procedure: `archive/security/zdr_terms_evidence_2026-08-20.md`. A status row now lives in
`docs/INFRASTRUCTURE.md` § Vertex AI credentials and is declared the single authority on whether
the exception is in force.

**The § Section 0 CORRECTION's premise was refined, not overturned.** The default for Gemini
models is *conditional* logging — prompts kept up to 90 days **only when a safety classifier flags
them**, never for training — not blanket retention. `tone_profiler`'s exposure is a classifier
misfire, not routine logging. The handoff's `cacheConfig` caution resolved: it governs only the
in-memory latency cache, which Google states does not violate ZDR — unrelated to abuse logging.
One real residual found: **Grounding with Google Search keeps query logs 3 days with no opt-out**,
and the Research path uses it; acceptable because that path is decontextualized by design.

**How access happened, and that it is closed.** Mike approved a per-occasion WebFetch lift scoped
to Google's own domains (option 2 of the handoff). The harness classifier refused to let the
session edit its own permissions — correctly — so Mike made the edit by hand; two JSON syntax
breaks from the hand edits were repaired in-session. The lift was **reverted the next morning and
verified byte-identical to HEAD**, deny list intact. Rejected: the paste-the-terms route (slower,
riskier extraction) and skipping to the not-obtainable amendment (would have baked in an
unverified premise — the exact error class being corrected).

**Open with Mike, filed to the backlog inbox:** submit the opt-out form (his account, his act),
and rule on the proposed § Section 0 amendment drafted at the bottom of the evidence doc — the
sensitive-tier default's corrected basis is stated there but **not applied**. No code written; the
handoff predicted that and it held.
