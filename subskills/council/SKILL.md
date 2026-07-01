# Subskill: council (Phase 10)

You run the judgment layer: four independent sales-consultant seats answer the same questions over the
run digest, blind to each other, then a synthesis seat reconciles them. The four seats are different
lenses on the same evidence, and the value comes from them not converging prematurely. The synthesis
seat states where they agree, where they genuinely disagree, and the ranked changes leadership should
make, with craft kept separate from outcome.

You are the conductor. A script aggregates the run, a script builds the digest the seats read, and you
spawn five subagents (four blind seats plus one synthesis). The seats do the judging; the scripts only
roll numbers up and fold the result back into the report.

Read `prompts/council.md` before you start. That template defines the four seats, the synthesis seat,
and the exact JSON each returns. Read `schema/DATA_CONTRACTS.md` for the `council_output.json` shape
`aggregate.py` reads.

## Preconditions

Scoring, post-mortems, and adherence (Phases 7 to 9) must be done, since the digest is built from the
aggregate of all of them. The working folder is `<workdir>`, resolved from `AUDIT_WORKDIR` or
`--workdir`.

## Step 1: Aggregate, so the digest has something to read

```
python3 scripts/aggregate.py --workdir <workdir>
```

This rolls the per-call atoms up to rep, deal, and org and writes `analysis/report_data.json`. The
digest builder reads that file, so run this once before building the digest. It is pure plumbing.

## Step 2: Build the council digest

```
python3 scripts/digest.py --workdir <workdir>
```

This folds `report_data.json` into `<workdir>/analysis/council_digest.json`: the funnel, the stall pile,
the org floor and strong dimensions, the dimension averages, the MEDDIC reality counts, the
maker-checker adherence, the per-rep craft spread with each rep's recurring failure and signature, and a
curated set of the highest-stakes deal post-mortems. This one file is what every seat reads. It is pure
plumbing; it makes no model call.

## Step 3: Run four blind seats plus one synthesis seat (host-agent mode, the default)

Spawn **five** subagents total. The four seats run first, each in a fresh context so they stay blind to
each other; the synthesis seat runs last, over the four seat outputs.

The four blind seats, each a separate subagent reading `council_digest.json` and answering the seat
questions in `prompts/council.md`:

1. **Technical-discovery diagnostician.** Where do deals die technically, and is it a craft problem or a
   structural one? Reads the funnel, the stall pile, and the gap ledgers.
2. **Demo-craft coach.** What do the SEs systematically do well and badly in demos across the lenses?
   Which spokes are the org's floor? Separate stage-appropriate NA from real weakness.
3. **POC / validation strategist.** How well are POCs scoped and controlled? Where is the Technical Win
   reached but the deal lost, or the POC drifting with no criteria?
4. **Enablement / competitive skeptic.** What would coaching individuals NOT fix: competitive-technical
   positioning, security readiness, champion enablement, knowledge gaps, missing artifacts? Be adversarial.

Keep them blind. Do not let one seat see another seat's output, and do not summarize one seat into
another's prompt. Each returns its own JSON object (`seat`, `findings`, and the four `answer_*` fields)
per `prompts/council.md`. Run the four in parallel; they are independent.

Then the **synthesis seat**, one more subagent, runs over the four seat outputs (not the digest alone).
It returns the synthesis JSON: `consensus`, `tensions`, `ranked_changes`, and the `craft_vs_outcome_note`
that reminds leadership where strong craft still lost and weak craft still won, so the two are not
conflated.

Assemble the five results into one file at `<workdir>/analysis/council_output.json` in the shape
`schema/DATA_CONTRACTS.md` specifies:

```
{seats:[<the four seat objects>], synthesis:{<the synthesis object>}}
```

`seats` is the array of the four seat JSON objects in order; `synthesis` is the synthesis object. Write
exactly what the subagents returned, taking only the JSON if any wraps it in prose.

### API alternative (opt-in)

In API mode, the same `prompts/council.md` is looped through the API backend as five calls (four blind
seats, then synthesis over their outputs), keeping the four blind to each other, when an operator has set
an endpoint and key in `.env`. The output contract is identical. Host-agent spawning is the default and
needs no key.

## Step 4: Fold the council back into the report

```
python3 scripts/aggregate.py --workdir <workdir>
```

Run aggregate once more. It now finds `analysis/council_output.json` and folds it into
`report_data.json`, so the council appears on the report's Council page. This second run is what makes
the council visible downstream.

## Gate

`analysis/council_output.json` exists with four seat objects and a synthesis object, and the second
`aggregate.py` run has folded it in (its output mentions the run completing without dropping the council
file). The seats stayed blind to each other and the synthesis ran over their outputs.

## Boundaries

- You run the seats and assemble their JSON. You do not write the findings yourself, merge seats early,
  or let the synthesis seat read the digest in place of the four seats' outputs.
- Keep craft separate from outcome, as the synthesis note requires. A strong rep on a lost deal is not
  marked down; a weak rep on a won one is not credited.
- Keep any prose you write plain. No em-dashes, no en-dashes, no buzzword filler.
