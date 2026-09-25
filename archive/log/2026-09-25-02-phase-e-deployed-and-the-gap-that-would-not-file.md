### 2026-09-25, second (phase E — Build is on the VM, and the one thing it cannot yet do) — `347926c`, `067c196`, `82cb225`, `20f1577`, `4f0a6c3` — **DEPLOYED: the VM moved `7bca654` → `4f0a6c3`, 33 commits, 130 files**

Phase E, the catch-up deploy with Build inside it. Everything in `core/build/` is now live on the
VM, along with the headset `source` field and three weeks of unrelated work. Five of seven probes
pass. The one that does not is the premise the whole vertical rests on.

**THE CHECKLIST'S OWN COMMANDS HAD FIVE DEFECTS, AND RUNNING ONE FOUND THEM ALL.** Every remote
command was written as `ssh metatron-vm`, which returns `Permission denied (publickey)` — the VPC has
had no public SSH ingress since 2026-07-31, only tcp:22 from the IAP range, so everything must go
through `gcloud compute ssh --tunnel-through-iap` (`deploy.sh:115-118`). The VM's checkout is
`~/multi-model-mcp`, not `~/metatron`. `vm_read.py` takes `presence log` positionally, not
`--presence log`. Two inline `#` comments would have run as arguments. All written carefully, none
executed, exactly the lesson of the session before.

**THE VM WAS NEVER WHERE THE RECORD SAID, AND THE ROLLBACK COMMAND IS WHERE THAT WOULD HAVE LANDED.**
Seven places said `b2b1dc7`; the VM was at `7bca654`, four commits further on — the 09-09/09-10
calendar-invitation fixes, deployed ~09-10 with nothing recording it. `b2b1dc7` had been asserted
since the 09-18 fragment, where it was already wrong, and three fragments on 09-24 repeated it.
**The phase-E rollback said `git checkout b2b1dc7`: run during an incident, the only time anyone runs
it, that reverts four commits the VM is already serving.** A rollback is the one command nobody
re-derives while reading it. `CLAUDE.md` § Infrastructure traps rule 2 — never record a value with a
short half-life — governs deploy SHAs, and failed in precisely the shape it describes.

**THE DEPLOY ABORTED FIRST, ON THE MIRROR IMAGE OF THE 2026-08-20 LANDMINE.** `scripts/renew_cert.sh`
existed **untracked on the VM** and arrives tracked from `579908e`; git refused the merge, correctly,
and `set -e` stopped the remote heredoc before `pip install` and before both restarts, so nothing
deployed. Pre-flight gate 1 asks *what is uncommitted on the Mac that committed code imports*; this
asks *what exists untracked on the VM that the incoming range brings under version control*. Added as
**gate 5** — the intersection of the VM's untracked files with the incoming paths — with three checks
per hit, because delete-and-retry is wrong on a file whose name hides what depends on it: this one
keeps the TLS certificate alive. Back up and diff (identical here); find what executes it (the 04:30
timer ran exactly that path); **check git's recorded mode — `100755` keeps the executable bit through
the pull, `100644` silently strips it and the timer fails nightly with the cert expiring ~90 days
later and nothing saying so.** It was `100755`.

**What passed.** Read door answering five real sources for `mike` (`log` 15, `conversations` 11,
`goals` 3, `wisdom` 16, `email` 6) with content withheld, and the live feeds refusing exactly as
designed — `weather` and `flights` return `state: live` with *"no outbound tool sits behind a door"*.
`build_tick` resolving in the scheduler log with the success string, not `ModuleNotFoundError`. The
`--persona mike` pipeline turn, **which closes phase A's owed (M)** — it cannot run on the Mac in any
tree. The host marker live on both units as a systemd **drop-in**, chosen over an in-place unit edit
because `docs/INFRASTRUCTURE.md`'s rebuild step rewrites the unit text and would silently revert it.
And `request_build`'s plumbing end to end: `BLD-0925-01` filed for a fixture persona with a complete
row and its `BUILD_PROPOSED` second record, so tool → `file_ticket` → writer allowlist → id
allocation → ledger → quality event all work on the deployed code.

**WHAT FAILED IS THE JUDGEMENT, AND IT IS THE PREMISE OF THE VERTICAL.** Asked *"when did I last water
the fig?"* — a shape-2 gap, a last-done date nothing performs, and the exact failure recorded on
09-11, 09-14 and 09-15 — the Coordinator answered from context and filed nothing. Diagnosed as
placement: `request_build`'s four shapes sat in § Tools available, a reference section, while the
six-step procedure mentioned the tool once at 2b, scoped to shape 1 because the `ROUTING_MISS` fork
had to disambiguate it. Shapes 2–4 had no entry point at all. Fixed in `4f0a6c3` — the trigger moved
into step 4 as *"a job nobody owns"*, § Tools available keeps the tool and points at it (One Home Per
Rule Class), net +2 lines, and the gap rule now explicitly outranks the standing-knowledge clause
whose *"omitting a specialist is only correct when a fact already on file answers the message
completely"* was being read as licence to omit the gap too. **Deployed, asked again, still no ticket.**

**So placement was not the binding constraint, and Mike had it right before I did:** *"Coord and the
subagents are liable to try to solve any query rather than admit they can't."* **Mike's proposed test
— declare a capability absent on a subagent so a request must route to Build — is also right, and my
objection to it was wrong on the facts.** I argued it would only exercise shape 1, the working path.
Reading the specialist directory properly: Research Agent claims *"any external query"* and *"how to
[general knowledge], best way to, options for"*, so **no class is naturally unowned** — declaring one
is the only way to make any shape deterministic.

*Rejected: reverting `4f0a6c3`.* The rule belonged in the procedure and 2b's pointer was genuinely
misleading; it is not the fix but it is not wrong. *Rejected: more prompt wording.* Two anecdotes,
both negative, no variance — tuning against that is guesswork. **The next step is measurement, not
instruction:** `tests/run_b1_redteam.py` already runs live through `run_pipeline_session()`, so a
`--suite build_trigger` with three must-file and three must-not-file requests is the fixture
`config/modules/routing_cloud.yaml:66` **already claims exists and never did** — my own phase B-Red
comment, asserting a test for the case the same comment calls *"the expensive one and it is silent."*

**Owed, none blocking.** One line in `docs/INFRASTRUCTURE.md` § Systemd units recording the drop-in,
or a rebuild drops the marker — and that stanza is **stale anyway**: it carries
`METATRON_PERSONA_STRICT=0`/`FALLBACK=mike` and no `PYTHONUNBUFFERED`, while the live units carry the
reverse. Not a defect — strict is `core/persona.py`'s documented default and the safer state — but a
VM rebuilt from that doc silently re-enables audit-mode fallback. The eight specialists still hold
`request_build` with no filing instruction (16 class-3 advisories). `file_ticket`'s code half, now
that `METATRON_HOST=vm` is real.

**Cost.** Phase E's deploy was inside estimate; the Coordinator work after it is outside § 14
altogether — development the probe discovered, not phase E. Build stands at ≈**$75–100** of $65–106
with **F** (bootstrap runs 1–3, live walkthrough) still to come.

