"""Structured brief: parse the model's answer and render it as Markdown.

The agent is instructed to answer with exactly one JSON object. Parsing is
defensive: if the model wraps the JSON in prose or returns plain text, we
still produce a usable brief instead of crashing, and we say so in the
output (``parse_note``) so a bad parse is visible, not silently smoothed over.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

BRIEF_INSTRUCTIONS = """You are a research brief agent. Use your tools to gather
facts about the user's topic, then answer with EXACTLY ONE JSON object and
nothing else, using these keys:

{
  "summary": "2-3 sentences summarising the topic",
  "key_points": ["3-5 short factual points, each one sentence"],
  "sources": [{"title": "source title", "url": "source url"}],
  "next_steps": ["2-3 concrete follow-up questions or actions"]
}

Rules:
- Only state facts your tools returned; do not invent sources or URLs.
- If a tool returned nothing useful, say so in the summary instead of guessing.
- Keep every key_point to one sentence and grounded in a tool result.
"""


@dataclass
class Brief:
    topic: str
    summary: str
    key_points: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    raw_text: str = ""
    parse_note: str = ""


def _extract_json(text: str) -> dict | None:
    """Return the first {...} JSON object in text, or None."""
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def parse_brief(topic: str, text: str) -> Brief:
    obj = _extract_json(text)
    if obj is None:
        # Fallback: keep the model's words as the summary, no invented structure.
        summary = text.strip() or "(empty model reply)"
        return Brief(
            topic=topic,
            summary=summary,
            raw_text=text,
            parse_note="Model reply was not valid JSON; stored verbatim as the summary.",
        )
    summary = str(obj.get("summary") or "").strip() or "(no summary returned)"
    key_points = [str(p).strip() for p in obj.get("key_points") or [] if str(p).strip()]
    sources = [
        {"title": str(s.get("title", "")), "url": str(s.get("url", ""))}
        for s in (obj.get("sources") or [])
        if isinstance(s, dict)
    ]
    next_steps = [str(s).strip() for s in obj.get("next_steps") or [] if str(s).strip()]
    return Brief(
        topic=topic,
        summary=summary,
        key_points=key_points[:5],
        sources=sources[:6],
        next_steps=next_steps[:3],
        raw_text=text,
        parse_note="Parsed from the model's JSON reply.",
    )


def render_markdown(brief: Brief, *, provider: str, model: str, session_id: str) -> str:
    lines = [
        f"# Research Brief: {brief.topic}",
        "",
        f"_Provider: {provider} / {model} · OpenMinion session: {session_id}_",
        "",
        "## Summary",
        "",
        brief.summary,
        "",
    ]
    if brief.key_points:
        lines += ["## Key points", ""]
        lines += [f"- {point}" for point in brief.key_points]
        lines += [""]
    if brief.sources:
        lines += ["## Sources", ""]
        for src in brief.sources:
            title = src.get("title") or src.get("url") or "(untitled)"
            url = src.get("url") or ""
            lines.append(f"- [{title}]({url})" if url else f"- {title}")
        lines += [""]
    if brief.next_steps:
        lines += ["## Next steps", ""]
        lines += [f"- {step}" for step in brief.next_steps]
        lines += [""]
    lines += ["---", "", f"_Parse note: {brief.parse_note}_", ""]
    return "\n".join(lines)


def slugify(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return slug[:60] or "brief"
