### 2026-11-13 (Mike's week-long cardiac log stops being sent to Physical Health — a dated persona-level exception) — no code or agent-file change; one VM persona edit, run by Mike — **live on the VM, no deploy needed**

**Outgoing handoff carried:** unchanged from § 2026-11-11. This session did not touch it.

**The request.** On 11-13 at 13:51 (seq 011) Mike asked that his cardiac event log (date, time
and what he was doing at each irregular heartbeat, kept for the cardiologist) stop prompting
symptom questions and stop being "referred out to Physical Health". It was meant as a one-week
exception for this persona.

**What the pipeline had already done, and what it couldn't.** The symptom-question half had
landed: Synth wrote it into the VM's `config/personas/mike.md` as a standing interaction
preference. The routing half had not. Physical Health ran on both cardiac exchanges (13:42 and
13:51), and Synth told Mike it "needs a change on my side". That was accurate, for two reasons:
- **The Coordinator never sees `mike.md`.** The routing layer loads `load_goals()`,
  `load_profile()` and recent context only (`core/orchestrator.py`, `_ROUTING_LAYER_AGENTS`
  branch). Persona preferences in `mike.md` reach the head layer, not routing.
- `config/agents/coordinator.md` line 60 says a logged or tracked health record goes to
  Physical Health "always".

**The fix.** It went into the VM's `config/personas/mike/profile.yaml`, whose `other:` list
`load_profile()` renders word for word into the Coordinator's (and the head layer's) prompt. The
empty `other: []` line was replaced with one entry dated 2026-11-13 to 2026-11-20: cardiac log
entries go to the Diarist only, with no Physical Health routing and no symptom questions,
unless Mike asks for advice or reports a new or worsening symptom. A backup was written to
`profile.yaml.bak-2026-11-13`. **Mike ran the command himself**, because the auto-mode
classifier refused an SSH write to the VM from this session. The line was then confirmed in
place by a read-only check. The server reads the file on every request, so no restart.

**Rejected:**
- A line in `mike.md`: the Coordinator doesn't read that file.
- A carve-out in `coordinator.md`: it's Red tier and agent-wide, for what is a one-user,
  one-week exception. It stays the fallback if Flash-Lite doesn't honour the profile line
  against its agent file's "always".

**Open:**
- The one-week end is model-read, not enforced. Removal on 11-21 is filed as `[DB-1113-01]`
  (Mike asked for it).
- Whether the line is honoured is unverified until the next cardiac entry. The test is that
  Physical Health is absent from that exchange's trace.
- Separately, Synth said at 13:51 that it found no Bupa pre-authorisation letter, which Mike
  believes is in his email. Not investigated this session.

