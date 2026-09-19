"""
core/router.py — model routing layer.

Each agent in routing.yaml specifies its preferred model directly.
Sensitive agents (local: true) route to Ollama only — fail-closed.
Ollama unavailable (local_enabled: false) → RuntimeError, never a cloud call.

complexity="quick" does NOT override local: true agents. Sensitivity beats speed.
quick_override applies only to non-sensitive (cloud) agents.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Trace helper — set AI_TRACE=1 to enable; off by default
# ---------------------------------------------------------------------------

def _trace(msg: str) -> None:
    if not os.environ.get("AI_TRACE"):
        return
    from datetime import datetime as _dt
    ts = _dt.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)

_ROOT = Path(__file__).parent.parent
# Daemon-level diagnostics, deliberately NOT per-persona: these record routing
# and provider failures for the process as a whole. Kept out of data/logs/ so
# infrastructure diagnostics are never mixed in with a persona's user data.
_ROUTING_ERROR_LOG = _ROOT / "data" / "diagnostics" / "routing_fallbacks.json"
_MODEL_ERROR_LOG = _ROOT / "data" / "diagnostics" / "model_errors.json"


def _routing_config_path() -> Path:
    mode = os.environ.get("DEPLOYMENT_MODE", "local")
    name = "routing_cloud.yaml" if mode == "cloud" else "routing.yaml"
    return _ROOT / "config" / "modules" / name


@dataclass
class ModelConfig:
    provider: str                    # "anthropic" | "openai" | "ollama" | "gemini"
    model: str | None                # None means use the provider's default
    base_url: str | None             # None means use the provider's default
    allowed_tools: list[str] | None = None  # schema whitelist; None = all tools


def _load_routing() -> dict:
    """
    The routing config for this deployment mode, with Build's overlay merged in.

    SEAM 2 of Build's four load seams, and the only Red-tier one. resolve_model()
    and get_allowed_tools() below need no change at all: they read the merged
    dict, and a generated capability is an ordinary entry in it by the time they
    see it.
    """
    path = _routing_config_path()
    cfg: dict = {}
    if path.exists():
        with open(path) as f:
            cfg = yaml.safe_load(f) or {}
    return _merge_overlay_routing(cfg)


def _merge_overlay_routing(cfg: dict) -> dict:
    """
    Add Build's generated capabilities to the agent table. TRACKED ALWAYS WINS.

    Three properties, each load-bearing:

    1. **A tracked name is never overridden.** The writer refuses a colliding
       name up front; this is the second line, and it holds even if a record
       reached the overlay some other way.

    2. **`model_ref` is resolved HERE, at load time, to the named tracked
       agent's live model.** A generated record must not pin a model id: ids
       have a short half-life in this project — the reasoning tier moved twice
       in four days in September 2026 — and a record pinning one would strand
       its capability on a retired id with nobody editing it. A ref that does
       not resolve is SKIPPED rather than registered half-built, so the failure
       is the existing, understood "no entry in the routing config" raise rather
       than a silent route to a model that does not exist.

    3. **It fails open to "no overlay".** Any failure returns the tracked config
       unchanged. This function sits on the path that routes EVERY agent,
       tracked ones included, so a broken overlay record must not be able to
       take a tracked session down. Build's fail-closed half is the writer and
       core/build/verify.py, where refusing costs nothing.
    """
    mode = os.environ.get("DEPLOYMENT_MODE", "local")
    try:
        from core.build.overlay import routing_entries
        entries = routing_entries(mode)
    except Exception as exc:
        _trace(f"[ROUTE] overlay unavailable, tracked routing only: {exc}")
        return cfg
    if not entries:
        return cfg

    agents = dict(cfg.get("agents") or {})
    for name, entry in entries.items():
        if name in agents:
            _trace(f"[ROUTE] overlay entry {name!r} ignored — a tracked agent owns that name")
            continue
        merged = dict(entry)
        ref = merged.pop("model_ref", None)
        if ref:
            tracked = agents.get(str(ref))
            if not isinstance(tracked, dict) or not tracked.get("model"):
                _trace(f"[ROUTE] overlay entry {name!r} skipped — model_ref "
                       f"{ref!r} resolves to no tracked model")
                continue
            # BOTH halves come from the tracked agent, and the record's own
            # provider is DISCARDED rather than deferred to.
            #
            # `setdefault` was the defect: the record always carried a provider,
            # so it always won, and `model_ref` only ever governed the model. A
            # record could therefore name a sensible tracked agent for its model
            # and still route itself to an entirely different vendor, with every
            # individual field reading correctly. The schema now refuses a record
            # that sets a provider at all; this is the half that holds even if
            # one reaches the overlay by another route.
            merged.pop("provider", None)
            merged["model"] = tracked["model"]
            merged["provider"] = tracked.get("provider", "gemini")
        agents[name] = merged

    out = dict(cfg)
    out["agents"] = agents
    return out


def resolve_model(agent: str, complexity: str | None = None) -> ModelConfig:
    """
    Resolve the provider and model for a given agent session.

    Resolution order:
    1. Agent has local: true → Ollama always, regardless of complexity.
       If local_enabled is false, logs the error and raises RuntimeError (fail-closed).
    2. complexity="quick" and agent is non-sensitive → quick_override model.
    3. Otherwise → agent's direct provider/model.
    """
    cfg = _load_routing()
    local_enabled: bool = cfg.get("local_enabled", False)
    local_cfg: dict = cfg.get("local", {})
    agent_cfg: dict = cfg.get("agents", {}).get(agent, {})

    allowed_tools: list[str] | None = agent_cfg.get("allowed_tools")  # None=allow all; []=allow none

    # Sensitive agents always route local — complexity cannot override this.
    if agent_cfg.get("local"):
        if local_enabled:
            cfg_out = ModelConfig(
                provider="ollama",
                model=local_cfg.get("model", "qwen3:14b"),
                base_url=local_cfg.get("endpoint", "http://localhost:11434/v1"),
                allowed_tools=allowed_tools,
            )
            _trace(f"[ROUTE] {agent} → ollama/{cfg_out.model}  (sensitive, local)")
            return cfg_out
        _log_routing_error(agent)
        raise RuntimeError(
            f"Agent '{agent}' is sensitive (local: true) and Ollama is not available "
            f"(local_enabled: false). Refusing to route to a cloud provider. "
            f"Start Ollama and ensure local_enabled is true in routing.yaml."
        )

    # Non-sensitive agents: complexity="quick" routes to the fast cloud model.
    if complexity == "quick":
        quick = cfg.get("quick_override", {})
        cfg_out = ModelConfig(
            provider=quick.get("provider", "gemini"),
            model=quick.get("model"),
            base_url=None,
            allowed_tools=allowed_tools,
        )
        _trace(f"[ROUTE] {agent} → {cfg_out.provider}/{cfg_out.model}  (quick_override)")
        return cfg_out

    # Direct cloud model assignment.
    if not agent_cfg:
        _log_routing_error(agent, reason="unknown agent — not listed in routing config")
        raise RuntimeError(
            f"Agent '{agent}' has no entry in the routing config. "
            f"Add it to config/modules/routing_cloud.yaml (or routing.yaml for local mode)."
        )
    cfg_out = ModelConfig(
        provider=agent_cfg.get("provider", "gemini"),
        model=agent_cfg.get("model"),
        base_url=None,
        allowed_tools=allowed_tools,
    )
    _trace(f"[ROUTE] {agent} → {cfg_out.provider}/{cfg_out.model}")
    return cfg_out


def get_allowed_tools(agent: str) -> list[str] | None:
    """Return the tool schema whitelist for an agent, or None if no whitelist is set."""
    cfg = _load_routing()
    agent_cfg = cfg.get("agents", {}).get(agent, {})
    return agent_cfg.get("allowed_tools")  # None=allow all; []=allow none


def _log_routing_error(agent: str, reason: str = "local_enabled: false — sensitive agent refused cloud routing") -> None:
    """Record a routing failure for auditability."""
    _ROUTING_ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    entries: list = []
    if _ROUTING_ERROR_LOG.exists():
        try:
            with open(_ROUTING_ERROR_LOG) as f:
                entries = json.load(f)
        except Exception:
            pass
    entries.append({
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "error": reason,
    })
    with open(_ROUTING_ERROR_LOG, "w") as f:
        json.dump(entries, f, indent=2)


def log_model_error(agent: str, provider: str, model: str | None, error: str) -> None:
    """Record a model API call failure. Called by orchestrator on any provider exception."""
    _MODEL_ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    entries: list = []
    if _MODEL_ERROR_LOG.exists():
        try:
            with open(_MODEL_ERROR_LOG) as f:
                entries = json.load(f)
        except Exception:
            pass
    entries.append({
        "timestamp": datetime.now().isoformat(),
        "agent": agent.agent if hasattr(agent, "agent") else agent,
        "provider": provider,
        "model": model,
        "error": error,
    })
    with open(_MODEL_ERROR_LOG, "w") as f:
        json.dump(entries, f, indent=2)
