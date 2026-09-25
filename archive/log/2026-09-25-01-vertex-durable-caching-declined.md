### 2026-09-25 (Google will store every prompt prefix for 24h from 15 October, and the opt-out does not exist yet) — `DEV_BACKLOG.md` — this close-out — **not deployed; no code changed**

Google's notice arrived mid-session: **Durable Caching goes GA 2026-10-15** and is enabled by
default for any project with implicit caching on, across Gemini 3.x Pro/Flash and every model
launched after. Cached data encrypted, project-partitioned, retained **up to 24h**, never used for
training, no fee. `metatron-ai-499810` named as in scope. **Mike ruled: opt out to `EPHEMERAL`.**
Filed as `[DB-0925-01]`, `due: 2026-10-08`, `@waiting:` on the field existing.

**What actually changes, which is the only reason this was worth a decision.** Today no user
content is ever at rest in a Vertex cache: the explicit cache
(`_get_or_create_vertex_cache`, `core/orchestrator.py:3990`) stores system prompt and tool schemas
only, and the implicit cache is in memory. Implicit caching caches the whole request prefix —
conversation history and personal context. From 10-15 that prefix goes to durable storage by
default. **The opt-out preserves current behaviour; accepting is the change**, which is what
decided it.

**Options rejected.** (1) *Accept the default* — free, and defensible under the 2026-08-26 ruling
(same vendor, encrypted, 24h, no training, and Google already holds Mike's mail and calendar).
Rejected because it silently retires a documented fact for ~$1–2/mo of forgone implicit-cache
discount. (2) *`disableCache: true` now* — works today and closes the pre-GA window outright, but
kills the implicit discount and is broader than the decision taken. Rejected as pre-emptive payment
for a ≤24h window that probably never opens; it stays available as **Mike's** call if the field is
still missing by 10-14, not as an automatic fallback.

**Believed true and wasn't, three times.** (a) **Google's own emailed command cannot run.**
`retentionConfig` does not exist on the live API — the published discovery schema for *both* `v1`
and `v1beta1` lists exactly `name` and `disableCache`, and the PATCH is rejected identically on the
global host and on `us-central1` / `us-east4` / `europe-west4`. The advice given before probing
assumed it was runnable today. (b) **Their command is also broken as pasted** — JSON payload inside
double quotes with unescaped double quotes within it, and a `${LOCATION_ID}-` host while we run
`GOOGLE_CLOUD_LOCATION=global`. (c) **`archive/security/zdr_terms_evidence_2026-08-20.md` Finding 4
carries a row quoting Google that this cache is *"in-memory only … does not violate zero data
retention"*.** It was written as a standing fact and has an expiry date nobody knew about: it goes
false on 10-15 unless the opt-out lands. That row is evidence the `ROADMAP.md` § Section 0 basis
rests on, which is why this outranks its dollar value. *Same shape as the availability lesson from
`[DB-0901-01]`: a vendor fact carries an expiry — write the date on it.*

**Two things the probe did settle, so October is a one-liner.** The credential can write the
resource — a `disableCache: false` PATCH returned a completed operation — and state is unchanged,
still `{"name": "projects/211460608583/cacheConfig"}`, nothing pinned, i.e. genuinely in scope for
the flip. **A cost no meter will report:** `spend_guard` sees tokens and explicit-cache storage;
nothing in this project can ever show durable-cache residency, because there is no charge to show.

**Carried forward unchanged:** phase E, the deploy, is still next — `7bca654..HEAD`, with the (M)
pipeline turn on `--persona mike` owed on the VM. Nothing in this session touched it.
