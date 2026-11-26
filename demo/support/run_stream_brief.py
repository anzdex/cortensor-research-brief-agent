#!/usr/bin/env python3
"""Probe/live runner for the Research Brief Agent using Agent.run_stream.

Same Agent, tools, instructions and session as main.py (via
brief_agent.build_agent); only difference is run_stream's on_delta, which
prints progress events (tool calls, etc.) live instead of staying silent
until the run finishes. Used for the demo video so the tool calls are
visible on screen. Writes the same outputs/<slug>-brief.md as main.py.

Usage:
    OPENMINION_PROVIDER=ollama OPENMINION_MODEL=llama3.2:3b \
    OPENMINION_TURN_TIMEOUT=1800 .venv/bin/python /tmp/run_stream_brief.py "OpenMinion"
"""
import os
import re
import sys

PROJECT_ROOT = "/home/hatch/workspace/dorahacks/cortensor-5"
sys.path.insert(0, PROJECT_ROOT)

from pathlib import Path  # noqa: E402

from brief_agent.agent import build_agent  # noqa: E402
from brief_agent.brief import parse_brief, render_markdown, slugify  # noqa: E402


def _sanitize_no_proxy() -> None:
    """Same workaround as main.py: httpx (OpenMinion providers,
    trust_env=True) raises InvalidURL on bracketed IPv6 in no_proxy."""
    for var in ("no_proxy", "NO_PROXY"):
        value = os.environ.get(var)
        if not value:
            continue
        kept = [part for part in value.split(",") if not part.startswith("[")]
        for host in ("localhost", "127.0.0.1"):
            if host not in kept:
                kept.append(host)
        os.environ[var] = ",".join(kept)


_sanitize_no_proxy()

_LAST = {"line": None}


def show(delta):
    """Print one concise line per progress event; collapse repeats."""
    kind = type(delta).__name__
    text = " ".join(str(delta).split())
    label = re.search(r"label='([^']*)'", text)
    phase = re.search(r"source_phase='([^']*)'", text)
    if kind == "PhaseStatus" and label:
        line = f"[phase] {label.group(1)}" + (f" ({phase.group(1)})" if phase else "")
    else:
        if len(text) > 220:
            text = text[:220] + "..."
        line = f"[delta] {kind}: {text}"
    if line == _LAST["line"]:
        return
    _LAST["line"] = line
    print(line, flush=True)


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "OpenMinion"
    provider = os.environ.get("OPENMINION_PROVIDER", "ollama")
    model = os.environ.get("OPENMINION_MODEL", "llama3.2:3b")
    timeout = float(os.environ.get("OPENMINION_TURN_TIMEOUT", "1800"))
    print(f"[brief-agent] provider={provider} model={model} topic={topic!r} (run_stream)", flush=True)
    with build_agent(topic, provider, model) as agent:
        result = agent.run_stream(
            f"Research this topic and produce the brief: {topic}",
            timeout_seconds=timeout,
            on_delta=show,
        )
    brief = parse_brief(topic, result.text)
    out_path = Path(PROJECT_ROOT) / "outputs" / f"{slugify(topic)}-brief.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = render_markdown(
        brief, provider=provider, model=model, session_id=result.session_id
    )
    out_path.write_text(markdown)
    print(f"[brief-agent] wrote {out_path}", flush=True)
    print(f"[brief-agent] session={result.session_id} run_id={result.run_id}", flush=True)
    if getattr(result, "stats", None):
        print(f"[brief-agent] stats={dict(result.stats)}", flush=True)
    print(flush=True)
    print(markdown, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
