## A backlog item re-proposed a decision Mike had already reversed, and nobody saw it

**What happened.** `[DB-0810-17](b)` described `read_google_contacts` as *"built but unreachable —
never imported into `register_tools()` and never granted"*, and suggested the tool-reference guard
should learn to flag `tools/` modules that nothing registers. All of that was literally true. It
was also not an oversight: the Google Contacts OAuth path was **built on 2026-08-07 and reversed on
2026-08-08 at Mike's own challenge** — import, schema and handler removed so the tool was
structurally undispatchable, the grant pulled from both routing files, and
`people.googleapis.com` disabled on the GCP project. The reasons were that the real defect was
local (`write_contact` had no validation against the user's own identity) and that OAuth carried a
7-day refresh-token expiry under Testing publishing status, needing Google review and a hosted
privacy policy to escape. The replacement was `scripts/import_vcard_contacts.py` using `vobject`.

**Why it got through.** Mike reframed the item on 2026-08-15 — *"the internal CRM pulls from Google
Contacts, and any other CRM arrives by import in conventional file types"* — which reads as
endorsement. But the question he was answering was **where contacts come from**, not **whether to
re-adopt OAuth**. The entry named no OAuth, no token expiry, no disabled API and no prior
reversal, so the only half of the decision that would have drawn a challenge was the half not on
the page. He said afterwards he had not realised he was reversing himself.

A `/backlog attack` worker then built `import_google_contacts` on top of the dormant module, and
hand-rolled a vCard parser reasoning that *"the project has no existing vCard use to justify a new
third-party package"* — while `vobject==0.9.9` had been in `requirements.txt` since 08-08, put
there for exactly this.

**What was done.** `import_contacts_file` (CSV + vCard) registered and granted to `relationships`;
`import_google_contacts` deliberately left unregistered with the reason in a comment at the
registration site, where the next person to consider wiring it will actually be standing.

**The transferable lesson, and it is not "verify the item".** Verification was done — the code
claim was checked and was true. What was missing is that **an item describing something as absent
must say whether it was ever present**. A thing that was removed on purpose and a thing that was
never built look identical in the current tree, and only one of them is safe to add. When an item
proposes building something that already exists in `tools/` unwired, the archive is the file to
check, not the code.

**Second-order:** the same shape now sits in the entry's own suggestion — *"should the guard flag a
`tools/` module that nothing registers?"* If that guard is ever built, it must read
`archive/backlog_closed_*.md` before reporting, or it will re-raise every deliberate reversal in
the project on a schedule.
