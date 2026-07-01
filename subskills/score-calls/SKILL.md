# Subskill: score calls (Phase 7)

You score every in-scope call. One task per call: a model reads the whole transcript and returns, for
each technical explainer on it, per-dimension scores with the explainer's own quotes and qualitative
failure points. The technical explainers are whoever carried the technical work on the call (from
`call_company.json`), title-agnostic. This is the atom the whole report aggregates up from. If a call
is not scored, it does not exist in the audit, so the one invariant that defines this phase is **every
in-scope call is read in full by a model**.

You are the conductor. A script prepares the tasks (which calls, which technical explainers on each,
their responsible dimensions, the SE stage, the POC criteria, the competitor, the prior-call arc) and a
script collects and verifies the results. The judgment in between is done by subagents you spawn. You never score a call yourself in one pass over the corpus,
and a script never reads a transcript for meaning.

Read `prompts/call_score.md` before you start. That template is the exact prompt each task runs and the
exact JSON shape each task returns. Read `schema/DATA_CONTRACTS.md` for the `call_out` shape the
collector validates.

## Preconditions

These phases must be done before scoring, because the task-prep reads their output:

- company research (`company_context.md` exists),
- normalize (`canonical/transcripts.json` exists),
- config (`config.json` exists),
- roles (`analysis/roles.json` exists),
- link (`analysis/opp_index.json` and the per-call company file exist).

The working folder is `<workdir>`, resolved from the `AUDIT_WORKDIR` environment variable or a
`--workdir` argument, the same way every script resolves it.

## Step 1: Emit one task per in-scope call

```
python3 scripts/score_calls.py --emit-tasks --workdir <workdir>
```

This writes one task file per in-scope presale call to `<workdir>/analysis/tasks/score/`. It is pure
plumbing: it fills `prompts/call_score.md` with that call's transcript, the reps on it, their
responsible dimensions, the deal stage, and the prior-call arc. It makes no model call. It is
resume-safe: a call that already has an output file in `analysis/call_out/` is skipped, so re-running
after a partial run only emits the tasks still missing.

Each task file is JSON with these fields you use:

- `out_path`: where the result JSON goes, relative to the workdir (`analysis/call_out/call_<id>.json`).
- `prompt`: the filled `prompts/call_score.md` to hand to a subagent verbatim.
- `call_id`, `account`, `reps`: for your own tracking and batching; not needed by the subagent.

The script prints the count it emitted. Note that count. It is the number of subagents you will run and
the number of output files that must exist when you are done.

## Step 2: Run one subagent per task, in parallel batches (host-agent mode, the default)

For each task file, spawn one subagent. Give it the task's `prompt` and nothing else; the prompt is
self-contained (it carries the company context, the rubric anchors, the reps to score, and the full
transcript). The subagent's whole job is to return ONE JSON object in the shape `prompts/call_score.md`
specifies. Write that JSON to the task's `out_path` (join it onto the workdir to get the absolute path).

Discipline:

- **Parallel, in batches.** Independent calls have no dependency on each other. Spawn them in batches
  sized to your host's limits, not one at a time. A corpus of a hundred calls is a hundred tasks; run
  them in waves, not in series.
- **Hand over the prompt as-is.** Do not summarize the transcript, do not trim it, do not add your own
  instructions. The script already capped and filled it. Changing it breaks the read-every-call
  invariant and the score calibration.
- **Write exactly what the subagent returns.** The result is one JSON object. Write it to `out_path`
  with no edits. If a subagent returns prose around the JSON, take the JSON object only.
- **Re-run for stragglers.** If a subagent fails or returns something unusable, leave that `out_path`
  empty and re-run Step 1; it will re-emit only the missing tasks. Then run their subagents again.

### API alternative (opt-in, for very large corpora or headless runs)

Instead of Steps 1 and 2, run the same template through the API driver:

```
python3 scripts/score_calls.py --workdir <workdir>
```

With no `--emit-tasks`, the script fills the same `prompts/call_score.md`, calls the configured
OpenAI-compatible endpoint through `engine/llm.py`, and writes `analysis/call_out/` directly. It is
resume-safe and concurrent (`--workers`). The output contract is identical, so everything downstream
does not care which path ran. Use this only when an operator has set an endpoint and key in `.env`;
the host-agent path above is the default and needs no key.

## Step 3: Collect, verify, and confirm the read-every-call invariant

```
python3 scripts/merge_scores.py --workdir <workdir>
```

This validates the shape of every `call_out` file (it reports and drops malformed ones), then prints
the read-every-call check: the number of in-scope transcripts versus the number scored, and the call
ids of any that are missing. Read that line. It is the gate.

## Gate

Every in-scope call has a valid `call_out` file. `merge_scores.py` must print
`read-every-call: N/N in-scope transcripts scored -> OK` with **no missing call ids**. If it prints a
GAP with missing ids, you have not finished: re-emit (Step 1), re-run the subagents for those ids
(Step 2), and re-run `merge_scores.py` until the scored count equals the in-scope count. Do not advance
to post-mortems while any in-scope call is unscored. The whole method rests on this one number.

## Boundaries

- You run tasks and write their JSON. You do not invent scores, edit a subagent's scores, or fill in a
  call a subagent could not score. A missing score is a missing task to re-run, not a number to make up.
- You do not change the prompt the script emitted, and you do not score a call yourself outside a task.
- Keep any prose you write plain. No em-dashes, no en-dashes, no buzzword filler.
