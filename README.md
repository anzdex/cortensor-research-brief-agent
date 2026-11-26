# Research Brief Agent — Cortensor Hackathon #5

A small, working agent built with the **OpenMinion 0.1 Python SDK**
(tested with `openminion 0.1.24`). Give it a topic; it researches with
tools and writes a short structured brief — summary, key points, sources,
next steps. One useful, repeatable workflow; no frontend, no mock output.

- **DoraHacks:** [Cortensor Hackathon #5](https://dorahacks.io/hackathon/2418/detail)
  — registered as `rajonjr` (GitHub `@anzdex`)
- **Deadline:** 19 Dec 2026 14:59 WIB (DoraHacks). The Cortensor docs say
  the build period ends 18 Dec Pacific Time, so treat **18 Dec PT** as the
  safe target.
- **Prize pool:** $1,150 in $COR (per the DoraHacks listing; the
  [Hackathon #5 docs](https://docs.cortensor.network/community-and-ecosystem/hackathon/hackathon-5)
  list a different tier split for the same $1,150 total — DoraHacks is the
  submission authority, so its listing is the one to trust at submit time).

## What it does

```
$ ./run.sh "Cortensor"
[brief-agent] provider=ollama model=llama3.2:1b topic='Cortensor'
[brief-agent] wrote outputs/cortensor-brief.md
```

The agent (OpenMinion `Agent`, instructions + tools + durable session)
researches the topic and composes the brief as one JSON object that
`brief_agent/brief.py` parses and renders to Markdown. See
[`outputs/cortensor-brief.md`](outputs/cortensor-brief.md) for a real run.

> Honest note: in the two recorded runs the 1B local model made **zero
> tool calls** — it answered from its own knowledge instead of using the
> Wikipedia tools (see "Real runs" below). The tools themselves are
> verified working (called directly), and the agent wiring is real, but
> a small model that will not call tools produces thin, sometimes wrong
> briefs. Run against a hosted provider for a demo-quality brief.

## How to run

```bash
# Push this folder to a new public GitHub repo first, then:
git clone https://github.com/anzdex/<your-repo-name>.git
cd <your-repo-name>
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Local model path (no API key needed)
ollama serve          # in another terminal
ollama pull llama3.2:1b
./run.sh "Your topic"
```

Or run the pieces directly:

```bash
.venv/bin/python main.py "Your topic" [--out outputs/x.md] [--json]
.venv/bin/python -m pytest tests/ -q   # unit tests, no model call
```

## Real runs (evidence)

Both runs are real OpenMinion turns against local Ollama
(`llama3.2:1b`, Q8_0, 1.2B params), 25 Nov 2026, this VM. Nothing below
is hand-written — the outputs are the model replies, verbatim.

### Run 1 — "Cortensor" ([`outputs/cortensor-brief.md`](outputs/cortensor-brief.md))

- session `research-brief-cortensor`, run_id `8eb35be4adae4e409507e6732aa28bf8`
- stats: `input_tokens 3977, output_tokens 571, llm_calls 3,
  tool_calls 0, tool_errors 0, duration_ms 221213` (~3.7 min)
- The model returned valid JSON, so the brief parsed cleanly
  ("Parsed from the model's JSON reply"). **But the content is wrong:**
  it claims Cortensor is "a machine learning model developed by
  OpenMinedition" and cites an invented URL
  (`https://openminion.com/cortensor-model`). The 1B model hallucinated
  instead of using the Wikipedia tools. This output is kept as-is on
  purpose — it is the honest record of what the small local model does.

### Run 2 — "OpenMinion" ([`outputs/openminion-brief.md`](outputs/openminion-brief.md))

- session `research-brief-openminion`, run_id `9de961880ef24eb4bb846a6230ddebb9`
- stats: `input_tokens 3962, output_tokens 481, llm_calls 3,
  tool_calls 0, tool_errors 0, duration_ms 155064` (~2.6 min)
- The model declined ("I don't have enough information…") and did not
  return JSON, so the verbatim fallback fired and the reply was stored
  as the summary ("Model reply was not valid JSON; stored verbatim as
  the summary"). The fallback works as designed — a weak model degrades
  visibly, not silently.

### Other providers

```bash
cp .env.example .env   # fill in ONLY the key for your provider
OPENMINION_PROVIDER=openai OPENMINION_MODEL=gpt-4.1-mini ./run.sh "Topic"
OPENMINION_PROVIDER=cortensor-portal ./run.sh "Topic"   # needs CORTENSOR_API_KEY
```

Provider/model defaults (from `openminion setup --list-providers --json`,
verified 25 Nov 2026): `ollama → llama3.2:1b`, `openai → gpt-4.1-mini`,
`cortensor-portal → oss-20b`. Keys are read from the environment only;
never paste one into code or commit `.env`.

## How the OpenMinion SDK is used

- `Agent` — `brief_agent/agent.py:build_agent()` constructs
  `openminion.Agent(instructions=..., tools=[...], config_path=...,
  agent_id="openminion", model=..., session_id="research-brief-<slug>")`
  and calls `agent.run(prompt, timeout_seconds=600)`. This is the
  documented 0.1 API from the SDK README and
  `examples/starter/quickstart.py` (the timeout is a documented
  `Agent.run()` parameter; the 600 s value is ours, see bugs).
- `@tool` — three tools in `brief_agent/tools.py`, all declared
  `min_scope="READ_ONLY", idempotent=True`, so the default action policy
  runs them without an interactive confirmation:
  - `wikipedia_search(query)` — Wikipedia public API, top 5 matches.
  - `wikipedia_fetch(title)` — Wikipedia summary for one article.
  - `fetch_url(url)` — public http(s) fetch, HTML stripped, 4,000-char cap,
    localhost/private hosts refused.
- **Sessions** — each topic gets a durable session
  (`research-brief-<slug>`) stored in OpenMinion's local SQLite state
  under `.openminion-home/` (git-ignored).
- **Config** — project-scoped config at
  `.openminion-home/.openminion/agents.json`, created with the documented
  `openminion config init --provider ollama`; `main.py` only patches the
  documented `providers.<id>.model` / `.timeout_seconds` fields from env.
  A minimal template is in `config/agents.example.json`.
- **Diagnostics** — `openminion setup --list-providers --json` and
  `openminion status readiness` were used during development.

## Building Blocks Tested

| Building block | Used? | Result |
|---|---|---|
| `Agent` + `agent.run()` (Python API) | Yes | Works. One turn, JSON brief returned (run 1); `agent.run()` is called with an explicit `timeout_seconds=600` because the SDK default of 90 s is too short for a cold 1B CPU model (see bugs). |
| `@tool` with `READ_ONLY` / `idempotent` | Yes (tools verified by direct calls) | Tools work when called directly (`wikipedia_search`/`wikipedia_fetch` returned real Wikipedia data). **But in both recorded agent runs the model made 0 tool calls**, so the through-agent tool path — including the default action policy's no-confirmation behaviour for read-only tools — is still untested end-to-end. |
| Ollama provider (local model, no key) | Yes | Works, with two environment workarounds (see bugs): httpx chokes on bracketed IPv6 in `no_proxy`, and `ollama pull` hung on the manifest — both fixed without touching the SDK. `llama3.2:1b` via `http://127.0.0.1:11434`. |
| Sessions (durable, per-topic) | Yes | Works. Session ids `research-brief-<slug>` persisted in local SQLite state. |
| `openminion setup --list-providers` | Yes | Works. Machine-readable catalog used to pick provider/model defaults. |
| `openminion config init --provider ollama` | Yes | Works. Created the project-scoped `agents.json`. |
| Cortensor Portal (`cortensor-portal`, `oss-20b`) | No — not tested | No Portal access/key was available, and Portal is optional for qualification per the hackathon docs ("Participants without access will not be penalized"). The code supports it via `OPENMINION_PROVIDER=cortensor-portal` + `CORTENSOR_API_KEY`. |
| Memory / skills / tasks / delegation / A2A / MCP | No | Not needed for this one-workflow agent; not claimed. |
| `openminion doctor --check-turn` | Attempted | See "Bugs / rough edges" below. |

## Bugs / rough edges found

Honest list — only things actually observed while building this project
(25 Nov 2026, `openminion 0.1.24`, Python 3.12, this VM):

1. **Ollama install script needs `zstd`, which was not installed.**
   `curl … | sh` failed with "This version requires zstd for extraction".
   `apt-get update` on this machine was extremely slow, so I downloaded
   `ollama-linux-amd64.tar.zst` directly and extracted it with the Python
   `zstandard` wheel instead. Not an OpenMinion bug — an environment
   gotcha worth noting for local-first setup docs.
2. **`/tmp` is a 512 MB tmpfs here.** The ~900 MB Ollama tarball filled it
   and `curl` failed with "Failure writing output to destination".
   Downloading to the workspace disk fixed it. Again environmental, not
   the SDK.
3. **A 1B local model writes short, loose briefs — and does not use
   tools.** In both recorded runs `tool_calls` was 0: `llama3.2:1b`
   answered from its own knowledge, hallucinated a developer
   ("OpenMinedition") and a source URL in run 1, and declined outright
   in run 2. That is why `brief.py` has a verbatim fallback and records
   the parse in the output (`parse_note`): a weak model degrades
   visibly, not silently. With a hosted model the same code should do
   better; the fallback exists so the failure mode is on the record.
4. **httpx (used by OpenMinion's providers) cannot parse bracketed
   IPv6 literals in `no_proxy`.** This sandbox sets
   `no_proxy=localhost,127.0.0.1,::1,[::1],…`; any run failed with
   `InvalidURL: Invalid port: ':1]'` until the bracketed entries were
   stripped. Bisected entry by entry: `[::1]` and `[fd8b:…]` fail, the
   bare forms (`::1`, `fd8b:…`) parse fine. `run.sh` and `main.py`
   sanitize `no_proxy`/`NO_PROXY` at startup (localhost routing is
   preserved). This is an httpx limitation, not an OpenMinion bug, but
   it bites any OpenMinion-on-Ollama run in an environment whose
   `no_proxy` contains bracketed IPv6.
5. **`ollama pull` hung on "pulling manifest" for 6+ minutes** (two
   attempts, zero bytes downloaded) even though direct `curl` to the
   registry worked in under a second. Workaround: the model blobs were
   fetched with `curl -L` straight into Ollama's layout
   (`~/.ollama/models/blobs/sha256-…` + the manifest), after which
   `ollama list` showed `llama3.2:1b` and it ran normally. Likely the
   Ollama server's registry path through this sandbox's proxy; not an
   OpenMinion issue.
6. **The SDK's default turn timeout (90 s) is too short for a cold
   1B CPU model.** The first real run died with `TurnTimeoutError`
   after 90.00 s. `agent.run(..., timeout_seconds=600)` fixed it;
   warm runs took ~2.6–3.7 min. `OPENMINION_TURN_TIMEOUT` overrides it.
7. **No SDK bugs found in the paths used.** `Agent`, `@tool`, sessions,
   config init, and the provider catalog all behaved as documented.
   No bug report / fix PR is claimed from this project.

## What We Learned

- The 0.1 Python API is genuinely small: `Agent` + `@tool` + `run()` is
  enough for a complete workflow, and the README/quickstart examples
  match the installed 0.1.24 package exactly.
- The provider catalog (`setup --list-providers --json`) is the reliable
  source of truth for provider ids, credential env vars, and default
  models — better than copying a table from docs.
- For a local-first agent, the real setup cost is the model runtime
  (Ollama install, model download, RAM), not the SDK. Documenting the
  Ollama path end-to-end (including the `zstd` / disk-space gotchas)
  would help the next builder more than another SDK example.
- Portal access remains the one untested path here; if Portal capacity
  opens up, the same agent runs against it with only env changes.

## Submission status

- [x] Public repo (this one — push pending)
- [x] README with setup + run instructions
- [x] One working example + real model-backed run (`outputs/`)
- [x] Building Blocks Tested note (above)
- [x] What We Learned note (above)
- [x] 1–5 minute demo video — script in `docs/DEMO_SCRIPT.md`
      (video file itself is recorded by the builder; see script)
- [ ] **PR to the Hackathon #5 repository — PENDING.** The official
      Hackathon #5 PR repository URL has not been published yet
      (docs say "The repository URL will be added before kickoff").
      Do not guess it: check the
      [Cortensor Discord](https://discord.gg/cortensor) / docs before
      submitting, then open the PR linking this repo.
- [ ] Fork + star `openminion/openminion`, follow OpenMinion + Cortensor
      (do this from the builder's own GitHub/X accounts before submit).

No secrets are in this repo: `.env` is git-ignored, keys come only from
the environment, and the sample output contains no credentials.
