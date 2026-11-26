"""Unit tests for brief parsing/rendering — no model call needed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brief_agent.brief import parse_brief, render_markdown, slugify


def test_parse_valid_json():
    text = """Here is the brief:
{"summary": "X is Y.", "key_points": ["P1.", "P2."],
 "sources": [{"title": "T", "url": "https://example.com"}],
 "next_steps": ["Do Z."]}"""
    brief = parse_brief("X", text)
    assert brief.summary == "X is Y."
    assert brief.key_points == ["P1.", "P2."]
    assert brief.sources == [{"title": "T", "url": "https://example.com"}]
    assert brief.next_steps == ["Do Z."]
    assert "Parsed" in brief.parse_note


def test_parse_plain_text_falls_back_verbatim():
    brief = parse_brief("X", "Just some words, no JSON here.")
    assert brief.summary == "Just some words, no JSON here."
    assert brief.key_points == []
    assert "not valid JSON" in brief.parse_note


def test_parse_empty_reply():
    brief = parse_brief("X", "")
    assert brief.summary == "(empty model reply)"


def test_render_markdown_contains_sections():
    brief = parse_brief(
        "X",
        '{"summary": "S.", "key_points": ["P."], '
        '"sources": [{"title": "T", "url": "https://example.com"}], '
        '"next_steps": ["N."]}',
    )
    md = render_markdown(brief, provider="ollama", model="llama3.2:1b",
                         session_id="research-brief-x")
    for heading in ("# Research Brief: X", "## Summary", "## Key points",
                    "## Sources", "## Next steps"):
        assert heading in md
    assert "ollama / llama3.2:1b" in md


def test_slugify():
    assert slugify("Cortensor & OpenMinion 101!") == "cortensor-openminion-101"
    assert slugify("   ") == "brief"
