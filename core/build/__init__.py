"""
core/build — the vertical that constructs Metatron's capabilities.

Build takes a gap and returns a capability, moving Mike from author to approver.
Two modes, one loop: CONSTRUCT (a gap has no capability, build one) and REPAIR
(a Build-made capability failed; the failure is a gap in the question set, not a
bug report).

Plan: archive/plans/build_vertical_plan_2026-09-24.md (v4.11)

BUILD IS DEVELOPMENT, NOT EXECUTION (ruling 1). It runs in Claude Code on the
Mac, on Mike's subscription; no node here calls a Vertex model. The VM keeps
four jobs and nothing else: filing tickets, serving the read doors, counting
dispatches for the registry's run line, and running the capability once
deployed.

This package lives under core/ rather than at the top level for coverage, not
aesthetics: qa_sweep.sh's py_compile check greps ^(core|tools|scripts)/,
CLAUDE.md's rules index globs core/**, and the change-tier table names core/
paths. A new top-level directory would silently escape all three on day one.
Sequestration comes from the hardcoded deny list in gates.py (core/build/** is
on it — Build may not edit itself), which holds wherever the code lives.

Module map:

  the record shapes
    schemas    the three artifacts, their validators, and the spine rule
    ids        BLD-MMDD-NN allocation, collision-proof across a restart

  the two state homes (plan section 5)
    tickets    the VM inbox: data/personas/{p}/build/tickets.jsonl
    registry   the tracked state: config/build/registry.yaml
    jobs       the Mac job directory: data/build/jobs/{persona}/BLD-.../

  what a node reads
    manifest   what sources exist, as ids — never as values
    policy     standing decision frameworks, tracked under config/build/
    index      Build's own FAISS index, separate from search_memory

  what drives and what guards
    driver     the control layer: node order, one retry, parks, the cursor
    gates      the content gates and the salvaged path deny list
    verify     the check runner — the same scripts the sweep runs
    constitution  constitution alignment at generation time

  what is rendered
    table      the question table: every ledger row, once
    brief      the one file the reviewer and Mike read
    coherence  the periodic set review

  the VM's own tick
    tick       the REPAIR counter and the dispatch counts. Nothing else.

`doors.py` (phase B) is the VM-side read endpoint and is not here yet.
"""
