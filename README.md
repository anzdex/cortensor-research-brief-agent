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

All runs are real OpenMinion turns against local Ollama on this VM
(CPU-only, 1.5 shared CPUs, 8 GB RAM). Nothing below is hand-written —
the outputs are the model replies, verbatim. Note: each run overwrites
`outputs/<slug>-brief.md`, so the files currently hold the *latest*
run per topic, not the first; the earlier runs are recorded here with
their stats so the history is not lost.

### Run 1 — "Cortensor", llama3.2:1b, 25 Nov 2026

- session `research-brief-cortensor`, run_id `8eb35be4adae4e409507e6732aa28bf8`
- stats: `input_tokens 3977, output_tokens 571, llm_calls 3,
  tool_calls 0, tool_errors 0, duration_ms 221213` (~3.7 min)
- The model returned valid JSON, so the brief parsed cleanly
  ("Parsed from the model's JSON reply"). **But the content is wrong:**
  it claims Cortensor is "a machine learning model developed by
  OpenMinedition" and cites an invented URL
  (`https://openminion.com/cortensor-model`). The 1B model hallucinated
  instead of using the Wikipedia tools. This output is kept on record
  here on purpose — it is the honest record of what the small local
  model does. (The file `outputs/cortensor-brief.md` has since been
  overwritten by runs 8–10; see below.)

### Run 2 — "OpenMinion", llama3.2:1b, 25 Nov 2026

- session `research-brief-openminion`, run_id `9de961880ef24eb4bb846a6230ddebb9`
- stats: `input_tokens 3962, output_tokens 481, llm_calls 3,
  tool_calls 0, tool_errors 0, duration_ms 155064` (~2.6 min)
- The model declined ("I don't have enough information…") and did not
  return JSON, so the verbatim fallback fired and the reply was stored
  as the summary ("Model reply was not valid JSON; stored verbatim as
  the summary"). The fallback works as designed — a weak model degrades
  visibly, not silently. (The file `outputs/openminion-brief.md` has
  since been overwritten by runs 5–6; see below.)

### Runs 3–4 — bigger models, still no tools (26 Nov 2026)

The 1B model never called a tool, so two larger local models were
tried with the stock config. Both parsed cleanly from JSON but still
made **0 tool calls** and hallucinated:

- Run 3 — "OpenMinion", llama3.2:3b: run_id
  `96f4e0e0e2944812b79cd382f785021c`, 3 LLM calls, 0 tool calls,
  528 out / 3910 in tokens, ~473 s. Claimed OpenMinion is a
  digital-forensics tool from 2018 and invented
  `https://openminion.org/`.
- Run 4 — "OpenMinion", qwen2.5:7b: run_id
  `4e5a77b652d649a5a14da90dcb8161a5`, 3 LLM calls, 0 tool calls,
  378 out / 4069 in tokens, ~910 s. Claimed OpenMinion is an
  open-source hardware platform, no sources.

### Root cause found — Ollama `tool_call_strategy="fallback"` (26 Nov 2026)

The 0-tool result was not the models' fault. In OpenMinion 0.1.24 the
Ollama provider defaults to `tool_call_strategy="fallback"`; the
adapter only sends `payload["tools"]` when the strategy is
`"native"`/`"hybrid"`, and the fallback parser is only enabled when
the tools are schema-only submit-output. With three real tools,
**tools are never sent to the model and fallback parsing is disabled
— 0 tool calls is guaranteed, regardless of model size.** Other
providers default to `"hybrid"`, which is why tools work on hosted
providers. Fixed by setting `providers.ollama.tool_call_strategy` to
`"native"` in the project config, and `ensure_config()` in
`brief_agent/agent.py` now forces `"native"` for the ollama provider
(with a comment) so a fresh `openminion config init` cannot silently
recreate the broken default. pytest still 5/5.

### Runs 5–6 — "OpenMinion", llama3.2:3b, native tools (26 Nov 2026)

- Run 5: run_id `95e26ec5c299419aa081765e5c7adcd2`, stats
  `input_tokens 16206, output_tokens 647, llm_calls 7, tool_calls 2,
  tool_errors 0, duration_ms 960425` (~16 min). **Tools worked:**
  `wikipedia_search("OpenMinion")` and `wikipedia_fetch("OpenMinion")`
  both completed. But the run stopped on the SDK's
  `brain_turn_timeout_seconds` (300 s default): the final text is
  "Stopped: turn time limit reached (300s/300s)", stored verbatim.
  This is the current `outputs/openminion-brief.md`.
- Run 6: turn budget raised to 1800 s. The 3B model called tools
  5+ times (`wikipedia_search` ×3, `wikipedia_fetch` ×2) across 12+
  LLM calls but **kept re-searching instead of composing the brief**
  and hit `TurnTimeoutError` after 1800.00 s. No brief written. The
  3B model does not converge on this workflow; it loops on research.

### Runs 7–11 — qwen2.5:7b, native tools (26 Nov 2026)

- Run 7 — "Cortensor": 2 tool calls, both completed
  (`wikipedia_search("Cortensor")` call `call_x6y9y1e2`,
  `wikipedia_fetch("Cortensor")` call `call_0ek2ak3z`), then
  `TurnTimeoutError` after 1800.00 s while in "Evaluating results…".
  No brief written. The run log is shown in the demo video.
- Run 8 — "Cortensor" resume (same session): run_id
  `bdb4b17dcd744ecc866a3ee5b6650e03`, stats `input_tokens 6036,
  output_tokens 195, llm_calls 3, tool_calls 0, duration_ms 858714`
  (~14 min). The model refused: "I could not safely update the task
  conditions. Please restate the current task and its required
  conditions." — resuming a timed-out session confuses the model.
  Stored verbatim; this is the current
  `outputs/cortensor-brief.md`.
- Run 9 — "Cortensor Network" (fresh session): 1 tool call
  (`wikipedia_search`), killed ~20 min in by a service restart that
  wiped `/tmp` and stopped Ollama/Chrome. No brief written.
- Run 10 — "Cortensor Network" (fresh session, continued): 1 tool
  call, then a 3493-token prefill failed with HTTP 500 after exactly
  300 s — the provider timeout (`PROVIDER_TIMEOUT_S = 300`) is
  shorter than a 7B cache-miss prefill at ~10 tok/s. Fixed by raising
  `PROVIDER_TIMEOUT_S` to 900 s in `brief_agent/agent.py` (pytest
  still 5/5); a 3262-token prefill that took 324 s then completed.
- Run 11 — "Cortensor Network" (fresh session, continued, provider
  timeout 900 s, turn budget 3600 s): **2 tool calls, both completed**
  (`wikipedia_search` + `wikipedia_fetch("Cortensor Network")`,
  call `call_iswz6wda`), then the final composition ran into CPU
  contention (generation as slow as 0.26 tok/s) and hit
  `TurnTimeoutError` after 3600.00 s (~60 min). No brief written.

**Bottom line for the Ollama path:** with `tool_call_strategy="native"`
the agent genuinely calls real tools and gets real Wikipedia results
— the tool path is proven end-to-end. But on this CPU-only shared box
a 7B model needs well over 60 minutes for a full native run (prefill
5–10 tok/s, generation 0.26–2.5 tok/s under contention), and the 3B
model loops instead of composing. No clean, accurate brief with real
tool calls was completed locally. That is why `docs/DEMO_SCRIPT.md`
records the demo against a hosted provider (which needs an API key the
builder did not have) and the demo video shows the real run + real
tool-call log rather than a finished brief. The video file is
`demo/cortensor-demo.mp4` (127 s, 1280x800, 30 fps, H.264, no audio).

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
| `@tool` with `READ_ONLY` / `idempotent` | Yes | Tools work when called directly (`wikipedia_search`/`wikipedia_fetch` returned real Wikipedia data) **and through the agent**: with `tool_call_strategy="native"` the 3B and 7B models called `wikipedia_search` + `wikipedia_fetch` for real (runs 5, 7, 11 — 2 tool calls each, 0 errors). The through-agent tool path, including the default action policy's no-confirmation behaviour for read-only tools, is now proven end-to-end. See "Real runs" for the root cause (`"fallback"` default) that blocked it before. |
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
   For native-tool runs the *brain* turn timeout also matters:
   `runtime.brain_turn_timeout_seconds` defaults to 300 s and stopped
   run 5 mid-composition; it was raised to 1800 s, then 3600 s, in the
   local (git-ignored) project config — a 7B native run still timed
   out at 3600 s because of CPU speed, not the limit itself.
7. **The Ollama provider's `tool_call_strategy="fallback"` default
   silently disables tools** (OpenMinion 0.1.24). See "Real runs —
   Root cause found" above. Fixed in-repo: `ensure_config()` forces
   `"native"` for the ollama provider. This is the one genuine SDK
   rough edge found in this project; it is worth a docs note (or a
   different default) upstream, but no bug report is claimed here.
8. **The Ollama provider timeout (300 s) is shorter than a 7B
   cache-miss prefill on CPU.** A 3493-token prompt prefills at
   ~10 tok/s (~350 s) and the call failed with HTTP 500 after exactly
   300 s. `PROVIDER_TIMEOUT_S` was raised 300 → 900 s in
   `brief_agent/agent.py` (pytest still 5/5); a 3262-token prefill
   taking 324 s then completed. A hosted provider would not hit this.
9. **Small local models do not converge on this workflow.**
   `llama3.2:3b` with working tools looped (5+ tool calls, 12+ LLM
   calls, re-searching instead of composing) and never produced the
   JSON brief in 1800 s. `qwen2.5:7b` does the research correctly but
   needs well over 60 min on this CPU-only shared box (prefill 5–10
   tok/s, generation 0.26–2.5 tok/s under contention). Resuming a
   timed-out session confuses the model ("I could not safely update
   the task conditions").
10. **Two service restarts (26 Nov 2026) wiped `/tmp` and killed
    runs in flight.** The recording/viewer/probe tooling lived in
    `/tmp` and had to be rebuilt twice; the durable copies now live
    in `demo/support/` so a rebuild is a copy, not a rewrite.
11. **No SDK bugs found in the paths used, apart from item 7.**
    `Agent`, `@tool`, sessions, config init, and the provider catalog
    all behaved as documented. No bug report / fix PR is claimed from
    this project.

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
- [x] 1–5 minute demo video — `demo/cortensor-demo.mp4` (127 s,
      1280x800, 30 fps, H.264, no audio; real screen recording:
      title + repo tour + live 7B run start + the real run log with
      `wikipedia_search`/`wikipedia_fetch` tool calls + end card).
      Script in `docs/DEMO_SCRIPT.md`. Note: the script's hosted-
      provider demo step needs an API key (none was available), so
      the video shows the Ollama path honestly — real tool calls,
      no finished brief (see "Real runs — Bottom line").
- [x] Fork + star `openminion/openminion`, follow OpenMinion +
      Cortensor — done 26 Nov 2026 (fork
      `github.com/anzdex/openminion`, star 57→58).
- [ ] **PR to the Hackathon #5 repository — PENDING.** The official
      Hackathon #5 PR repository URL has not been published yet
      (docs say "The repository URL will be added before kickoff").
      Do not guess it: check the
      [Cortensor Discord](https://discord.gg/cortensor) / docs before
      submitting, then open the PR linking this repo.

No secrets are in this repo: `.env` is git-ignored, keys come only from
the environment, and the sample output contains no credentials.
