"""
tools/subagent.py — run a specialist sub-agent session and return its output.

Used by the Coordinator to fan out to specialists. Each call spawns a
full run_session() with the named agent's instruction file and the shared
data context. The active persona is resolved and passed through automatically.
"""

import logging
import os
import threading

from core.persona import current_persona
from core.trace import get_subagent_depth, set_subagent_depth

logger = logging.getLogger(__name__)

# CODE-ONLY AGENTS — reachable from Python, never from another agent
# (archive/plans/multi_user_accounts_plan_2026-10-26.md § 4.11, review P4).
#
# Each of these is built to take input that CODE assembles and to run bare with an empty
# tool grant (config/modules/routing_cloud.yaml). Their callers reach them through
# run_session directly — tools/tone.py `_extract`, tools/intake_extract.py,
# tools/accountability.py, tools/day_plan.py, tools/crm_sweep.py — and those callers hold
# the checks that make the call legitimate: `tone_profiler` runs only under the user's
# current `tone_profile` permission (tools/tone.py). run_subagent passes any name through
# to run_session, so an agent holding it could otherwise call one of these below that
# check. No config/agents/*.md file names one as a dispatch target, so refusing them here
# costs no existing route (tests/test_consent_enforcement.py greps for it).
CODE_ONLY_AGENTS = frozenset({
    "tone_profiler", "intake_extractor", "accountability_judge", "day_planner", "crm_sweep",
})


def _code_only_refusal(agent_name: str) -> str | None:
    """The refusal for a code-only agent, or None for any other name.

    The name is normalised the way a file lookup would see it — case, separators, and any
    path prefix — because core.orchestrator.load_agent() opens config/agents/{name}.md, and
    on a case-insensitive disk "Tone_Profiler" or "../agents/tone_profiler" would load the
    same file the exact name is refused for."""
    norm = os.path.basename(os.path.normpath(str(agent_name or "").strip()))
    norm = norm.lower().replace("-", "_").replace(" ", "_")
    if norm.endswith(".md"):
        norm = norm[:-3]
    if norm in CODE_ONLY_AGENTS:
        logger.warning(f"[subagent] refused dispatch of code-only agent {agent_name!r}")
        return (
            f"Error: '{agent_name}' cannot be called as a sub-agent — it runs only from "
            f"the system's own code. Carry on without it."
        )
    return None


def run_subagent(agent_name: str, message: str, complexity: str = "",
                 fire_and_forget: bool = False) -> str:
    """
    Spawn a specialist agent session and return its response.

    complexity: "quick" routes to the fast/cheap model tier (Gemini Flash);
                "deep" routes to the agent's configured target model;
                omit or pass "" to use the agent's default routing.

    fire_and_forget: when True, dispatch in a background thread and return
                     immediately without waiting for the result. Use for
                     write-only agents (Diarist) that don't need to block
                     the Coordinator's context package.

    The current persona is resolved on the calling thread and passed explicitly to
    the specialist session, so specialists see the same config context as the
    Coordinator session — including on the fire-and-forget path.
    """
    from core.orchestrator import run_session

    # Before anything else, and before any model call: see CODE_ONLY_AGENTS.
    refusal = _code_only_refusal(agent_name)
    if refusal:
        return refusal

    # Recursion guard, DEPTH-AWARE since 2026-09-24 rather than binary.
    #
    # It used to refuse at depth >= 1: only the Coordinator could spawn. That was
    # right while the graph was two layers, and it blocks the four-layer one Mike
    # ruled for on 2026-09-24 — Coord -> category router -> tier-3 agent -> Synth,
    # where a category agent's whole job is to fan out to the narrow agents Build
    # constructs beneath it (build plan v3.7 § 2, "the tier"). A binary guard makes
    # that architecture unreachable.
    #
    # MAX_SUBAGENT_DEPTH = 2 admits exactly that chain and nothing longer: depth 0
    # is the Coordinator dispatching a category router, depth 1 is the router
    # dispatching a tier-3 agent, and depth 2 refuses. A tier-3 agent is by
    # definition narrow and has nothing to delegate to, so a call from there is a
    # loop forming, not a design.
    #
    # WHAT THIS IS NOT. The confused-deputy control is architectural and is NOT this
    # guard: `_dispatch_from_coordinator()` is the only function that parses free
    # text into dispatch calls, and its only call site is fed `coord_output` — the
    # Coordinator's own text — never a specialist's. That property is asserted by
    # `tests/run_b1_redteam.py --suite deputy` (security_testing_plan check 6) and is
    # untouched here. It is also why a router must fan out by CALLING run_subagent
    # rather than by having its output parsed for SPECIALISTS_TO_CALL: a second
    # dispatch parser reading agent output would break check 6 directly, and this
    # relaxation exists precisely so that the safe route is available.
    MAX_SUBAGENT_DEPTH = 2
    # Thread-local (core/trace.py), never os.environ: an env value is shared by every
    # request in the process, so one user's nested call would block another's delegation.
    depth = get_subagent_depth()
    if depth >= MAX_SUBAGENT_DEPTH:
        return (
            f"Error: run_subagent cannot be called at delegation depth {depth}. "
            f"The chain is Coordinator -> category agent -> specialist, and this "
            f"session is already at the end of it. "
            f"Perform this task directly without delegating."
        )

    # Resolve on THIS thread, before any background thread starts. A fire-and-forget
    # subagent (the Diarist) outlives the request that spawned it, so it cannot read
    # the persona later — by then the parent scope may have exited.
    persona = current_persona()
    complexity_hint = complexity if complexity in ("quick", "deep") else None

    # Diarist is always write-only — enforce fire_and_forget at the code layer
    # regardless of what the coordinator model passes.
    if agent_name == "diarist":
        fire_and_forget = True

    if fire_and_forget:
        # Captured on this thread: the background thread starts with no depth of its own.
        def _run(child_depth: int = depth + 1) -> None:
            set_subagent_depth(child_depth)
            try:
                run_session(agent_name, user_input=message, persona=persona,
                            complexity=complexity_hint)
            except Exception as e:
                logger.warning(f"[fire_and_forget] {agent_name} failed: {e}")
        threading.Thread(target=_run, daemon=True).start()
        return f"{agent_name}: dispatched (async)"

    set_subagent_depth(depth + 1)
    try:
        return run_session(agent_name, user_input=message, persona=persona,
                           complexity=complexity_hint)
    finally:
        set_subagent_depth(depth)


def run_model_conference(message: str, models: list[str],
                         agent_name: str = "coordinator") -> str:
    """
    Query the same message across multiple model tiers and return all responses.

    Each model in `models` should be a routing tier name: "cloud_fast",
    "cloud_deep", or "cloud_analytical". The caller (Coordinator or specialist)
    receives all responses labeled by tier and synthesizes them.

    Use for high-stakes decisions, analytical questions where model diversity
    adds value, or when a single model's perspective feels insufficient.
    """
    from core.orchestrator import run_session
    from core.router import _load_routing

    # Same hole as run_subagent: `agent_name` is model-supplied and passed straight to
    # run_session, so a code-only agent is refused here too (plan § 4.11, P4).
    refusal = _code_only_refusal(agent_name)
    if refusal:
        return refusal

    persona = current_persona()
    cfg = _load_routing()
    providers = cfg.get("providers", {})

    results = []
    for tier in models:
        provider_cfg = providers.get(tier, {})
        provider = provider_cfg.get("provider", "anthropic")
        model = provider_cfg.get("model")
        try:
            response = run_session(
                agent_name, user_input=message, persona=persona,
                provider=provider, model_override=model,
            )
            results.append(f"[{tier}]\n{response}")
        except Exception as e:
            results.append(f"[{tier}]\nError: {e}")

    return "\n\n---\n\n".join(results)


RUN_MODEL_CONFERENCE_SCHEMA = {
    "name": "run_model_conference",
    "description": (
        "Query the same message across multiple model tiers and return all responses for synthesis. "
        "Use for high-stakes decisions, complex analysis, or when a single model's perspective is insufficient. "
        "The Coordinator or specialist receives all responses and synthesizes them — the user sees only the final integrated reply."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The question or task to put to all models.",
            },
            "models": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["cloud_fast", "cloud_deep", "cloud_analytical"],
                },
                "description": (
                    "List of model tiers to query. "
                    "'cloud_fast' = Gemini Flash (quick, cheap). "
                    "'cloud_deep' = Sonnet (nuanced, balanced). "
                    "'cloud_analytical' = o3 (deep reasoning, higher cost). "
                    "Typically use two tiers; rarely all three."
                ),
            },
            "agent_name": {
                "type": "string",
                "description": "Agent instruction file to use for all model calls. Defaults to 'coordinator'. Use a specialist name to run a specialist across multiple models.",
            },
        },
        "required": ["message", "models"],
    },
}


RUN_SUBAGENT_SCHEMA = {
    "name": "run_subagent",
    "description": (
        "Spawn a specialist agent and return its response. "
        "Use this to consult a specialist — Mental Wellbeing, Physical Health, "
        "Work & Vocation, Relationships, Learning & Growth, Recreation & Hobbies, "
        "Finance, Research Agent, or Logistics. "
        "Pass a contextualized directive (user message + relevant context) as the message."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "description": (
                    "Name of the specialist agent to call. Must match a file in config/agents/. "
                    "Options: mental_wellbeing, physical_health, "
                    "work_vocation, relationships, learning_growth, recreation_hobbies, "
                    "finance, research_agent, logistics"
                ),
            },
            "message": {
                "type": "string",
                "description": "The message to pass to the specialist. Usually the user's input, optionally with brief context.",
            },
            "complexity": {
                "type": "string",
                "enum": ["quick", "deep"],
                "description": (
                    "Model tier hint. 'quick' uses the fast model (good for logging, lookups, simple tasks). "
                    "'deep' uses the agent's full-power model (for synthesis, analysis, nuanced judgment). "
                    "Omit to use the agent's default routing."
                ),
            },
            "fire_and_forget": {
                "type": "boolean",
                "description": (
                    "When true, dispatch the agent in the background and return immediately. "
                    "Reserved for write-only agents whose output is never needed in the response. "
                    "Do not use for any specialist whose output must inform the reply."
                ),
            },
        },
        "required": ["agent_name", "message"],
    },
}
