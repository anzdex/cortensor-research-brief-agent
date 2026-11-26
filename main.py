#!/usr/bin/env python3
"""Research Brief Agent — CLI entry point.

Usage:
    python main.py "Cortensor" [--out outputs/brief.md] [--json]
    OPENMINION_PROVIDER=openai OPENMINION_MODEL=gpt-4.1-mini python main.py "Topic"

The model call goes through OpenMinion's configured provider. With the
default provider (ollama) no API key is needed — run `ollama pull
llama3.2:1b` first. With a hosted provider, set its key in the environment
(see .env.example); keys are never read from files in this repo.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def _sanitize_no_proxy() -> None:
    """Drop bracketed IPv6 literals (e.g. ``[::1]``) from no_proxy/NO_PROXY.

    OpenMinion's providers use httpx with ``trust_env=True``, and httpx
    raises ``InvalidURL: Invalid port: ':1]'`` on bracketed IPv6 entries in
    no_proxy. Bare IPv6 forms (``::1``) parse fine, and localhost routing is
    unaffected. Only this process's environment is touched, so the
    local Ollama server is reached directly instead of through the proxy.
    """
    for var in ("no_proxy", "NO_PROXY"):
        value = os.environ.get(var)
        if not value:
            continue
        kept = [part for part in value.split(",") if not part.startswith("[")]
        for host in ("localhost", "127.0.0.1"):
            if host not in kept:
                kept.append(host)
        os.environ[var] = ",".join(kept)


from brief_agent.agent import resolve_provider, run_brief  # noqa: E402
from brief_agent.brief import render_markdown, slugify  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    _sanitize_no_proxy()
    parser = argparse.ArgumentParser(description="Research Brief Agent (OpenMinion 0.1)")
    parser.add_argument("topic", help="Topic to research")
    parser.add_argument(
        "--out",
        default=None,
        help="Markdown output path (default: outputs/<slug>-brief.md)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also print the parsed brief as JSON on stdout",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Override OPENMINION_PROVIDER for this run",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override OPENMINION_MODEL for this run",
    )
    args = parser.parse_args(argv)

    if args.provider:
        os.environ["OPENMINION_PROVIDER"] = args.provider
    if args.model:
        os.environ["OPENMINION_MODEL"] = args.model

    provider, model = resolve_provider()
    print(f"[brief-agent] provider={provider} model={model} topic={args.topic!r}")
    try:
        run = run_brief(args.topic, provider, model)
    except (ValueError, RuntimeError) as exc:
        print(f"[brief-agent] ERROR: {exc}", file=sys.stderr)
        return 1

    brief = run["brief"]
    out_path = Path(args.out) if args.out else (
        PROJECT_ROOT / "outputs" / f"{slugify(args.topic)}-brief.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = render_markdown(
        brief, provider=provider, model=model, session_id=run["session_id"]
    )
    out_path.write_text(markdown)
    print(f"[brief-agent] wrote {out_path}")
    print(f"[brief-agent] session={run['session_id']} run_id={run['run_id']}")
    if run["stats"]:
        print(f"[brief-agent] stats={run['stats']}")
    print()
    print(markdown)
    if args.json:
        print(json.dumps({
            "topic": brief.topic,
            "summary": brief.summary,
            "key_points": brief.key_points,
            "sources": brief.sources,
            "next_steps": brief.next_steps,
            "provider": provider,
            "model": model,
            "session_id": run["session_id"],
            "run_id": run["run_id"],
        }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
