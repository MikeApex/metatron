"""
tools/subagent.py — run a specialist sub-agent session and return its output.

Used by the Coordinator to fan out to specialists. Each call spawns a
full run_session() with the named agent's instruction file and the shared
data context. Persona (AI_TEST_PERSONA env var) is passed through automatically.
"""

import logging
import os
import threading

logger = logging.getLogger(__name__)


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

    The current persona (if any) is inherited from the environment so specialist
    sessions see the same config context as the Coordinator session.
    """
    from core.orchestrator import run_session

    # Recursion guard: specialists must not spawn further subagents.
    # Only the Coordinator (depth 0) may call run_subagent.
    depth = int(os.environ.get("_SUBAGENT_DEPTH", "0"))
    if depth >= 1:
        return (
            f"Error: run_subagent cannot be called from within a specialist session. "
            f"Only the Coordinator may spawn subagents. "
            f"Perform this task directly without delegating."
        )

    persona = os.environ.get("AI_TEST_PERSONA") or None
    complexity_hint = complexity if complexity in ("quick", "deep") else None

    # Diarist is always write-only — enforce fire_and_forget at the code layer
    # regardless of what the coordinator model passes.
    if agent_name == "diarist":
        fire_and_forget = True

    if fire_and_forget:
        # Capture env vars needed by the background thread before returning.
        subagent_env = os.environ.get("_SUBAGENT_DEPTH", "0")
        def _run() -> None:
            os.environ["_SUBAGENT_DEPTH"] = str(int(subagent_env) + 1)
            try:
                run_session(agent_name, user_input=message, persona=persona,
                            complexity=complexity_hint)
            except Exception as e:
                logger.warning(f"[fire_and_forget] {agent_name} failed: {e}")
            finally:
                os.environ["_SUBAGENT_DEPTH"] = subagent_env
        threading.Thread(target=_run, daemon=True).start()
        return f"{agent_name}: dispatched (async)"

    os.environ["_SUBAGENT_DEPTH"] = str(depth + 1)
    try:
        return run_session(agent_name, user_input=message, persona=persona,
                           complexity=complexity_hint)
    finally:
        os.environ["_SUBAGENT_DEPTH"] = str(depth)


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

    persona = os.environ.get("AI_TEST_PERSONA") or None
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
