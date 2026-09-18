"""
core/build — the vertical that constructs Metatron's capabilities.

Build takes a gap and returns a capability, moving Mike from author to approver.
Two modes, one loop: CONSTRUCT (a gap has no capability, build one) and REPAIR
(a Build-made capability failed; the failure is a gap in the question set, not a
bug report).

Plan: archive/plans/build_vertical_plan_2026-09-18.md

This package lives under core/ rather than at the top level for coverage, not
aesthetics: qa_sweep.sh's py_compile check greps ^(core|tools|scripts)/,
CLAUDE.md's rules index globs core/**, and the change-tier table names core/
paths. A new top-level directory would silently escape all three on day one.
Sequestration comes from the writer's hardcoded deny list (core/build/** is on
it — Build may not edit itself), which holds wherever the code lives.

Module map, by execution-order phase:

  phase 1   ids        BLD-MMDD-NN allocation, collision-proof across a restart
            jobs       the append-only ledger and the state replayed from it
            schemas    the three artifacts, their validators, and the spine rule

  phase 2   manifest   what data exists, as ids — never as values
            probe      manifest id -> a fixed, code-written read call
            condense   range fetch, condensed to evidence a judgment can sit on
            settle     what is already answerable: policies first, then data
            policy     standing decision frameworks; what depth: triage reads
            index      Build's own FAISS index, separate from search_memory
            cost       per-job metering, priced through spend_guard

Nothing here writes a tracked file. That rule is enforced in phase 3's writer.
"""
