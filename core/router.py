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
_ROUTING_CONFIG = _ROOT / "config" / "modules" / (
    "routing_cloud.yaml" if os.environ.get("DEPLOYMENT_MODE") == "cloud" else "routing.yaml"
)
_ROUTING_ERROR_LOG = _ROOT / "data" / "logs" / "routing_fallbacks.json"


@dataclass
class ModelConfig:
    provider: str           # "anthropic" | "openai" | "ollama" | "gemini"
    model: str | None       # None means use the provider's default
    base_url: str | None    # None means use the provider's default


def _load_routing() -> dict:
    if _ROUTING_CONFIG.exists():
        with open(_ROUTING_CONFIG) as f:
            return yaml.safe_load(f) or {}
    return {}


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

    # Sensitive agents always route local — complexity cannot override this.
    if agent_cfg.get("local"):
        if local_enabled:
            cfg_out = ModelConfig(
                provider="ollama",
                model=local_cfg.get("model", "qwen3:14b"),
                base_url=local_cfg.get("endpoint", "http://localhost:11434/v1"),
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
        )
        _trace(f"[ROUTE] {agent} → {cfg_out.provider}/{cfg_out.model}  (quick_override)")
        return cfg_out

    # Direct cloud model assignment.
    cfg_out = ModelConfig(
        provider=agent_cfg.get("provider", "anthropic"),
        model=agent_cfg.get("model"),
        base_url=None,
    )
    _trace(f"[ROUTE] {agent} → {cfg_out.provider}/{cfg_out.model}")
    return cfg_out


def _log_routing_error(agent: str) -> None:
    """Record a sensitive-agent routing failure for auditability."""
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
        "error": "local_enabled: false — sensitive agent refused cloud routing",
    })
    with open(_ROUTING_ERROR_LOG, "w") as f:
        json.dump(entries, f, indent=2)
