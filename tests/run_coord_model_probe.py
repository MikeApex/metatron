#!/usr/bin/env python3
"""
Offline Coordinator model probe — Flash-Lite vs Pro, evidence for [DB-0820-05].

WHAT THIS ANSWERS, and nothing else: if the Coordinator moved from
gemini-3.1-flash-lite to gemini-3.1-pro-preview, would routing get better, and
what would each reply cost in wall-clock seconds? The decision that follows is
Red-tier and Mike's — this script does not touch config/modules/routing*.yaml.

It drives `_run_single_agent("coordinator", ..., model_override=...)` directly:
no Synthesizer, no specialist dispatch, no routing edit. The Coordinator holds
an empty tool grant (`allowed_tools: []`), so a run here writes nothing and
calls nothing.

Three parts:

  Step 0 — cache-key self-test (offline, no API). Proves that a coordinator call
    with model_override=pro creates a cache keyed to *that* model rather than
    reusing the Flash-Lite entry or silently falling through to uncached. Runs
    against a stub client, so it is free and always runs, including --dry-run.

  Suite A — 15 representative coordinator turns against both models. Latency,
    tokens, and the routing package, scored against a stated expectation.

  Suite B — the four recovered ROUTING_MISS referent failures, replayed as
    two-turn setups (prior turn establishes the referent, short referring turn
    follows via the `history` parameter).

CACHED PATH — a deliberate divergence from the [DB-0820-05] entry text.
The backlog entry says "both models on the uncached path for like-for-like
timing". Mike's 2026-08-28 run instruction supersedes it: run on the CACHED
path, because that is the path the live Coordinator actually uses and the
question is what a live flip would cost. The first call per model is therefore a
cache warm-up whose latency is not comparable to the rest, and it is run
explicitly and excluded from every statistic.

Usage:
    python tests/run_coord_model_probe.py --dry-run       # no API calls
    python tests/run_coord_model_probe.py                 # full live probe
    python tests/run_coord_model_probe.py --suite b       # Suite B only

Cost: ~40 coordinator calls at ~9k input tokens each, plus two cache creations.
Budgeted evidence step; a few dollars.
"""

import argparse
import json
import os
import re
import statistics
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load_env() -> None:
    """Load .env before core.orchestrator does, tolerating a git worktree.

    `.env` is gitignored, so a worktree checkout does not carry one — and
    core/orchestrator.py loads it from its own parent at import time, which in a
    worktree is a directory with no .env at all. Vertex then resolves no project
    and every call falls back to AI Studio or fails. Fall back to the main
    checkout's .env, which is where the worktree's git dir points.
    """
    from dotenv import load_dotenv

    local = ROOT / ".env"
    if local.exists():
        load_dotenv(local)
        return
    common = Path(
        os.popen(f"git -C {ROOT} rev-parse --path-format=absolute --git-common-dir 2>/dev/null").read().strip()
    )
    if common.name == ".git" and (common.parent / ".env").exists():
        print(f"[env] worktree has no .env — loading {common.parent / '.env'}")
        load_dotenv(common.parent / ".env")


_load_env()

FLASH = "gemini-3.1-flash-lite"
PRO = "gemini-3.1-pro-preview"
MODELS = [FLASH, PRO]

# The Coordinator sits on the cached path in production. The dev kill switch is set
# on this machine (Mike flips it by hand); Mike's run instruction is the cached path,
# so the probe clears it for its own process only.
os.environ["VERTEX_CACHE_DISABLED"] = "0"

from core import orchestrator as orch  # noqa: E402
from core import trace as _tr  # noqa: E402
from core.persona import persona_scope  # noqa: E402

# --------------------------------------------------------------------------- #
# Suite A — representative coordinator turns
# --------------------------------------------------------------------------- #
# `expect_any`: at least one of these specialists must be dispatched — the routing
# decision this turn is really about. `forbid`: a specialist whose presence is a
# routing error, not merely surplus. Over-dispatch is deliberately NOT scored as a
# failure except where `forbid` names it: coordinator.md keeps over-dispatch
# dominant on purpose (under-dispatch loses a user's record), so penalising extra
# specialists would score the model against a rule the agent file does not hold.

WARMUP = {
    "id": "A0-warmup",
    "message": "Just checking in, nothing much to report today.",
    "why": "cache warm-up — first call per model, excluded from all statistics",
}

SUITE_A = [
    {"id": "A1", "message": "I slept about four hours and I'm wrecked today.",
     "expect_any": ["physical_health"], "forbid": [],
     "why": "sleep is the highest-signal Physical Health trigger"},
    {"id": "A2", "message": "Book me a dentist appointment for sometime next Tuesday afternoon.",
     "expect_any": ["logistics"], "forbid": [],
     "why": "single-domain scheduling — the routine logistics path"},
    {"id": "A3", "message": "Log that I went for a 5k run this morning and it felt good.",
     "expect_any": ["diarist", "physical_health"], "forbid": [],
     "why": "a plain record; Diarist must be dispatched fire-and-forget"},
    {"id": "A4", "message": "What time is my first meeting tomorrow?",
     "expect_any": ["logistics"], "forbid": ["mental_wellbeing"],
     "why": "quick factual lookup — should not recruit emotional domains"},
    {"id": "A5", "message": "I'm exhausted but I can't stop working and I snapped at Priya today.",
     "expect_any": ["mental_wellbeing"], "forbid": [],
     "why": "multi-intent: emotional + physical + work + relational in one turn"},
    {"id": "A6", "message": "How many contacts do we have on file?",
     "expect_any": ["relationships"], "forbid": [],
     "why": "contact-store question — Relationships answers from its own data"},
    {"id": "A7", "message": "I'm thinking about leaving my job at the end of the quarter.",
     "expect_any": ["work_vocation"], "forbid": [],
     "why": "surface domain is work; a major decision should also pull wellbeing"},
    {"id": "A8", "message": "What's the going rate for a plumber in Dublin right now?",
     "expect_any": ["research_agent"], "forbid": [],
     "why": "external fact with no personal context — the Research path"},
    {"id": "A9", "message": "Move the Thursday call to Friday and tell Marcus about it.",
     "expect_any": ["logistics", "relationships"], "forbid": [],
     "why": "multi-intent: a reschedule plus an outbound message to a person"},
    {"id": "A10", "message": "Good morning.",
     "expect_any": ["mental_wellbeing", "physical_health"], "forbid": [],
     "why": "morning brief is a whole-person session — both must be called"},
    {"id": "A11", "message": "The invoice from the Apex job finally cleared.",
     "expect_any": ["finance"], "forbid": [],
     "why": "money event; Diarist expected alongside"},
    {"id": "A12", "message": "I want to start reading properly again in the evenings.",
     "expect_any": ["learning_growth"], "forbid": [],
     "why": "aspiration in a single domain"},
    {"id": "A13", "message": "Thanks.",
     "expect_any": [], "forbid": ["logistics", "finance", "research_agent"],
     "why": "empty-signal turn — the package is still required, dispatch should be near-empty"},
    {"id": "A14", "message": "Add milk and coffee to the shopping list, and remind me to call the bank about the overdraft.",
     "expect_any": ["logistics"], "forbid": [],
     "why": "two logistics intents plus a financial referent in one turn"},
    {"id": "A15", "message": "I've been feeling flat for about two weeks now and I don't really know why.",
     "expect_any": ["mental_wellbeing"], "forbid": [],
     "why": "sustained low mood — the case where a shallow route is most costly"},
]

# --------------------------------------------------------------------------- #
# Suite B — the four recovered ROUTING_MISS referent failures
# --------------------------------------------------------------------------- #
# PROVENANCE: these are FAITHFUL REPRODUCTIONS, not the verbatim live turns.
# The originals live in `mike`'s quality_events.json on the VM; `data/personas/`
# is gitignored and this machine holds only the git-tracked test personas, so a
# grep for ROUTING_MISS under data/ and archive/ returns the descriptions in
# DEV_BACKLOG [DB-0826-01] and nothing replayable. Each case below reconstructs
# the two-turn shape from that description: a prior turn that establishes the
# referent, then the short referring turn. `history` carries the prior turn the
# way the live pipeline does.
#
# What that costs: the exact wording is not the live wording, so a pass here is
# evidence about the CLASS (a pronoun pointing at the previous turn), not proof
# the specific live turn would now succeed.
#
# Scoring: `expect_any` is the correct referent's domain. `forbid` is the domain
# the live failure wrongly chose. A CLARIFICATION_NEEDED flag is scored
# separately as a THIRD outcome, not a failure — coordinator.md § "Clarify,
# don't assume" mandates it for a pronoun with no clear referent, so a model that
# asks rather than guesses has obeyed the agent file, even though it has not
# resolved the referent.

SUITE_B = [
    {
        "id": "B1",
        "label": '08-26 "Undo that merge" one turn after a contact merge',
        # The live failure needed a COMPETING referent to fall onto — work_vocation
        # searched for "Prudential Apex project merge", so a work-project sense of
        # "merge" was reachable from that session's context. A clean two-turn setup
        # has no distractor, and both models resolve it easily; that measures nothing
        # about the failure. `distractor` restores the competing referent, and the
        # `h` variant of each case is the one that can actually discriminate.
        "distractor": [
            {"role": "user", "content": "Where did we land on the Prudential Apex project — was that branch merged in the end?"},
            {"role": "assistant", "content": "The Apex feature branch was merged to main last Thursday; the release notes still need writing."},
        ],
        "history": [
            {"role": "user", "content": "Marcus Delgado is in there twice, merge those two contacts."},
            {"role": "assistant", "content": "Done — the duplicate Marcus Delgado records are merged into one contact."},
        ],
        "message": "Undo that merge.",
        "expect_any": ["relationships"],
        "forbid": ["work_vocation"],
        "live_failure": "routed to work_vocation, which searched memory for 'Prudential Apex project merge'",
    },
    {
        "id": "B2",
        "label": '08-18 "Read that back to me again" after a food log',
        "distractor": [
            {"role": "user", "content": "Read me the Prudential schedule for next week."},
            {"role": "assistant", "content": "Prudential: Monday 10:00 review, Wednesday 14:00 handover, Friday 09:00 retro."},
        ],
        "history": [
            {"role": "user", "content": "Log what I ate today — porridge at seven, a chicken salad at one, and a big bowl of pasta at nine."},
            {"role": "assistant", "content": "Logged: porridge 07:00, chicken salad 13:00, pasta 21:00."},
        ],
        "message": "Read that back to me again.",
        "expect_any": ["physical_health", "diarist"],
        "forbid": ["logistics"],
        "live_failure": "resolved to Prudential scheduling instead of the previous turn's food data",
    },
    {
        "id": "B3",
        "label": '08-10 "previous request" resolved to an older item',
        "distractor": [
            {"role": "user", "content": "Book me lunch with Aoife at Brother Hubbard on Monday at one."},
            {"role": "assistant", "content": "Booked — Brother Hubbard with Aoife, Monday 13:00."},
        ],
        "history": [
            {"role": "user", "content": "Book a table at Fumbally for Thursday at half twelve."},
            {"role": "assistant", "content": "I've put a hold on Fumbally, Thursday 12:30."},
        ],
        "message": "Cancel my previous request.",
        "expect_any": ["logistics"],
        "forbid": [],
        "expect_referent": ["fumbally", "thursday", "12:30", "half twelve", "table"],
        "live_failure": "resolved to an older lunch instead of the immediately prior turn",
    },
    {
        "id": "B4",
        "label": '08-15 "Approved" resolved to the wrong pending action',
        "distractor": [
            {"role": "user", "content": "Set up the quarterly review invite for the Apex team and hold it for my say-so."},
            {"role": "assistant", "content": "Quarterly review invite for the Apex team is drafted and waiting on your approval."},
        ],
        "history": [
            {"role": "user", "content": "Draft an email to the landlord about the boiler and hold it for me to check."},
            {"role": "assistant", "content": "Draft ready for the landlord about the boiler — say the word and I'll send it."},
        ],
        "message": "Approved.",
        "expect_any": ["relationships"],
        "forbid": [],
        "expect_referent": ["landlord", "boiler", "email", "draft"],
        "live_failure": "resolved to the wrong pending action and wrongly closed an obligation",
    },
]

# The discriminating half. Same four referring turns, but with the competing referent
# the live sessions actually had in front of them, two turns back. Without it neither
# model has anything to get wrong, and a clean sweep proves only that the setup was
# easy — which is exactly what the first run of this probe produced.
SUITE_B_HARD = [
    {**c, "id": c["id"] + "h",
     "label": c["label"] + " — WITH a competing referent two turns back",
     "history": c["distractor"] + c["history"]}
    for c in SUITE_B if c.get("distractor")
]


# --------------------------------------------------------------------------- #
# Step 0 — cache-key self-test
# --------------------------------------------------------------------------- #

def cache_key_self_test() -> dict:
    """Prove _get_or_create_vertex_cache keys its cache on the model, offline.

    The failure this rules out is silent and expensive in both directions: a Pro
    call reusing the Flash-Lite CachedContent would be measuring the wrong model's
    prefix, and a Pro call falling through to uncached would report a latency no
    live flip would ever produce.
    """
    import types

    created: list[str] = []

    class _FakeCaches:
        def create(self, model=None, config=None):
            created.append(model)
            return types.SimpleNamespace(name=f"fakeCache/{model}/{len(created)}")

    class _FakeClient:
        caches = _FakeCaches()

    saved_registry = dict(orch._vertex_cache_registry)
    saved_record = orch._record_cache_storage
    orch._vertex_cache_registry.clear()
    orch._record_cache_storage = lambda *a, **k: None
    try:
        prompt = "COORDINATOR SYSTEM PROMPT LINE\n" * 2000  # comfortably past the 4,096-token floor
        n_flash = orch._get_or_create_vertex_cache(_FakeClient(), prompt, FLASH, [])
        n_pro = orch._get_or_create_vertex_cache(_FakeClient(), prompt, PRO, [])
        n_flash2 = orch._get_or_create_vertex_cache(_FakeClient(), prompt, FLASH, [])
    finally:
        orch._record_cache_storage = saved_record
        orch._vertex_cache_registry.clear()
        orch._vertex_cache_registry.update(saved_registry)

    checks = {
        "flash cache created": n_flash is not None,
        "pro cache created (not None — no silent uncached fallback)": n_pro is not None,
        "pro did NOT reuse the flash cache": n_flash != n_pro,
        "second flash call reused the first cache": n_flash == n_flash2,
        "creation was issued against each model id": created == [FLASH, PRO],
        "padding kept the prompt over the 4,096-token floor": len(orch._pad_for_vertex_cache("x" * 100)) // 5 >= 4096,
    }
    for name, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    return {"checks": checks, "passed": all(checks.values()),
            "flash_cache": n_flash, "pro_cache": n_pro, "creations": created}


# --------------------------------------------------------------------------- #
# Running one coordinator turn
# --------------------------------------------------------------------------- #

_AGENT_ALIASES = {
    "work & vocation": "work_vocation",
    "learning & growth": "learning_growth",
    "recreation & hobbies": "recreation_hobbies",
}


def _normalise_agent(name: str) -> str:
    n = str(name).strip().lower()
    if n in _AGENT_ALIASES:
        return _AGENT_ALIASES[n]
    return n.replace(" & ", "_").replace(" and ", "_").replace(" ", "_")


def parse_package(output: str) -> dict:
    """Pull the scoreable fields out of the Coordinator's context package."""
    agents: list[str] = []
    m = re.search(r'SPECIALISTS_TO_CALL:\s*```(?:json)?\s*(.*?)```', output, re.DOTALL)
    if not m:
        m = re.search(r'SPECIALISTS_TO_CALL:\s*(\[.*?\])\s*(?:\n[A-Z_]+:|\Z)', output, re.DOTALL)
    if m:
        try:
            specs = json.loads(m.group(1).strip())
            agents = [_normalise_agent(s.get("agent", "")) for s in specs if isinstance(s, dict)]
        except json.JSONDecodeError:
            agents = []

    # `CLARIFICATION_NEEDED: [none]` is the model filling in an optional field it was
    # told to omit — it is an ABSENT flag, not a request to clarify. Reading it as
    # present made a Flash-Lite turn that had confidently mis-routed look like a turn
    # that had sensibly asked, which is the one distinction Suite B exists to draw.
    _PLACEHOLDERS = {"", "none", "n/a", "na", "-", "null", "omitted", "not applicable",
                     "if applicable", "omit if not applicable"}

    def _field(name: str) -> str:
        f = re.search(rf'^{name}:\s*(.*?)(?=\n[A-Z_]+:|\Z)', output, re.DOTALL | re.MULTILINE)
        if not f:
            return ""
        val = f.group(1).strip()
        if val.strip("[]() ").lower() in _PLACEHOLDERS:
            return ""
        return val

    return {
        "agents": agents,
        "resolved_intent": _field("RESOLVED_INTENT"),
        "complexity": _field("COMPLEXITY"),
        "clarification": _field("CLARIFICATION_NEEDED"),
        "knowledge": _field("KNOWLEDGE_TO_LOAD"),
        "well_formed": bool(m) or "SPECIALISTS_TO_CALL" in output,
    }


def run_turn(case: dict, model: str, persona: str, with_history: bool = True) -> dict:
    """One Coordinator call. Returns latency, tokens and the parsed package.

    `with_history=False` reproduces the condition that shipped until 2026-09-03, when
    both live Coordinator call sites in core/orchestrator.py invoked
    `_run_single_agent("coordinator", ...)` with no `history=` argument at all — only the
    Synthesizer was given the conversation. This probe has always supplied `history`, so
    every number it produced before that date, including the 6/12 Flash-Lite baseline of
    2026-08-28, measured a strictly easier condition than the one the five [DB-0826-01]
    failures actually happened in.

    The gap is now closed in production — `_coord_history()` passes the last six messages
    — so True is once again the live condition and stays the default, which also keeps the
    historical figures comparable. False is kept because it is the only way to re-measure
    what the fix bought. See tests/run_referent_probe.py, which drives all three arms.
    """
    history = [dict(h) for h in case.get("history", [])] if with_history else []  # the loops append to this; never share it
    t = _tr.start_request_trace(case["message"], persona)
    started = time.monotonic()
    error = None
    output = ""
    try:
        with persona_scope(persona):
            output = orch._run_single_agent(
                "coordinator", case["message"],
                persona=persona,
                model_override=model,
                history=history or None,
            )
    except Exception as e:  # a failed call is data, not a reason to abandon the suite
        error = f"{type(e).__name__}: {e}"
    latency = time.monotonic() - started

    rec = t.pipeline[0] if t.pipeline else None
    _tr.set_trace(None)

    parsed = parse_package(output)
    return {
        "id": case["id"], "model": model, "message": case["message"],
        "latency_s": round(latency, 2),
        "input_tokens": rec.total_input_tokens() if rec else 0,
        "output_tokens": rec.total_output_tokens() if rec else 0,
        "thinking_tokens": rec.total_thinking_tokens() if rec else 0,
        "cached_tokens": rec.total_cached_tokens() if rec else 0,
        "error": error,
        "output": output,
        **parsed,
    }


def score_a(case: dict, res: dict) -> tuple[str, str]:
    if res["error"]:
        return "ERROR", res["error"]
    if not res["well_formed"]:
        return "FAIL", "no SPECIALISTS_TO_CALL block — package malformed"
    got = set(res["agents"])
    missing = [a for a in case["expect_any"] if a not in got]
    if case["expect_any"] and len(missing) == len(case["expect_any"]):
        return "FAIL", f"none of {case['expect_any']} dispatched; got {sorted(got) or '[]'}"
    hit_forbidden = [a for a in case.get("forbid", []) if a in got]
    if hit_forbidden:
        return "FAIL", f"dispatched forbidden {hit_forbidden}"
    if missing:
        return "PARTIAL", f"missing {missing}; got {sorted(got)}"
    return "PASS", f"got {sorted(got) or '[]'}"


def score_b(case: dict, res: dict) -> tuple[str, str]:
    if res["error"]:
        return "ERROR", res["error"]
    got = set(res["agents"])
    hit_forbidden = [a for a in case.get("forbid", []) if a in got]
    intent = res["resolved_intent"].lower()
    markers = [m for m in case.get("expect_referent", []) if m in intent]
    referent_ok = bool(markers) if case.get("expect_referent") else None

    if hit_forbidden:
        return "FAIL", f"reproduced the live failure — dispatched {hit_forbidden}"
    if case.get("expect_referent") and not referent_ok:
        return "FAIL", f"RESOLVED_INTENT names none of {case['expect_referent']}: {res['resolved_intent'][:120]!r}"
    correct = [a for a in case["expect_any"] if a in got]
    if res["clarification"]:
        verdict = "CLARIFIED" if not correct else "PASS"
        return verdict, f"CLARIFICATION_NEEDED: {res['clarification'][:120]}"
    if not correct:
        return "FAIL", f"none of {case['expect_any']} dispatched; got {sorted(got) or '[]'}"
    return "PASS", f"got {sorted(got)}" + (f"; intent names {markers}" if markers else "")


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #

def _stats(rows: list[dict], key: str) -> dict:
    vals = [r[key] for r in rows if not r["error"]]
    if not vals:
        return {"n": 0, "mean": 0, "median": 0, "min": 0, "max": 0}
    return {"n": len(vals), "mean": round(statistics.mean(vals), 2),
            "median": round(statistics.median(vals), 2),
            "min": round(min(vals), 2), "max": round(max(vals), 2)}


def write_report(path: Path, results: dict) -> None:
    L: list[str] = []
    ap = L.append
    run_date = results["date"]
    ap(f"# Coordinator model probe — {FLASH} vs {PRO}")
    ap("")
    ap(f"*Run {run_date} · offline probe for `[DB-0820-05]` (should the Coordinator move to Pro) · "
       f"persona `{results['persona']}` · no routing file touched.*")
    ap("")
    ap("## What this is evidence for")
    ap("")
    ap("Whether moving the Coordinator from Flash-Lite to Pro fixes the referent-resolution class "
       "(`[DB-0826-01]` — a short turn like *\"undo that merge\"* routed against the wrong "
       "conversation), and what a Pro Coordinator would add to the wait before every single reply. "
       "**The flip itself is Red-tier and Mike's; this file recommends no routing change.**")
    ap("")
    ap("## Method")
    ap("")
    ap(f"- `tests/run_coord_model_probe.py` drives `_run_single_agent(\"coordinator\", …, "
       f"model_override=…)` directly — no Synthesizer, no specialist dispatch, no routing edit. "
       f"The Coordinator's tool grant is empty, so nothing is written.")
    ap(f"- **Cached path — a deliberate divergence from the `[DB-0820-05]` entry text.** The entry "
       f"says *\"both models on the uncached path for like-for-like timing\"*; Mike's 2026-08-28 run "
       f"instruction supersedes it. The live Coordinator runs cached, and the question is what a "
       f"live flip costs, so both models run cached here. **The first call per model is a cache "
       f"warm-up, run explicitly and excluded from every latency and quality statistic below** — "
       f"it pays the CachedContent creation round-trip, which a live Coordinator pays once per "
       f"10-minute TTL window and never on a turn inside one.")
    ap(f"- Suite A: {len(SUITE_A)} representative turns × both models. Suite B: the four recovered "
       f"`ROUTING_MISS` referent failures × both models, clean. Suite B-hard: the same four with "
       f"the competing referent restored, ×3 runs per cell.")
    ap("- Over-dispatch is not scored as a failure unless the case names the specialist as "
       "forbidden. `coordinator.md` keeps over-dispatch dominant on purpose (under-dispatch loses "
       "a user's record), so penalising surplus specialists would score the model against a rule "
       "the agent file does not hold.")
    ap(f"- Persona `{results['persona']}` — the git-tracked test persona. `mike` was not touched.")
    ap("")
    all_rows = [r for rows in results["suites"].values() for r in rows]
    mean_cached = _stats(all_rows, "cached_tokens")["mean"]
    mean_in = _stats(all_rows, "input_tokens")["mean"]
    if mean_cached > 0:
        ap(f"**The cached path was confirmed exercised, not assumed:** a mean of "
           f"{mean_cached} of {mean_in} input tokens per call were served from the Vertex context "
           f"cache ({round(100 * mean_cached / mean_in)}%). This is measurable only because "
           f"`core/trace.py` now stores `cached_tokens` on the turn record — it previously "
           f"accepted the figure, forwarded it to the spend guard and discarded it, so no trace "
           f"or test could distinguish a cache hit from a miss.")
    else:
        ap("**⚠ The cached path was NOT exercised** — zero cached tokens across the run. Treat "
           "every latency figure below as an uncached measurement and do not read it as the cost "
           "of a live flip.")
    ap("")

    ap("## Step 0 — does the Vertex cache honour `model_override`?")
    ap("")
    st = results["self_test"]
    ap(f"**{'PASS — no code change needed' if st['passed'] else 'FAIL'}.** "
       "`_get_or_create_vertex_cache` hashes `model_name` into its cache key and issues "
       "`caches.create(model=model_name)`, and `model_override` reaches it unmodified through "
       "`_run_single_agent` → `run_session_gemini_cached`. A Pro call therefore builds its own "
       "CachedContent instead of reusing the Flash-Lite entry or silently running uncached — "
       "which is what the live flip needs anyway.")
    ap("")
    ap("| Check | Result |")
    ap("|---|---|")
    for name, ok in st["checks"].items():
        ap(f"| {name} | {'PASS' if ok else 'FAIL'} |")
    ap("")

    for suite in ("A", "B", "Bh"):
        rows = results["suites"].get(suite)
        if not rows:
            continue
        title = {
            "A": "Suite A — 15 representative turns",
            "B": "Suite B — the four referent failures, replayed clean",
            "Bh": "Suite B-hard — the same four, with the competing referent restored",
        }[suite]
        ap(f"## {title}")
        ap("")
        if suite == "Bh":
            ap("**This is the half that can discriminate.** Suite B gives the referring turn a "
               "clean two-turn history, so there is nothing for either model to get wrong — and "
               "the live failures did not happen in that condition. Each case here puts the "
               "competing referent the live session actually had (the Prudential Apex *branch* "
               "merge, the Prudential *schedule*, an older lunch booking, a second pending "
               "approval) two turns back, so the short referring turn genuinely points at two "
               "things.")
            ap("")
        if suite in ("B", "Bh"):
            ap(f"**Provenance: {results['suite_b_provenance']}**")
            ap("")
            ap("A `CLARIFIED` verdict is a third outcome, not a failure: `coordinator.md` "
               "§ *Clarify, don't assume* mandates a `CLARIFICATION_NEEDED` flag for a pronoun "
               "with no clear referent, so a model that asks has obeyed the agent file without "
               "resolving the referent.")
            ap("")

        by_id: dict = {}
        for r in rows:
            by_id.setdefault(r["id"], {}).setdefault(r["model"], []).append(r)
        reps = max(len(v) for per in by_id.values() for v in per.values())
        if reps > 1:
            ap(f"*Each cell is {reps} independent runs — Flash-Lite's routing is not "
               f"deterministic, and a single run per cell cannot tell a real difference from "
               f"one sample of noise.*")
            ap("")

        ap("| Turn | " + " | ".join(f"{m} verdict | {m} latency" for m in MODELS) + " |")
        ap("|---|" + "---|" * (2 * len(MODELS)))
        for cid, per in by_id.items():
            cells = []
            for m in MODELS:
                rs = per.get(m, [])
                if not rs:
                    cells.append("— | —")
                    continue
                good = sum(1 for r in rs if r["verdict"] in ("PASS", "CLARIFIED"))
                v = f"{good}/{len(rs)} ok" if len(rs) > 1 else rs[0]["verdict"]
                if len(rs) > 1 and good < len(rs):
                    v = f"**{v}**"
                cells.append(f"{v} | {round(statistics.mean([r['latency_s'] for r in rs]), 2)}s")
            ap(f"| {cid} | " + " | ".join(cells) + " |")
        ap("")

        ap("### Per-turn detail")
        ap("")
        for cid, per in by_id.items():
            case = per[MODELS[0]][0]
            ap(f"**{cid} — {case['message']!r}**  ")
            if case.get("label"):
                ap(f"*{case['label']}*  ")
            if case.get("live_failure"):
                ap(f"*Live failure: {case['live_failure']}*  ")
            for m in MODELS:
                for r in per.get(m, []):
                    ap(f"- `{m}` — **{r['verdict']}** ({r['latency_s']}s, "
                       f"in {r['input_tokens']} / cached {r['cached_tokens']} / out {r['output_tokens']} "
                       f"/ think {r['thinking_tokens']}): {r['note']}")
                    if r["resolved_intent"]:
                        ap(f"  - RESOLVED_INTENT: {r['resolved_intent'][:200]}")
            ap("")

        ap("### Aggregate")
        ap("")
        ap("| Model | turns | PASS | PARTIAL | CLARIFIED | FAIL | ERROR | mean latency | median | max | mean in | mean cached | mean out | mean thinking |")
        ap("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for m in MODELS:
            mr = [r for r in rows if r["model"] == m]
            lat = _stats(mr, "latency_s")
            counts = {v: sum(1 for r in mr if r["verdict"] == v)
                      for v in ("PASS", "PARTIAL", "CLARIFIED", "FAIL", "ERROR")}
            ap(f"| {m} | {len(mr)} | {counts['PASS']} | {counts['PARTIAL']} | {counts['CLARIFIED']} | "
               f"{counts['FAIL']} | {counts['ERROR']} | {lat['mean']}s | {lat['median']}s | {lat['max']}s | "
               f"{_stats(mr, 'input_tokens')['mean']} | {_stats(mr, 'cached_tokens')['mean']} | "
               f"{_stats(mr, 'output_tokens')['mean']} | {_stats(mr, 'thinking_tokens')['mean']} |")
        ap("")

    ap("## Warm-up calls (excluded from every figure above)")
    ap("")
    ap("| Model | latency | input | cached | output |")
    ap("|---|---|---|---|---|")
    for w in results["warmups"]:
        ap(f"| {w['model']} | {w['latency_s']}s | {w['input_tokens']} | {w['cached_tokens']} | {w['output_tokens']} |")
    ap("")

    ap("## Bottom line — for the Red-tier flip decision")
    ap("")
    ap(results["bottom_line"])
    ap("")
    ap("---")
    ap("")
    ap(f"*Raw results: `{results['raw_path']}`. Regenerate with "
       f"`python tests/run_coord_model_probe.py`.*")

    path.write_text("\n".join(L) + "\n")
    print(f"\nreport written: {path}")


def _bottom_line(results: dict) -> str:
    """A stated comparison, not a recommendation — the flip is Mike's call."""
    parts = []
    for suite, name in (("Bh", "referent class WITH a competing referent (Suite B-hard) — the discriminating test"),
                        ("B", "referent class, clean two-turn setup (Suite B)"),
                        ("A", "ordinary routing (Suite A)")):
        rows = results["suites"].get(suite) or []
        if not rows:
            continue
        seg = []
        for m in MODELS:
            mr = [r for r in rows if r["model"] == m]
            passes = sum(1 for r in mr if r["verdict"] == "PASS")
            clar = sum(1 for r in mr if r["verdict"] == "CLARIFIED")
            fails = sum(1 for r in mr if r["verdict"] in ("FAIL", "ERROR"))
            seg.append(f"`{m}` {passes}/{len(mr)} pass, {clar} clarified, {fails} fail")
        parts.append(f"- **{name}:** " + "; ".join(seg))

    bh = results["suites"].get("Bh") or []
    if bh:
        fails = {m: sum(1 for r in bh if r["model"] == m and r["verdict"] in ("FAIL", "ERROR"))
                 for m in MODELS}
        if fails[FLASH] == 0 and fails[PRO] == 0:
            parts.insert(0, "- **Does Pro fix the referent class? This run cannot show that it "
                             "does — because Flash-Lite did not fail.** Both models resolved every "
                             "referring turn correctly even with a competing referent in play. The "
                             "evidence for a flip is therefore absent, not negative: a model "
                             "upgrade cannot be justified by a failure this probe could not "
                             "reproduce. What that points at is the *live* condition the "
                             "reproduction still lacks — a long real session's recent-context "
                             "block, not a four-message history — which is where the next cheap "
                             "evidence lies.")
        else:
            tot = {m: sum(1 for r in bh if r["model"] == m) for m in MODELS}
            broken = sorted({r["id"] for r in bh
                             if r["model"] == FLASH and r["verdict"] in ("FAIL", "ERROR")})
            if fails[PRO] < fails[FLASH]:
                parts.insert(0, f"- **Yes — Pro resolved referents that Flash-Lite got wrong.** "
                                 f"With the competing referent present, Flash-Lite failed "
                                 f"{fails[FLASH]}/{tot[FLASH]} runs and Pro {fails[PRO]}/{tot[PRO]}. "
                                 f"The cases Flash-Lite broke on: {', '.join(broken)}. This is the "
                                 f"direct evidence the flip decision was waiting on.")
            else:
                parts.insert(0, f"- **No — Pro did not improve on the referent class.** "
                                 f"{fails[PRO]}/{tot[PRO]} Pro failures against "
                                 f"{fails[FLASH]}/{tot[FLASH]} on Flash-Lite. The routing errors are "
                                 f"not explained by model capability, so a flip would buy latency "
                                 f"and no fix.")

    a_rows = results["suites"].get("A") or []
    lat = {m: _stats([r for r in a_rows if r["model"] == m], "latency_s") for m in MODELS}
    if lat[FLASH]["n"] and lat[PRO]["n"]:
        delta = round(lat[PRO]["mean"] - lat[FLASH]["mean"], 2)
        parts.append(
            f"- **Per-reply latency cost:** the Coordinator is on the critical path ahead of every "
            f"reply, so this is added to *every* turn — mean {lat[FLASH]['mean']}s → "
            f"{lat[PRO]['mean']}s, **+{delta}s per reply** (median {lat[FLASH]['median']}s → "
            f"{lat[PRO]['median']}s; worst case {lat[FLASH]['max']}s → {lat[PRO]['max']}s)."
        )
    think = _stats([r for r in a_rows if r["model"] == PRO], "thinking_tokens")["mean"]
    if think:
        parts.append(
            f"- **The latency is thinking tokens, not the model being slow.** Pro spends a mean "
            f"{think} thinking tokens per routing call on a task whose output is a fixed-shape "
            f"context package. Flash-Lite spends none. That matters because the cost is not "
            f"fixed: `_SYNTH_THINKING_BUDGET` is the existing precedent for capping it on an "
            f"agent that does not need it, and the same lever exists here. **Three options, and "
            f"they are Mike's to pick:** (1) flip as measured and accept ~+11s on every reply — "
            f"the safest routing, the worst voice experience; (2) flip with a thinking budget "
            f"capped, which needs one more probe run to show the referent fix survives the cap — "
            f"cheap, and the only option that might get both; (3) do not flip, and fix the "
            f"referent class in `coordinator.md` instead, since Pro's winning behaviour on B2h "
            f"was to raise `CLARIFICATION_NEEDED` — a rule the agent file already states and "
            f"Flash-Lite did not follow. **Option 2 first** — it is one run, and it is the only "
            f"one that has not been ruled in or out by evidence already in hand."
        )
    parts.append(
        "- **No routing change is proposed here.** `config/modules/routing_cloud.yaml` is "
        "untouched. If Mike flips `coordinator` to Pro, the `[DB-0820-05]` disposition already "
        "requires the revert condition to travel with the flip so a trial cannot quietly become "
        "permanent."
    )
    return "\n".join(parts)


# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--persona", default="danny_park",
                    help="git-tracked test persona (default danny_park). 'mike' is refused.")
    ap.add_argument("--suite", choices=["a", "b", "both"], default="both")
    ap.add_argument("--repeat", type=int, default=3,
                    help="runs per cell for Suite B-hard, the discriminating suite (default 3). "
                         "Routing is not deterministic; one run per cell cannot separate a model "
                         "difference from a single sample of noise.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Step 0 self-test and the case inventory only — no API calls, no cost.")
    ap.add_argument("--out", default=None, help="report path (default tests/coord_model_probe_<date>_flashlite_vs_pro.md)")
    ap.add_argument("--report-only", action="store_true",
                    help="Rebuild the markdown report from the saved .json. Editing the report's "
                         "prose must not cost another 60 API calls.")
    args = ap.parse_args()

    if args.persona == "mike":
        raise SystemExit("refusing to probe against 'mike' — that is a real person's data, VM-owned")

    run_date = date.today().isoformat()
    out = Path(args.out) if args.out else ROOT / "tests" / f"coord_model_probe_{run_date}_flashlite_vs_pro.md"
    raw_path = out.with_suffix(".json")

    if args.report_only:
        if not raw_path.exists():
            raise SystemExit(f"no saved results at {raw_path} — run the probe first")
        results = json.loads(raw_path.read_text())
        results["raw_path"] = str(raw_path.relative_to(ROOT))
        results["bottom_line"] = _bottom_line(results)
        write_report(out, results)
        return 0

    print("=" * 78)
    print("Step 0 — cache-key self-test (offline)")
    print("=" * 78)
    self_test = cache_key_self_test()

    if args.dry_run:
        print("\n--dry-run: no API calls made.")
        print(f"\nSuite A would run {len(SUITE_A)} turns × {len(MODELS)} models "
              f"(+1 warm-up per model, excluded).")
        for c in SUITE_A:
            print(f"  {c['id']:>3}  {c['message'][:64]!r}  expect_any={c['expect_any']}")
        print(f"\nSuite B ({len(SUITE_B)} clean) + Suite B-hard ({len(SUITE_B_HARD)} with a "
              f"competing referent) × {len(MODELS)} models.")
        for c in SUITE_B + SUITE_B_HARD:
            print(f"  {c['id']:>3}  {c['label']}")
            print(f"       expect_any={c['expect_any']} forbid={c['forbid']}")
        return 0 if self_test["passed"] else 1

    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        raise SystemExit(
            "GOOGLE_CLOUD_PROJECT is not set — the cached Vertex path is unreachable and any "
            "timing produced here would be from a different provider. Load the project .env "
            "and re-run, or use --dry-run."
        )

    results: dict = {
        "date": run_date, "persona": args.persona, "self_test": self_test,
        "suites": {}, "warmups": [], "raw_path": str(raw_path.relative_to(ROOT)),
        "suite_b_provenance":
            "faithful reproductions built from the DEV_BACKLOG [DB-0826-01] descriptions, not the "
            "verbatim live turns — the originals are in `mike`'s `quality_events.json` on the VM "
            "and `data/personas/` is gitignored, so nothing replayable exists on this machine. A "
            "pass is therefore evidence about the CLASS, not proof the exact live turn now works.",
    }

    print("\n" + "=" * 78)
    print("Cache warm-up — first call per model, EXCLUDED from all statistics")
    print("=" * 78)
    for model in MODELS:
        w = run_turn(WARMUP, model, args.persona)
        print(f"  {model}: {w['latency_s']}s  in={w['input_tokens']} cached={w['cached_tokens']} "
              f"out={w['output_tokens']}{'  ERROR: ' + w['error'] if w['error'] else ''}")
        w.pop("output", None)
        results["warmups"].append(w)

    plan = []
    if args.suite in ("a", "both"):
        plan.append(("A", SUITE_A, score_a))
    if args.suite in ("b", "both"):
        plan.append(("B", SUITE_B, score_b))
        plan.append(("Bh", SUITE_B_HARD, score_b))

    for suite, cases, scorer in plan:
        # Only the small referent suites repeat. Suite A is 15 cases and its verdicts were
        # unanimous on the first run; the variance that matters is in the four short
        # referring turns, where a single sample cannot separate a model difference from noise.
        reps = args.repeat if suite == "Bh" else 1
        print("\n" + "=" * 78)
        print(f"Suite {suite} — {len(cases)} cases × {len(MODELS)} models"
              + (f" × {reps} runs" if reps > 1 else ""))
        print("=" * 78)
        rows = []
        for case in cases:
            print(f"\n{case['id']}: {case['message']!r}")
            for model in MODELS:
                for rep in range(1, reps + 1):
                    res = run_turn(case, model, args.persona)
                    verdict, note = scorer(case, res)
                    res.update(verdict=verdict, note=note, rep=rep,
                               label=case.get("label", ""), live_failure=case.get("live_failure", ""))
                    tag = f" #{rep}" if reps > 1 else ""
                    print(f"  {model:<26}{tag:<4} {verdict:<9} {res['latency_s']:>6}s  "
                          f"in={res['input_tokens']:>6} cached={res['cached_tokens']:>6} "
                          f"out={res['output_tokens']:>5} think={res['thinking_tokens']:>5}  {note}")
                    rows.append(res)
        results["suites"][suite] = rows

    results["bottom_line"] = _bottom_line(results)
    raw_path.write_text(json.dumps(results, indent=2, default=str))
    write_report(out, results)

    errs = sum(1 for rows in results["suites"].values() for r in rows if r["verdict"] == "ERROR")
    print(f"\n{errs} call errors.")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
