# Demo video script — Research Brief Agent (1–5 minutes)

Target length: ~3 minutes. Record the terminal + the generated brief file.
No mock output: every model reply on screen comes from a live OpenMinion
run against the configured provider. **Provider choice matters for the
demo:** the recorded Ollama run (`llama3.2:1b`, see
`outputs/cortensor-brief.md`) is real but the 1B model made zero tool
calls and hallucinated facts — do not read its summary aloud as if it
were correct. Record the video against a hosted provider
(`OPENMINION_PROVIDER=openai` or `cortensor-portal`) so the demo shows
real tool use and a correct brief; the Ollama path stays as the
documented no-key fallback.

## 0:00–0:20 — What this is
- "This is the Research Brief Agent, built with the OpenMinion 0.1 Python
  SDK for Cortensor Hackathon #5."
- Show the repo: `main.py`, `brief_agent/agent.py`, `brief_agent/tools.py`.
- "One workflow: give it a topic, it researches with tools and writes a
  structured brief — summary, key points, sources, next steps."

## 0:20–0:50 — The OpenMinion part (show, don't just say)
- Show `brief_agent/agent.py`: `Agent(instructions=..., tools=[...])`,
  `agent.run(...)` — the real 0.1 API from the SDK README/quickstart.
- Show the three tools in `brief_agent/tools.py`: `wikipedia_search`,
  `wikipedia_fetch`, `fetch_url` — all `@tool(min_scope="READ_ONLY",
  idempotent=True)`.
- Show `openminion setup --list-providers` output (Ollama, no key) and
  the project config at `.openminion-home/.openminion/agents.json`
  (provider `ollama`, model `llama3.2:1b`).

## 0:50–2:00 — The live run
- Run in the terminal (do not pre-record the output):
  ```
  ./run.sh "Cortensor"        # with OPENMINION_PROVIDER=openai (or cortensor-portal)
  ```
- Narrate as it runs: the model calls `wikipedia_search`, then
  `wikipedia_fetch`, then composes the JSON brief. Point at the tool-call
  lines in the terminal output. (On the 1B Ollama path the model made
  zero tool calls — that is why the demo uses a hosted provider.)
- Open `outputs/cortensor-brief.md` and read the summary + one key point
  aloud. This file is the real output of this run.

## 2:00–2:40 — Repeatability
- Run it again with a different topic:
  ```
  ./run.sh "OpenMinion"
  ```
- Same workflow, new session (`research-brief-openminion`), new brief.
- Mention the session is durable: OpenMinion stores it in the local
  SQLite state under `.openminion-home/`.

## 2:40–3:00 — What was tested, what was rough
- Tested: `Agent` + `@tool` + sessions (worked), Ollama provider
  (worked, local model, no key), `openminion setup --list-providers`
  (worked).
- Rough edges (see README "Building Blocks Tested" for the honest list):
  the Ollama install script needs `zstd`, which was not installed;
  `ollama pull` hung on the manifest (blobs fetched with curl instead);
  httpx chokes on bracketed IPv6 in `no_proxy` (sanitized in `run.sh`);
  the SDK's 90 s default turn timeout is too short for a cold 1B CPU
  model (raised to 600 s); and the 1B model made zero tool calls and
  hallucinated facts in the recorded runs — use a hosted provider for
  the demo.
- Close: "Repo link in the submission. The PR step waits on the official
  Hackathon #5 repo URL from Discord/docs."
