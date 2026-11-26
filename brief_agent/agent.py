"""OpenMinion wiring for the Research Brief Agent.

The agent itself is OpenMinion's ``Agent`` (0.1 API, verified against
openminion 0.1.24): instructions + three read-only tools + a durable
session. Provider/model come from the environment so the same code runs
against local Ollama, a hosted provider, or Cortensor Portal — the model
call is always the configured provider, never a hard-coded reply.

Config handling (documented OpenMinion behaviour):
- The runtime config lives at ``.openminion-home/.openminion/agents.json``
  (project-scoped, git-ignored). It is created once with the documented
  ``openminion config init --provider <provider>`` command.
- ``ensure_config`` then patches only two documented fields for the active
  provider: ``providers.<id>.model`` and ``providers.<id>.timeout_seconds``,
  plus ``agents.openminion.provider``. Credentials are never written here;
  OpenMinion reads them from the environment (e.g. ``OPENAI_API_KEY``).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from openminion import Agent, ProviderError, TurnTimeoutError

from .brief import BRIEF_INSTRUCTIONS, parse_brief, slugify
from .tools import fetch_url, wikipedia_fetch, wikipedia_search

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / ".openminion-home" / ".openminion" / "agents.json"

DEFAULT_MODELS = {
    "ollama": "llama3.2:1b",
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-sonnet-5",
    "openrouter": "openai/gpt-4.1-mini",
    "cortensor-portal": "oss-20b",
    "cortensor-router": "gpt-oss-20b",
    "groq": "llama-3.3-70b-versatile",
    "cerebras": "gpt-oss-120b",
    "minimax": "MiniMax-M3.1-Flash",
    "deepseek": "deepseek-v4-flash",
    "gemini": "gemini-3.6-flash",
}

# A 1B local model on CPU needs longer than the 60 s provider default.
PROVIDER_TIMEOUT_S = 300
# Turn budget for one full brief run (several model round-trips: tool calls
# + final JSON). The SDK default is 90 s, which a cold 1B CPU model cannot
# meet; 600 s is generous but bounded. Override with OPENMINION_TURN_TIMEOUT.
TURN_TIMEOUT_S = float(os.environ.get("OPENMINION_TURN_TIMEOUT", "600"))


def resolve_provider() -> tuple[str, str]:
    provider = os.environ.get("OPENMINION_PROVIDER", "ollama").strip() or "ollama"
    model = os.environ.get("OPENMINION_MODEL", "").strip()
    if not model:
        model = DEFAULT_MODELS.get(provider, "")
    if not model:
        raise ValueError(
            f"No default model known for provider '{provider}'. "
            "Set OPENMINION_MODEL explicitly."
        )
    return provider, model


def _run_config_init(provider: str) -> None:
    """Create the project config the documented way (no hand-rolled JSON)."""
    env = dict(os.environ)
    env["OPENMINION_HOME"] = str(PROJECT_ROOT / ".openminion-home")
    cmd = [sys.executable, "-m", "openminion", "config", "init",
           "--provider", provider, "--force"]
    # Prefer the `openminion` console script when it exists on PATH.
    from shutil import which

    binary = which("openminion")
    if binary:
        cmd = [binary, "config", "init", "--provider", provider, "--force"]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "openminion config init failed:\n"
            f"{result.stdout}\n{result.stderr}"
        )


def ensure_config(provider: str, model: str) -> Path:
    """Make sure the project config exists and points at provider/model."""
    if not CONFIG_PATH.exists():
        _run_config_init(provider)
    data = json.loads(CONFIG_PATH.read_text())
    agents = data.setdefault("agents", {})
    profile = agents.setdefault("openminion", {})
    profile["provider"] = provider
    providers = data.setdefault("providers", {})
    if provider not in providers:
        raise ValueError(
            f"Provider '{provider}' has no block in {CONFIG_PATH}. "
            "Add it with `openminion setup --provider "
            f"{provider} --no-focus` or edit the config."
        )
    providers[provider]["model"] = model
    providers[provider]["timeout_seconds"] = PROVIDER_TIMEOUT_S
    CONFIG_PATH.write_text(json.dumps(data, indent=2))
    return CONFIG_PATH


def build_agent(topic: str, provider: str, model: str) -> Agent:
    """Construct the OpenMinion Agent for one brief run."""
    config_path = ensure_config(provider, model)
    return Agent(
        instructions=BRIEF_INSTRUCTIONS,
        tools=[wikipedia_search, wikipedia_fetch, fetch_url],
        config_path=str(config_path),
        agent_id="openminion",
        model=model,
        session_id=f"research-brief-{slugify(topic)}",
    )


def run_brief(topic: str, provider: str, model: str) -> dict:
    """Run one model-backed brief. Returns the brief + run metadata."""
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("Topic must not be empty.")
    with build_agent(topic, provider, model) as agent:
        try:
            result = agent.run(
                f"Research this topic and produce the brief: {topic}",
                timeout_seconds=TURN_TIMEOUT_S,
            )
        except TurnTimeoutError as exc:
            raise RuntimeError(
                f"OpenMinion turn timed out after the configured budget: {exc}"
            ) from exc
        except ProviderError as exc:
            raise RuntimeError(
                f"Provider '{provider}' ({model}) failed: "
                f"[{exc.code}] {exc.message}"
            ) from exc
    brief = parse_brief(topic, result.text)
    return {
        "brief": brief,
        "provider": provider,
        "model": model,
        "session_id": result.session_id or f"research-brief-{slugify(topic)}",
        "run_id": result.run_id,
        "stats": dict(result.stats or {}),
        "raw_text": result.text,
    }
