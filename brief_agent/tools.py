"""Read-only research tools for the Research Brief Agent.

All tools are pure reads over public HTTP endpoints and need no API key:
Wikipedia's public API for search/summaries, plus a generic URL fetcher.
They are declared READ_ONLY + idempotent so OpenMinion's default action
policy runs them without an interactive confirmation.

Nothing here calls a model; the model is OpenMinion's configured provider.
"""

from __future__ import annotations

import html
import ipaddress
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from socket import timeout as SocketTimeout

from openminion import tool

_USER_AGENT = "ResearchBriefAgent/0.1 (Cortensor Hackathon #5; +https://github.com/anzdex)"
_MAX_CHARS = 4000
_HTTP_TIMEOUT_S = 15


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def _get_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:
        raw = resp.read().decode("utf-8", "replace")
    # Strip scripts/styles, then tags; keep readable text only.
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    text = html.unescape(re.sub(r"\s+", " ", raw)).strip()
    return text[:_MAX_CHARS]


def _is_public_host(host: str) -> bool:
    """Block localhost / private-network fetches (SSRF guard)."""
    host = host.lower().rstrip(".")
    if host in {"localhost", "ip6-localhost"}:
        return False
    try:
        return not ipaddress.ip_address(host).is_private
    except ValueError:
        return True  # a DNS name: resolve check happens at connect time


@tool(min_scope="READ_ONLY", idempotent=True)
def wikipedia_search(query: str) -> str:
    """Search Wikipedia for a topic. Returns matching article titles + snippets."""
    query = (query or "").strip()
    if not query:
        return "Empty query: pass a topic to search for."
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 5,
            "format": "json",
        }
    )
    try:
        data = _get_json(f"https://en.wikipedia.org/w/api.php?{params}")
    except (urllib.error.URLError, SocketTimeout, json.JSONDecodeError) as exc:
        return f"Wikipedia search failed: {exc}"
    results = data.get("query", {}).get("search", [])
    if not results:
        return f"No Wikipedia results for '{query}'."
    lines = []
    for item in results:
        snippet = html.unescape(re.sub(r"<[^>]+>", "", item.get("snippet", "")))
        lines.append(f"- {item.get('title', '')}: {snippet}")
    return "\n".join(lines)


@tool(min_scope="READ_ONLY", idempotent=True)
def wikipedia_fetch(title: str) -> str:
    """Fetch the summary of one Wikipedia article by exact title."""
    title = (title or "").strip()
    if not title:
        return "Empty title: pass an article title from wikipedia_search."
    path = urllib.parse.quote(title.replace(" ", "_"))
    try:
        data = _get_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{path}")
    except (urllib.error.URLError, SocketTimeout, json.JSONDecodeError) as exc:
        return f"Wikipedia fetch failed: {exc}"
    extract = data.get("extract", "")
    if not extract:
        return f"No summary found for '{title}'."
    return extract[:_MAX_CHARS]


@tool(min_scope="READ_ONLY", idempotent=True)
def fetch_url(url: str) -> str:
    """Fetch a public http(s) URL and return its readable text (first 4000 chars).

    Localhost and private-network hosts are refused.
    """
    url = (url or "").strip()
    if not url:
        return "Empty URL."
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return "Only public http(s) URLs are allowed."
    if not _is_public_host(parsed.hostname):
        return "Refused: localhost/private hosts are not allowed."
    try:
        return _get_text(url)
    except (urllib.error.URLError, SocketTimeout, ValueError) as exc:
        return f"Fetch failed for {url}: {exc}"
