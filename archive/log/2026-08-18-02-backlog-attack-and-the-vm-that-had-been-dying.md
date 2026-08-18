### 2026-08-18 (`/backlog attack` — three clusters, and a VM that had been dying quietly)

*(Fragment numbering note: this date already carries a `-01-` from the parallel knowledge-layering
window. Unique slugs meant no file was lost, but two sessions independently picked `01`, so the
number orders nothing. Next session on a shared day should check `ls archive/log/` first.)*

**Three clusters ran in parallel, all merged, all green.** Cluster A widened the CRM placeholder
guard from email-only to phone/address/social/name (`8c7121b`); cluster B added
`tools/contacts_import.py` — Google pull plus vCard/CSV file import (`5c3bb3b`); cluster C added
`fetch_rendered`, a read-only headless-browser fetch behind the same SSRF and `<untrusted_content>`
boundary as `fetch_url` (`6097c44`). Registration and routing grants were kept in this window
because `routing*.yaml` is Red tier, which turned out to be the right split for an unrelated reason
— see the OAuth finding below.

**The clusters collided semantically even though their file manifests were disjoint.** B passed
17/17 alone and failed 7/17 once merged: it had written fixtures with canonical fake data
(`555-0100`, `Jane Doe`) and A had shipped a guard that refuses exactly that. Fixed in `4212071`.
**The disjoint-manifest rule prevents file collisions and says nothing about behavioural ones** —
worth carrying into the next `attack`, because nothing in the current protocol would have caught it
except running the suites together after the merge.

**That collision exposed a real defect (`0d9310e`).** `write_contact` refused the *whole record*
when any one field was a placeholder — correct when a model is inventing a contact field by field,
wrong on a bulk import, where it silently costs a real person their record over one junk value.
Mike chose option (a): drop the offending field, keep the person, report the drop. A placeholder
*name* is still refused outright, being the record's only anchor. Placeholder values also had to be
stripped from the identity-matching lists, or two unrelated people who both had `555-0100` saved
would have collapsed into one record — the failure a dedup feature would have caused.

**`[DB-0813-02]`'s own diagnosis was wrong, and working it as written would have "fixed" nothing.**
The item said the `OPENAI_API_KEY` in `.env` was invalid, returning `401 invalid_api_key`, fix being
a rotation. A live call returned `OPENAI_API_KEY environment variable is not set`: `ask_gpt.py` reads
`os.environ` only and its `~/.claude.json` registration carried an empty `env: {}`, while
`ask_gemini` beside it had its key inline. The key was valid all along. Rotating it would have
closed the item and left GPT silent.

**The VM had been dying and restarting without anyone knowing.** Sizing the Playwright decision
surfaced three `Out of memory: Killed process` entries in the kernel log — one on 2026-08-15 15:02
that killed `metatron-server.service` itself at 3.6 GB RSS, with `Restart=always` masking it in five
seconds. **Mike's proposed design — let Playwright be shut down first with a friendly message — was
half right and the correction mattered:** the kernel kills the *largest* process, which is the
server, and an OOM kill is SIGKILL, so nothing downstream can return a message. Built in the order
that does work (`4d10cbd`): a `MemAvailable` pre-flight refusal *before* launch, a single-render
lock, and `oom_score_adj=1000` on the browser as backstop rather than mechanism.

**Applied to the VM the same session rather than filed and carried** (`fa4d200`, `b62bb18`): 2 GB
swapfile with fstab entry, a 5-minute watchdog timer that recorded the pre-existing OOM kill as a
critical alert on its first run, and Playwright installed and proven by running it — headless
Chromium loads a page at **~189 MB**, against the 700 MB pre-flight threshold. Disk was the
unexamined constraint at 76%; reclaiming 403 MB apt and 2.8 GB pip cache left the VM at **75%
having gained a swapfile and a browser**. The 1.6 GB huggingface cache is live model data and was
left alone.

**A backlog item re-proposed a decision Mike had already reversed** — the Google Contacts OAuth
path, reversed 2026-08-08, re-described on 08-15 as an unregistered-tool oversight. Full narrative
in `2026-08-18-01-backlog-item-hid-a-reversal.md`; the operative outcome is that
`import_contacts_file` shipped and granted while `import_google_contacts` stayed structurally
undispatchable, with the reason written at the registration site. **Duplication left standing and
flagged, not fixed:** cluster B hand-rolled a vCard parser while `vobject==0.9.9` has been in
`requirements.txt` since 08-08 and `scripts/import_vcard_contacts.py` already uses it.

**Two things I asserted that were wrong, both caught by Mike asking.** First, I reported `## Now`
as "9 → 3, all three workable" — none of the three counted as workable: `[DB-0809-02]` had no
marker at all (I said I would add `@session:` and did not), and `[DB-0808-04]` carried a stale
`@session:` guarding a half that had been split into its own entry on 08-15. **A marker scoped to
half an item is invisible to the counter, which reads per item.** Both fixed in `b62bb18`. Second,
`scp`-ing two tracked scripts to the VM — chosen to avoid putting routing grants there ahead of
their code — made the next `./deploy.sh` abort on untracked files at those paths. Verified
byte-identical and removed; the avoidance was right, the mechanism was not.

**Added to the plan:** `ROADMAP.md` § **A9 — Product analytics instrumentation**, and the Alpha gate
row now requires it. Mike's framing — *"measure and quantify usage FROM THE START"* — is a
sequencing constraint: Section 3 defines Alpha as when accumulation begins, so instrumentation added
later leaves the least-recoverable weeks unmeasured. Collection largely exists already in
`core/trace.py`; what is missing is a question set and a durable daily rollup. Filed as
`[DB-0818-03]`, opening with a decision rather than a build, and carrying an explicit prohibition on
third-party analytics SDKs, which would ship behavioural data off-box against § Section 0.

**Deployed: NO — and this fragment said "yes" when first written, which is the error worth
recording.** `./deploy.sh` pushed to GitHub and then **aborted on the VM**: the `git pull` refused
to overwrite `scripts/vm_add_swap.sh` and `scripts/vm_memory_watch.py`, which existed there only as
untracked files because this session had `scp`'d them. I cleared the untracked copies, said "re-run
and it will go through", and then **recorded the session as deployed without checking that it had
been re-run.** The VM sat at `2a51f46` — carrying the merged cluster code but *not* the tool
registration, the routing grants, or the `fetch_rendered` memory guards.

**And clearing the blocker broke the thing this session built.** Removing the untracked scripts left
`metatron-memory-watch.timer` pointing at a file that no longer existed, so from 11:53 it failed
every five minutes with `status=2/INVALIDARGUMENT` — the alerting built to make an invisible outage
visible was itself silently down. The swapfile was unaffected, being an `/etc/fstab` entry rather
than a script.

**Two generalisable points.** *"I ran the push"* and *"the commits are offsite"* already have a
loud assertion in `/archive` step 5; **"deploy ran" and "the VM has the code" had no equivalent
check**, and this is the failure mode that gap produces. Second: `scp`-ing a file that is *also
tracked in the repo* creates a guaranteed collision on the next pull — if a script must reach the
VM ahead of a deploy, it belongs in `/tmp`, not at its repo path.

**Resolved same day: deployed as `cad98cc`, and verified by running it rather than reading the
deploy output.** `fetch_rendered` is registered on the VM (70 tools) and rendered a live page there;
the watchdog timer recovered to `Result=success` the moment the pull restored its script. The
correction above stands as written — the failure was recording a deploy that had aborted, and that
happened regardless of the deploy later succeeding.


