# Misheard names — per-user vocabulary, correction notes, and a flag for the unknown

*Plan, 2026-10-23. Approved in direction by Mike, conditional on a Fable review. Follows
`archive/plans/client_voice_reserve_and_outbox_plan_2026-10-23.md` and commit `6408b97`.*

> **As built, 2026-10-23. Code review on Fable 5.1; findings fixed.**
>
> - **Real data:** on Mike's 68 user messages since 09-23, a note fires on 5 (7%). Three are right
>   ("Eva" twice, an alias on Iva's record; "Ivy" sounds like Iva). Two are false ("Share",
>   "Day"); the "Day" case has since been removed by requiring two-sound keys.
> - **Flash-Lite, five runs per case, synthetic contacts:**
>
>   | Case | Result |
>   |---|---|
>   | A correction is applied | 5/5 |
>   | A new person with the same name is kept, or asked about | 5/5 |
>   | "Benny is a real person" is honoured | 5/5 |
>   | A sound-alike is resolved or asked about | 5/5 (wording chosen by A/B) |
>   | A new "Ella" beside a known Bella is kept | 5/5 |
>   | The correction turn writes `MISHEARD` | 5/5 |
>   | The note is copied into `ORIGINAL_MESSAGE` | 0/5 |
>
>   With the 1b paragraph alone, names were corrected 1/3.
> - **Changed in build:**
>   - A word that is only a contact's nickname or `referred_to_as` is noted with who it means.
>     Mike's own record lists "Eva" for Iva, and that did not stop "Eva & Benny".
>   - `MISHEARD` is recorded only when the user's own message names both people.
>   - The sound-key path needs two sounds and a spelling score of at least 0.6.
>   - Checking is window-bounded, so a 21 KB paste costs under 0.15s.
> - **Known residuals:**
>   - "Gmail" sounds like a contact "Kamal". It scores exactly what Benny/Manny does.
>   - A name that opens a sentence is unchecked.
>   - A plain "yes" to "did you mean Iva?" records no correction.
> - **Whisper vocabulary:** built and off. It needs the VM measurement.
>
> **Revised after the Fable design review, same day; this block supersedes parts 2–4 and the Red
> edits below where they differ.**
>
> 1. **Corrections are not a contact field.** They live in their own per-persona file,
>    `crm/misheard_names.json`, written under the same rules as `name_resolutions.json`: `0600`,
>    nothing deleted, superseded entries kept in history. They are never read by contact lookup or
>    dedup — otherwise `read_contact("Benny")` would resolve to Manny and the Bonnie trap returns.
>    `write_contact` replaces collections and drops fields on gate replay and on merge.
> 2. **The Coordinator records a correction as an output line** (`MISHEARD: "Benny" -> Manny`),
>    parsed by code the way `USER_CORRECTION` already is. No tool or grant is needed, and
>    Relationships is not involved. The code refuses to record a heard name that belongs to a contact.
> 3. **Archived (merged-away) contact names count as corrections** to the contact they merged into.
> 4. **The near-name flag must not flood.** It skips sentence-initial tokens and uses a stop-list.
>    There is no prefix signal and the bar is higher. It is measured on real messages before it ships.
> 5. **The note's escape reads "unless the message introduces a new or different person".** Nothing
>    is deleted when a same-named contact appears; rule 1 already suppresses the note.
> 6. **Whisper:** both `hotwords` and `initial_prompt` are built, off by default, and measured side by
>    side. The persona reaches `transcribe()` inside `persona_scope`.
> 7. **Tests:** twin wiring, flood rate, proactive turns, store round trips, the correction turn itself,
>    and n ≥ 5 per A/B case.

**Model: Opus 5.5 to build; Fable 5.1 to review.** The review matters here because the
correction rule acts on Mike's own words.

## The problem, measured

Dictated names arrive misheard, and Flash-Lite agents save them as heard. On 10-15 Relationships
created a contact "Eva" (for Iva); on 10-22 Logistics wrote the calendar event "Eva & Benny" (Iva and
Manny); morning check-ins have carried the misheard names daily since 10-16. With the 1b paragraph
in `coordinator.md`, an A/B on Flash-Lite corrected a place 3/3 but a person's name only 1/3,
because "Ella" and "Benny" are plausible real names and the model will not assume them away.

Constraints from Mike: per user; no model upgrade and no added latency; **never stop a new person
from being registered** — the Bonnie/Johnny case. A correction rule that rewrites the transcript
would make a real Bonnie arrive as "Johnny", even in the sentence meant to say "Bonnie is a real person".

## Design — three parts, none of which rewrites the user's words

1. **Known names are never touched.** "Known" means the contact's `name`, `first_name`, `nickname` or
   `referred_to_as`, read from that persona's `crm/contacts.json`.
2. **A correction is a note, not a replacement.** A new contact field, `heard_as: [str]`, records the
   ways the transcriber has misheard that person. It is written by Relationships through the existing
   `write_contact`, when the user corrects a name ("it's Manny, not Benny"). On a later turn
   containing "Benny", the Coordinator's input carries
   `[Name note: "Benny" is not a contact; corrected to Manny before. Read it as Manny unless this message says otherwise.]`
   **Retired by construction:** if anyone named Benny ever becomes a contact, rule 1 wins, the note
   is no longer produced, and the stale `heard_as` entry is removed at that write.
3. **An unknown name near a known one is flagged.** A capitalised token that is not a known name but
   scores at least the CRM's existing `_name_similarity` threshold (0.6) against one gets
   `[Name note: "Ella" is not a contact; it sounds like Bella. If the message does not make clear
   who is meant and something would be saved or sent, ask.]` That is a hint, never a substitution.

**Where the note goes.** It is computed in `core/orchestrator.py` beside `receipt_line` and
`attach_note`, in both the blocking and the streaming twin, for user turns only (never proactive
ones). It is appended to the Coordinator's input and nowhere else. That covers voice and typed
input, so no client change is needed. A failure produces no note, never a failed turn.

**4. Per-user Whisper vocabulary (prevention).** `core/voice_pipeline.transcribe()` gets the
persona, which `/transcribe` already passes, and sets faster-whisper's `initial_prompt` to a short
list of known first names and nicknames, capped at about 30 by recency (`last_contact`). It is
primed with **contacts only, never `heard_as`**: a bias toward a corrected name would be invisible
downstream. It ships **off** behind `METATRON_WHISPER_NAME_PROMPT` until it has been measured on
Mike's saved recordings, on the VM, where the audio stays.

## Red-tier edits (each prompts Mike)

- `coordinator.md` 1b — one clause saying a `[Name note]` is evidence to weigh, and that a correction
  ("it's X, not Y") goes to Relationships to record.
- `relationships.md` — when the user corrects a misheard name, add the heard form to that contact's
  `heard_as`; never create a contact for it.

## Tests

- **Unit tests for the note builder:** a known name is never noted; a correction produces its note;
  a near name is flagged; a contact named Benny retires the correction; persona isolation; a broken
  contacts file yields no note.
- **A/B on Flash-Lite, synthetic context, a few cents:** a known correction; a genuinely new person
  with the same name ("I met someone called Benny today"); the escape ("Benny is a real person").
  The pass bar is the corrected name in the Logistics/Relationships directive, the new person
  registered or asked about, and the escape honoured.
- **Whisper measurement on the VM:** the 10-15 and 10-22 recordings re-transcribed with and without
  the prompt. Prints the name tokens only.

## Cost

- **Build:** one Opus 5.5 session on the subscription, roughly $5–10 API-equivalent. The Fable
  review is roughly $2–4. The A/B is under $0.05 of Vertex.
- **Run:** nothing in money. The note is about 30 tokens when it fires, which is rare. Whisper priming
  is a few dozen tokens per decode, which is negligible.
- **Persisting:** `heard_as` is a few bytes per contact. It is deleted by a contact taking that
  name, or by the user saying so.
