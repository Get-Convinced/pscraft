# Subskill: post-mortems (Phase 9)

You write one post-mortem per deal. A deal is its in-scope calls grouped into a unit. For each unit a
model reads the deal's calls in full, in date order, and writes the technical arc: how it opened, what
moved it, where technical conviction was lost, why it parked or lost, the POC arc, the stall archetype,
the one change that most would have mattered, and a field-by-field check of the CRM (including the
technical-win flag) against what was actually earned on the calls. The Technical Win itself is inferred
separately in Phase 8, before this.

You are the conductor. A script prepares one task per deal (the deal's transcripts, its CRM MEDDIC, its
stage history, its notes, and the per-call failure findings the scorer already produced) and you spawn
one subagent per task. You never write a post-mortem yourself over the whole corpus, and the script
never reads a call for meaning.

Read `prompts/postmortem.md` before you start. That template is the exact prompt and the exact JSON
shape each task returns. Read `schema/DATA_CONTRACTS.md` for the post-mortem shape `aggregate.py` reads.

## Preconditions

**Scoring (Phase 7) must be done first.** The task-prep reads `analysis/call_out/` to fold each call's
failure findings into the post-mortem prompt, and the post-mortem leans on those findings to locate
where a deal lost pressure. A deal whose calls were never scored gets a thinner prompt. Also required:
`canonical/transcripts.json`, `config.json`, and `analysis/opp_index.json` (the deal units). The CRM
inputs (`deals.json`, `stage_history.json`, `notes.json`) are optional; the task degrades cleanly when
they are absent.

The working folder is `<workdir>`, resolved from `AUDIT_WORKDIR` or `--workdir`.

## Step 1: Emit one task per deal

```
python3 scripts/build_tasks.py postmortem --workdir <workdir>
```

This writes one task file per deal unit to `<workdir>/analysis/tasks/postmortem/`, named by unit index.
It is pure plumbing: it groups each unit's calls in date order (capped in length), pulls the unit's CRM
MEDDIC fields, stage transitions, and rep notes, gathers the failure findings the scorer wrote for those
calls, and fills `prompts/postmortem.md`. It makes no model call.

Each task file is JSON with these fields you use:

- `out_path`: where the result goes (`analysis/postmortem/deal_<unit>.json`).
- `prompt`: the filled `prompts/postmortem.md` to hand to a subagent verbatim.
- `unit_index`, `account`: for tracking.

The script prints the count. That is the number of subagents to run and the number of post-mortem files
that must exist when you are done.

## Step 2: Run one subagent per task, in parallel (host-agent mode, the default)

For each task file, spawn one subagent. Give it the task's `prompt` and nothing else; it is
self-contained. The subagent reads the deal's calls and returns ONE JSON object in the post-mortem
shape. Write that JSON to the task's `out_path` (join onto the workdir for the absolute path).

Discipline:

- **Parallel.** Deals are independent of each other. Run the tasks in batches sized to your host's
  limits, not in series.
- **Stay suspicious of the CRM, because the prompt enforces it.** The template makes the subagent label
  every CRM MEDDIC field as `observed` (the rep was seen earning it on a call, with a verbatim quote),
  `claimed` (it sits in the CRM but was never seen being gathered on any call, so it is unverified), or
  `contradicted` (a call shows otherwise). A field is real only if a rep earned it on a recording. Do
  not soften that in any wrapper you add; the trust-check in the report is built from these labels.
- **Hand over the prompt as-is** and **write exactly what the subagent returns**. Take only the JSON
  object if the subagent wraps it in prose.

### API alternative (opt-in)

The same task files can be looped through the API backend instead of spawned subagents (an API driver
reads each `analysis/tasks/postmortem/*.json` and writes its `out_path`), when an operator has set an
endpoint and key in `.env`. The output contract is identical. Host-agent spawning is the default and
needs no key.

## Step 3: Collect and verify

```
python3 scripts/merge_scores.py --workdir <workdir>
```

This validates the post-mortem files (it reports and drops any that are malformed) alongside the
call_out and adherence checks. Confirm it prints `postmortem N valid` with the count matching the
number of deal units, and no malformed files.

## Gate

Every deal unit has a valid `deal_<unit>.json`. If `merge_scores.py` reports malformed post-mortems or
a count short of the deal units, re-run the subagents for the missing or broken units and re-run
`merge_scores.py`.

## Boundaries

- You run tasks and write their JSON. You do not author a post-mortem yourself, edit a verdict, or
  upgrade a `claimed` field to `observed` because the CRM says so. The whole point is to keep the CRM
  honest against the recordings.
- You do not change the prompt the script emitted.
- Keep any prose you write plain. No em-dashes, no en-dashes, no buzzword filler.
