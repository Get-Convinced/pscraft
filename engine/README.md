# engine: how judgment runs

Every judgment step in this skill is a **task**: one prompt template from `prompts/` filled with one
unit of input (one call, one deal, one research target, one rep), returning one validated JSON object.
This directory is the contract for how those tasks execute.

There are two modes. The default needs no setup and ships no keys. The optional one is for large or
headless runs. **The output contract is identical in both**, so the plumbing scripts and the report
never know or care which mode produced a result.

## No keys ship with this skill

Nothing in this directory or anywhere in the skill contains an API key, an endpoint, or any operator
data. Host-agent mode (the default) needs no key at all. API mode reads its key only from a local
`.env` that the operator creates and that `.gitignore` blocks from ever being committed. If you are
reading this to run the skill: you do not need to set anything up unless you choose API mode.

## Host-agent mode (default)

You are inside an agentic CLI that can spawn subagents (Claude Code, Claude cowork, Codex, and
similar). In this mode:

- Each judgment task is **a subagent the host spawns**. The host fills the prompt template with one
  unit of input and the subagent returns the JSON for that unit.
- The model is **whatever the host CLI runs**. There is no separate model to pick, no key to set, and
  no endpoint to configure.
- **Independent tasks run in parallel.** Scoring fans out one subagent per in-scope call; research
  fans out one per source target; role inference one per person. Batch the fan-out to the host's
  concurrency limit. Tasks that depend on an earlier result (the council on the digest, the synthesis
  seat on the four seats) wait for it; everything else runs concurrently.
- Maker-checker independence (Phase 9) is achieved by running the checker in a **fresh context** so it
  is blind to the scorer's reasoning, even when maker and checker share the host's model.

Prefer this mode whenever a subagent capability exists. It is the simplest, has nothing to install,
and keeps every transcript inside your CLI session.

## API mode (opt-in)

For very large corpora or fully headless runs, point the skill at an OpenAI-compatible endpoint. The
`scripts/*_via_api.py` drivers loop the same `prompts/` templates through `engine/llm.py`, which sends
chat completions to the endpoint and extracts the JSON. You opt in by creating a local `.env`.

Set these **generic** variables in `$AUDIT_WORKDIR/.env` (or in `<skill>/.env`):

```
LLM_PROVIDER=openai        # provider switch: openai | anthropic | deepseek | local
LLM_API_KEY=sk-...         # your key. read only from this gitignored file (or the environment)
LLM_BASE_URL=https://...   # the OpenAI-compatible base URL for your provider
LLM_MODEL=...              # the model id to score with
```

`LLM_PROVIDER` selects the request shape for that vendor. `LLM_BASE_URL` and `LLM_MODEL` point at the
exact endpoint and model. `LLM_API_KEY` is read only from the gitignored `.env` or the process
environment, never from anything committed. For maker-checker independence you can set a second model
for the checker (the operator supplies it); if only one model is available, the checker still runs in
a fresh blind context.

The drivers run tasks concurrently with a thread pool and retry on transport errors and on malformed
JSON, so a single bad response does not wedge a batch. Same input list, same prompt templates, same
output files as host-agent mode.

## The output contract is identical in both modes

Whichever mode runs, a judgment task writes the same JSON shape that the plumbing expects. The schemas
in `schema/` define those shapes (call scores, role records, post-mortems, council output). Because
the contract is fixed:

- `scripts/merge_scores.py`, `scripts/aggregate.py`, and `scripts/report_app.py` read the same files
  regardless of engine.
- You can score most of a corpus in host-agent mode and a long tail in API mode, or re-run one phase
  in the other mode, and the aggregation still joins cleanly.
- The anti-slop gate, the read-every-call invariant check, and the verification gates in RUNBOOK.md
  all operate on the output, so they hold under either engine.

Pick the engine once at the start of a run (RUNBOOK Phase 0). After that, the rest of the run is
engine-agnostic.
