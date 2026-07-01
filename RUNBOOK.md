# RUNBOOK: running the presales audit

This is the operator procedure. Read it once before you start. The phase list and the non-negotiables in
`SKILL.md` hold throughout, and the locked design is in `SPEC.md`. You are the conductor: judgment is done
by model agents you spawn, plumbing is done by stdlib Python scripts in `scripts/`. A script never reads a
transcript or a document for meaning, and you never score the whole corpus in one pass.

PSCraft scores the **technical explainer** on each call (title-agnostic). Scripts are stdlib-only Python
3.9+. There is no install step.

Set the run directory once and keep it set. Every script reads it (or takes `--workdir`):

```bash
export AUDIT_WORKDIR=/abs/path/to/this-run
```

A finished run directory:

```
$AUDIT_WORKDIR/
  config.json            Phase 4
  company_context.md     Phase 2
  intake.json            Phase 1     mapping.json (Phase 3, model-produced column maps)
  .env                   optional, API mode only, gitignored, never committed
  raw/                   the operator's export. READ ONLY. never committed.
    transcripts/**       one file per call (Read.ai, Gong, Chorus, Fireflies, Otter, Zoom, plain text)
    crm/deals.csv  crm/stage_history.csv  crm/notes.csv          (all optional)
    poc/**  map/**  security/**  design/**                        (optional SE artifact docs)
    se_platform/export.csv  docs/**                               (optional)
  canonical/             Phase 3 output (transcripts + deals + notes + stage + poc_plans + map_plans +
                         security_qs + solution_designs + se_platform)
  analysis/              Phases 2 and 5 through 11 output
    company_context sources, roles.json, call_company.json,
    call_out/call_<id>.json, technical_win/deal_<unit>.json, postmortem/deal_<unit>.json,
    adherence/*.json, council_output.json, report_data.json
  report.html            Phase 12 output, the one self-contained report
```

Run top to bottom. Each phase lists its **inputs**, the **command or prompt** to run, the **gate** that
must be true before you advance, and the **degradation tier** for a missing optional input. Do not advance
past a failed gate. Every judgment phase runs one of two ways: **host-agent mode** (default; spawn one
subagent per task from `scripts/*_tasks` or `score_calls.py --emit-tasks`, run independent tasks in
parallel) or **API mode** (opt-in; the `scripts/*_via_api.py` drivers loop the same templates through
`engine/llm.py`). The output JSON is identical either way.

---

## Phase 0: resolve engine and working folder

Resolve host-agent (default) vs API. Create the tree:

```bash
mkdir -p "$AUDIT_WORKDIR"/{raw/transcripts,raw/crm,raw/poc,raw/map,raw/security,raw/design,raw/docs,canonical,analysis}
```

Tell the operator which engine you resolved and roughly how many model reads the run costs: about one per
in-scope call for scoring, one per deal for the Technical Win, one per deal for the post-mortem, one per
artifact document, plus research, role inference, an adherence sample, and the council.

**Gate:** the `raw/` tree exists and the engine is stated. **Degradation:** none.

---

## Phase 1: intake

Run `subskills/intake/`. **Transcripts are required.** Ask the operator once, in a single prompt, for the
optional inputs: CRM export, rep notes, stage history, POC/POV success-criteria docs, mutual action plans,
security questionnaires, solution designs, an SE-platform export, and company docs. Place each under the
matching `raw/` subdir and record a manifest (`intake.json`) of what is present.

**Gate:** at least one transcript is present and readable, and the manifest is confirmed. Zero transcripts
means stop. **Degradation:** no CRM means craft-only (no funnel, no trust check); no POC docs means POC
scoping is judged from the calls alone; no SE platform means no flag cross-check. Note each in `config.caveats`.

---

## Phase 2: company research

Run `subskills/company-research/`. Disambiguate the entity, plan where the knowledge lives, fan out a
research swarm in parallel, fold in operator docs, and synthesize `company_context.md` using
`schema/company_context.template.md`: product and integrations, the technical buyer and champion, what a
credible **technical** claim sounds like (and the overclaim traps), the competitive **technical**
differentiation, the security/compliance posture, and the POC/evaluation norms.

**Gate:** `company_context.md` names the right entity and fills the "What a credible technical claim sounds
like", "Security & compliance posture", "POC / POV & evaluation norms", and "Presales motion and roles"
sections (the scorer and role inference depend on them). **Degradation:** mark unknowns plainly; never
invent a competitor, integration, or cert.

---

## Phase 3: normalize (plumbing) + 3.5 artifact ingest (judgment)

```bash
python3 scripts/normalize.py
```

Maps transcripts and any CRM/notes/stage/SE-platform exports into the canonical model. When CRM headers do
not match the synonym lists, have a model propose the column mapping (`prompts/crm_mapping.md`) and write
`mapping.json`. Structure only, never meaning.

**3.5 artifact ingest.** For any POC/MAP/security/design docs:

```bash
python3 scripts/build_tasks.py doc-ingest
```

Run one subagent per task filling `prompts/poc_ingest.md` (reads each document IN FULL, emits structured
JSON to `analysis/<kind>_out/`). Then rerun `python3 scripts/normalize.py`, which collects them into
`canonical/poc_plans.json`, `map_plans.json`, `security_qs.json`, `solution_designs.json`.

**Gate:** the canonical call count equals the transcript count the operator expects (minus explicit drops);
POC criteria docs, if provided, land in `canonical/poc_plans.json`. **Degradation:** with no CRM, only
`transcripts.json` (plus any artifact docs) is produced; the run continues craft-only.

---

## Phase 4: config

Generate `config.json` from `schema/config.template.json` using `prompts/config_generate.md`: org name and
domains, scope, the SE `stage_map` (map each raw CRM label to a canonical rung), `technical_win.source`,
`reporting` (QoQ), exclusions, aliases. Leave `stage_map` empty until the real stage labels are visible.

**Gate:** validates against the template, `org_domains` is correct (it decides who is a rep), and
`stage_map` covers every raw stage label. **Degradation:** no CRM means no `stage_map`; leave it empty.

---

## Phase 5: technical-explainer roles (judgment)

Build the roster (every `org_domains` email seen on calls, plus every CRM deal owner and SE owner). Run
`prompts/role_inference.md` per person: infer the archetype (solution-engineer / seller-doing-technical /
se-leader / ae-nontechnical / partner-external), kind, seniority level, and whether they carried the
technical-explainer role. Write `analysis/roles.json`.

**Gate, show the operator the full role table.** Correct any misattributed archetype, seniority, or
exclusion in `config.roles.overrides`. **Degradation:** thin CRM means the roster is built from call
attendance alone; mark low confidence.

---

## Phase 6: name + link + SE-stage (plumbing + one judgment pass)

```bash
python3 scripts/build_tasks.py naming     # emits one naming task per substantive call
# run each subagent (prompts/account_naming.md) -> analysis/naming_out/<call_id>.json
python3 scripts/merge_scores.py           # collects naming_out into call_company.json
python3 scripts/link.py                   # joins calls to deals, funnel, stall pile, conservation gate
```

The naming pass reads each call to name the account, bucket it, flag quality, list the **technical
explainers** present, and infer the **SE stage**. `link.py` never silently drops a call; an unnamed
substantive call holds the gate open.

**Gate, show the operator the verification counts** (deals parsed, transcripts ingested, calls joined,
in-scope calls, the ledger balancing). Confirm the `stage_map` now that the real labels are visible.
**Degradation:** no CRM means nothing to join to; every external call still becomes an in-scope scoring
unit, and the naming pass still buckets and stage-tags each call.

---

## Phase 7: score calls (judgment, one task per in-scope call)

```bash
python3 scripts/score_calls.py --emit-tasks
# run one subagent per task (prompts/call_score.md) -> analysis/call_out/call_<id>.json
python3 scripts/merge_scores.py
```

Each task reads the call in full and, for each technical explainer on it, returns per-dimension scores
(with the explainer's own quote), the per-lens demo read when a demo occurred, the prospect-gap
contributions, and qualitative failure points. Stage-aware: a move not yet due at the call's SE stage is
NA, not a failure.

**Gate:** `len(call_out/call_*.json) == in-scope call count`, and every technical explainer on every scored
call appears in a score block. Spot-check three cited quotes: verbatim, attributed to the explainer.
**Degradation:** thin or poor transcripts yield more NA at lower confidence, never invented marks.

---

## Phase 8: technical win (judgment, one task per deal)

```bash
python3 scripts/build_tasks.py technical_win
# run one subagent per task (prompts/technical_win.md) -> analysis/technical_win/deal_<unit>.json
```

Each infers the Technical Win state and builds the gap ledger (each prospect-voiced gap: addressed-written
/ addressed-verbal / open / ignored) and tags any CRM/SE-platform technical-win flag as corroborated or
not. Have the output echo its `unit_index` and `account`.

**Gate:** one file per in-scope deal; every gap and the reached-on moment cites a verbatim call quote; a
platform flag with no corroborating call moment is marked uncorroborated. **Degradation:** none; with no
CRM the business_outcome is left unknown, the Technical Win is still inferred from the calls.

---

## Phase 9: post-mortems (judgment, one task per deal)

```bash
python3 scripts/build_tasks.py postmortem
# run one subagent per task (prompts/postmortem.md) -> analysis/postmortem/deal_<unit>.json
```

Each returns the technical arc, where conviction was lost, the POC arc, the stall archetype, the one
change, and the CRM/platform-vs-call check (including the technical-win flag).

**Gate:** one post-mortem per in-scope deal with a call; every observed/contradicted claim cites a quote.
**Degradation:** no CRM means no post-mortems and no trust check; skip this phase.

---

## Phase 10: adherence, maker-checker (judgment)

```bash
python3 scripts/build_tasks.py adherence --sample 24
# run each with an INDEPENDENT seat (prompts/adherence_check.md) -> analysis/adherence_calls/
python3 scripts/merge_scores.py           # rolls the checks into analysis/adherence.json
```

An independent agent re-reads a sample and audits the scores against rules R1 to R7 (including R6, a demo
feature-dump scored as high demo craft). Overturned scores are corrected in the call_out files and
re-merged before aggregation.

**Gate:** the pass-rate is computed and the punch-list produced; report it honestly. **Degradation:** small
corpus means audit every call; a single model means the checker still runs blind and the pass-rate is a
consistency check.

---

## Phase 11: council (judgment)

```bash
python3 scripts/digest.py                 # builds analysis/council_digest.json
# run four blind SE seats + a synthesis seat (prompts/council.md) -> analysis/council_output.json
# also run prompts/diagnosis.md over the digest -> analysis/diagnosis.json (the specific, actionable
# org diagnosis that opens the report: names the concrete move missed on nearly every call + what to do)
```

Four seats blind to each other (technical-discovery diagnostician, demo-craft coach, POC/validation
strategist, enablement/competitive skeptic) then a synthesis seat.

**Gate:** four seats plus a synthesis exist, every finding traces to the digest, and the synthesis keeps
craft, the technical win, and the business outcome separate.

---

## Phase 12: aggregate and render (plumbing)

```bash
python3 scripts/aggregate.py     # rolls per-call atoms up to SE / deal / org -> analysis/report_data.json
python3 scripts/report_app.py    # renders one self-contained report.html
```

`aggregate.py` computes each explainer's role-weighted craft composite (NA excluded, low-confidence
down-weighted), and in separate blocks the Technical Win rate, the business outcomes, the demo-lens
rollup, and the quarter trend (only when the corpus spans at least `reporting.min_quarters` quarters).
Pages: Diagnosis, Engineers, Deals, Technical Win, Trust check, Trend, Council.

**Gate:** `report.html` opens with no network. Spot-check three composite cells: none folds in the
Technical Win or the business outcome.

---

## Phase 13: gate (plumbing)

```bash
python3 scripts/antislop_check.py "$AUDIT_WORKDIR"/report.html
```

Must exit 0. Show the operator the Diagnosis and Engineers pages and the confirmed role table, and report
the adherence pass-rate honestly. **Degradation:** none; the gate always runs.

---

## Verifying the method held (before handover)

- `len(call_out/call_*.json)` equals the in-scope call count, so every call was read.
- Every technical explainer on every scored call appears in a score block.
- No craft composite folds in the Technical Win or the business outcome; spot-check three cells.
- Three cited quotes are verbatim and attributed to the named explainer.
- One Technical Win and one post-mortem per in-scope deal with a call; every gap cites a quote.
- `antislop_check.py` exits 0 on the final report.
