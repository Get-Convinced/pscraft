# Subskill: adherence (Phase 9, maker-checker)

You audit the scorer's own work. A sample of the scored calls is re-read by an **independent** agent,
the checker, who never scored those calls. The checker reads each transcript fresh, then audits the
scorer's output against the seven calibration rules: explainer-quote grounding, read-the-whole-turn,
scale-anchoring, the craft-versus-outcome firewall, earned-on-the-call, demo So-What (a feature-dump must
not score as high demo craft), and anti-slop. It returns a verdict per explainer and a spot re-score on
the dims it most disagrees with. This is the quality control on
the scores, and it surfaces a punch-list for human review.

The one thing that makes this phase work is independence. The checker must not inherit the scorer's
mistakes. If the same seat that scored a call also checks it, it will confirm its own reasoning. So the
checker is a fresh subagent, blind to how the scorer reasoned, and if your host supports it, a different
model or an explicitly skeptical instruction.

You are the conductor. A script prepares one task per sampled call (the scorer's output for that call
plus the full transcript) and you spawn one independent subagent per task. The script never judges a
call; it only samples and fills the prompt.

Read `prompts/adherence_check.md` before you start. That template is the exact prompt, the six rules,
and the JSON shape each task returns. Read `schema/DATA_CONTRACTS.md` for the `adherence_calls` and
`adherence.json` shapes.

## Preconditions

Scoring (Phase 7) must be done, since the checker audits the `call_out` files. Also required:
`canonical/transcripts.json` and `config.json`. The working folder is `<workdir>`, resolved from
`AUDIT_WORKDIR` or `--workdir`.

## Step 1: Emit checker tasks over a sample

```
python3 scripts/build_tasks.py adherence --workdir <workdir> --sample 24
```

This samples evenly across the scored calls (up to `--sample`, default 24) and writes one task file per
sampled call to `<workdir>/analysis/tasks/adherence/`. Each task fills `prompts/adherence_check.md` with
the scorer's per-rep output for that call (the maker output the checker audits) and the full transcript
the checker reads independently. It makes no model call.

Each task file is JSON with these fields you use:

- `out_path`: where the result goes (`analysis/adherence_calls/check_<id>.json`).
- `prompt`: the filled `prompts/adherence_check.md` to hand to a checker subagent verbatim.
- `call_id`, `account`: for tracking.

## Step 2: Run one INDEPENDENT checker per task, in parallel (host-agent mode, the default)

For each task file, spawn a **fresh** subagent as the checker. This is the part that must not be cut.
The checker has to be a separate seat from whatever scored the call, so it does not rubber-stamp the
scorer's reasoning:

- **Always a fresh subagent.** Never reuse a scoring subagent's context to check its own call.
- **A different model if your host can.** If your host can run a second model, give the checker a
  different one than the scorer used. A second pair of eyes catches what the first missed.
- **An explicitly skeptical instruction if it cannot.** If only one model is available, keep the
  checker fresh and lean on the prompt's adversarial framing; the template already tells the checker it
  is an independent auditor whose job is to find rule breaks, not to agree.

Give the checker the task's `prompt` and nothing else. It reads the transcript itself, audits the maker
output, and returns ONE JSON object: per rep a `verdict` (`pass`, `minor`, or `major`), a list of rule
violations, and up to two `rescore` disagreements. Write that JSON to the task's `out_path`. Run the
tasks in parallel batches; sampled calls are independent of each other.

### API alternative (opt-in)

In API mode, set a **different** `LLM_MODEL` for the checker than the scorer used, then loop the same
task files through the API backend. A different model is the API way of getting an independent seat. The
output contract is identical. Host-agent spawning of fresh subagents is the default and needs no key.

## Step 3: Roll the checks into the adherence aggregate

```
python3 scripts/merge_scores.py --workdir <workdir>
```

This collects every `check_<id>.json` and rolls them into `<workdir>/analysis/adherence.json`: the
pass-rate, the verdict counts, the violations grouped by rule, the mean re-score gap, and the list of
majors. It prints how many calls were audited.

## Reading the verdict

The aggregate is what the report and the council read. Interpret it honestly:

- **pass**: the checker found no rule break and no meaningful re-score gap. The scorer's call holds.
- **minor**: a soft issue only: a scale-anchoring or read-the-whole-turn or craft-versus-outcome or
  anti-slop nit, or a one-point re-score gap. Worth noting, not worth blocking on.
- **major**: a hard break: a rep-quote grounding failure (a quote that is not the rep's words or is
  not in the transcript), a MEDDIC-credited-from-the-CRM failure, or a re-score gap of two or more on a
  real dim. Majors are the punch-list. They are the calls a human should re-read before trusting the
  score, and they are listed by call, account, rep, and reason in `adherence.json`.

A sampled pass-rate is a confidence signal on the whole run, not a grade on individual reps. Report the
pass-rate and the count of majors honestly when you hand the audit over. A low pass-rate means the
scoring pass needs another look, not that the reps are worse.

## Gate

`merge_scores.py` writes `analysis/adherence.json` and reports the calls audited. The phase is done when
the sample has been checked by independent seats and the aggregate exists. Carry the pass-rate and the
majors forward; the council and the final report both surface them.

## Boundaries

- The checker audits, it does not re-author the scores. Its `rescore` is a disagreement on the record,
  not a rewrite of `call_out`. The original scores stand; the adherence pass reports confidence in them.
- You do not let the checker and the scorer be the same seat. Independence is the method here.
- Keep any prose you write plain. No em-dashes, no en-dashes, no buzzword filler.
