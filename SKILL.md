---
name: pscraft
description: "Audit a B2B presales / sales-engineering team from their real call and demo transcripts and produce one interactive HTML report. Point it at a folder of transcripts (Read.ai, Gong, Chorus, Fireflies, Otter, or plain text) plus, optionally, a CRM deal export, rep notes, POC/POV success-criteria docs, mutual action plans, security questionnaires (SIG/CAIQ/VSQ/RFP/RFI), solution-design docs, and SE-platform exports (Vivun/Prelay/Cuvama). It researches the company off the web to build a grounded product, competitor, and security context, infers who carried the technical-explainer role on each call (title-agnostic: a seller who does the technical explaining is scored for it), reads every call in full, and scores that explainer across a presales rubric of the pressure moves a technical sale must make (technical discovery, tailored-demo craft, POC/POV scoping and exit-criteria control, technical and security objection handling, competitive technical displacement, champion enablement, defeating status-quo, plus technical accuracy, substance, and knowledge-gap handling). It infers a Technical Win per deal (the solution judged superior AND the prospect's voiced gaps recognized and addressed) and reports it separately from the craft score and from the business outcome. Demo craft is scored from multiple methodology lenses. Stage-aware: a late-stage move on an early call is NA, not a failure. It runs an independent maker-checker adherence pass and a four-seat consultant council, and renders a self-contained report (org diagnosis, per-SE radar with per-spoke explainers and demo-lens breakdowns, deal post-mortems, a Technical Win gap ledger, a CRM/platform-vs-call trust check, and a quarter-over-quarter trend when enough data exists). Craft is kept strictly separate from outcome. Hermetic and engine-agnostic: ships no keys and no data, runs the judgment as subagents using your own CLI's model by default, with an optional bring-your-own API backend. Company, CRM, and stack agnostic; everything org-specific is discovered or configured at run time."
argument-hint: "[<path-to-data-folder>]"
user-invocable: true
---

# PSCraft — orchestrator

You are auditing a B2B **presales / sales-engineering** organization from its real calls and demos and
producing one interactive HTML report. You are the **conductor**. The judgment (researching the company,
inferring who did the technical explaining, scoring calls, inferring the Technical Win, writing
post-mortems, the council) is done by **model agents you spawn**; the plumbing (normalizing inputs,
reading artifact docs into canonical shapes, joining calls to deals, aggregating numbers, rendering
HTML) is done by **deterministic Python scripts** in `scripts/` (stdlib only). You never score a call
yourself in one pass over the whole corpus, and a script never reads a transcript or a document for
meaning.

PSCraft scores the **technical explainer** on each call — the person who carried the technical
discovery, demo, POC, and objection load. Usually that is the SE/SC/SA; when a seller (AE) does the
technical explaining, they are scored in this lane for those moves and recognized for it. A participant
who did not do the technical explaining is context, not scored.

This file is the map. The per-phase procedure, gates, and degradation tiers are in **RUNBOOK.md** — read
it before you start. The locked design is in **SPEC.md**. Judgment templates are in **prompts/**,
subskills in **subskills/**, the engine contract in **engine/**, the calibration in
**schema/rubric.template.json**, and the output and config contracts in **schema/**.

## This skill is hermetic — keep it that way

It must run for anyone, with nothing of its author's. Never reach for an external service, MCP, key, or
dataset that the recipient would not have. The company context comes from **live web research and the
operator's own documents**, never a private knowledge base. No secrets are ever written into the skill;
operator keys live only in a gitignored `.env`. No customer data is ever committed; it lives in the
operator's working folder.

## The engine — host agents by default, API optional

Every judgment step is a **task**: a prompt template from `prompts/` filled with one unit of input (one
call, one deal, one document, one research target), returning validated JSON. How those tasks execute is
the only thing that varies by environment. Resolve it once at the start (`engine/README.md`):

- **Host-agent mode (default).** You are inside an agentic CLI (Claude Code, cowork, Codex, …). Run each
  task by **spawning a subagent**, and run independent tasks **in parallel** (batches sized to the
  host's limits). The model is whatever the host runs — no key needed. Prefer it whenever a subagent
  capability exists.
- **API mode (opt-in).** For very large corpora or headless runs, the operator sets an OpenAI-compatible
  endpoint + key in `.env`; the `scripts/*_via_api.py` drivers loop the same templates through
  `engine/llm.py` (provider switch: deepseek / openai / anthropic / local).

Either way the **output contract is identical** (`schema/DATA_CONTRACTS.md`), so the plumbing and the
report never care which engine ran.

## Non-negotiables (these define the method — never relax them)

1. **Every relevant call is read in full by a model.** No grep, keyword list, regex, or "read the top N"
   decides which calls matter, who is in them, or how the explainer performed. Scripts never read a
   transcript or a document for meaning. Verifiable: the number of calls handed to agents equals the
   number of in-scope canonical transcripts.
2. **Code is plumbing only.** Scripts parse files, read documents into canonical JSON via a model, join
   on ids, count, deduplicate, aggregate numbers a model already produced, and render HTML. A script
   never scores a call, classifies it by keyword, or decides who the technical explainer is.
3. **Score the technical explainer, title-agnostic.** On each call, the person who carried the technical
   explaining is scored on the SE rubric. A seller who did the technical work is recognized and scored
   for it (`seller-doing-technical`); a participant who did not is context, not scored.
4. **Three axes, never blended.** (a) the craft **composite** (the 1-5 rubric), (b) the **Technical
   Win** state + gap ledger (the craft-side outcome), (c) the **business outcome** (won/lost/stalled,
   ARR, stage) when a CRM is present. A strong explainer who reached a Technical Win on a deal later
   lost to price is **not** marked down. Never fold axis b or c into the composite.
5. **The corpus is incomplete — score what you can see, flag what you cannot.** Calls are one channel
   (async POC work, email, Slack, whiteboarding are absent). Where an expected move is simply **not
   visible**, score the dimension **NA with low confidence**, not a low mark. A move that IS visible but
   done badly (a feature-dump, a hand-waved security answer, a criteria-less POC) scores low.
6. **The CRM and the SE platform are suspect until proven on a call.** A MEDDIC field or a Technical-Win
   flag is real only if the explainer was seen earning it on a recording. An uncorroborated flag is a
   *claim*, not a fact. Tag it accordingly. A POC success-criteria document is authoritative for WHAT
   the criteria were, but the transcript decides whether the explainer scoped and controlled them.
7. **Stage-aware.** A move not yet due at a call's SE stage (POC exit-criteria on a first demo,
   competitive displacement with no competitor in play) is NA, not a failure. Use the deal arc and the
   rubric's `stage_expectations` matrix to judge what was due.
8. **The evidence quote for the explainer's craft must be the explainer's own words.** A buyer's
   objection is the setup, never the score. Read the whole turn: quote the explainer's reply.
9. **No slop in authored prose.** No em-dashes or en-dashes, no buzzword filler, in anything the model
   writes for the report. Verbatim quotes and source titles are exempt. `scripts/antislop_check.py`
   enforces this on the final HTML.

## Phases (the run, end to end)

Work top to bottom. Each phase has a gate in RUNBOOK.md; do not advance past a failed gate. Phases
marked **‖ parallel** fan out one task per unit.

0. **Resolve engine + working folder.** Pick host-agent vs API. Create the operator's `work/` tree.
1. **Intake** (`subskills/intake/`). Take the data-folder argument. Identify the transcripts (required).
   Ask the operator, once, for any optional inputs — CRM export, rep notes, stage history, POC/POV
   success-criteria docs, mutual action plans, security questionnaires, solution-design docs, SE-platform
   export, company docs. Prompt for them but never block. Record what is present.
2. **Company research** (`subskills/company-research/`). Disambiguate the entity, plan where the
   knowledge lives, **‖ fan out** a research swarm, fold in operator docs, and **synthesize**
   `company_context.md`: product, the technical buyer and champion, what a credible technical claim
   sounds like, the competitive **technical** differentiation, the security/compliance posture, and the
   POC/evaluation norms. This grounds the scorer.
3. **Normalize** (`scripts/normalize.py` + `prompts/crm_mapping.md`). Map transcripts and any CRM/notes/
   stage exports into the canonical model. Structure only, never meaning.
   **3.5 Ingest SE artifacts ‖** (`subskills/intake/` doc pass). A model reads each POC/POV doc, MAP,
   security questionnaire, and solution-design doc **in full** and emits `canonical/poc_plans.json`,
   `map_plans.json`, `security_qs.json`, `solution_designs.json`; `normalize.py` folds the SE-platform
   CSV into `se_platform.json`. Documents are read, never keyword-scraped.
4. **Config.** Generate `config.json`: org name, domains, scope, stage map (the SE rungs), technical-win
   source, reporting levels, exclusions, aliases.
5. **Technical-explainer roles ‖** (`prompts/role_inference.md`). For each person, and per call, infer
   who carried the technical-explainer role (title-agnostic), their kind (dedicated_se /
   seller-doing-technical), and seniority level (model-inferred if unset). Gate: operator eyeballs the
   role table.
6. **Name + Link + SE-stage** (`subskills/account-naming/` + `scripts/link.py`). Read each call to name
   the account, bucket it, flag quality, list the technical explainers present, and infer the **SE
   stage**. Then join calls to deals, build the funnel and stall pile, clear the conservation gate.
7. **Score calls ‖** (`prompts/call_score.md`). One task per in-scope call: read it in full, for each
   technical explainer return per-dimension scores (with the explainer's quote), the demo per-lens read
   when a demo occurred, and gap contributions. Collect with `scripts/merge_scores.py`.
8. **Technical Win ‖** (`prompts/technical_win.md`). One task per deal: infer the Technical Win state and
   build the gap ledger (each prospect-voiced gap: addressed-written / addressed-verbal / open /
   ignored), tag any platform/CRM technical-win claim as corroborated or not.
9. **Post-mortems ‖** (`prompts/postmortem.md`). One task per deal: the technical arc, where conviction
   was lost, the POC arc, the stall archetype, the one change, and the CRM/platform-vs-call check.
10. **Adherence (maker-checker) ‖** (`prompts/adherence_check.md`). An **independent** agent re-reads a
    sample, audits against the calibration (especially any low mark on absence, any high mark with no
    explainer quote, any feature-dump credited as demo craft), spot re-scores.
11. **Council** (`prompts/council.md`). Four blind SE seats (technical-discovery diagnostician,
    demo-craft coach, POC/validation strategist, enablement/competitive skeptic) + a synthesis seat.
12. **Aggregate + render** (`scripts/aggregate.py` → `scripts/report_app.py`). Roll the per-call atoms up
    to SE / deal / org, add the quarter trend when >= 2 quarters exist, then render one self-contained
    `report.html`.
13. **Gate** (`scripts/antislop_check.py`). Anti-slop must pass on the final HTML. Report the adherence
    pass-rate and the flagged calls honestly.

## Output

One file: `work/<run>/report.html` — hash-routed, no network, no external assets. Pages: Diagnosis,
Engineers (radar + per-spoke explainers + demo-lens reads + full per-call breakdowns), Deals
(post-mortems + POC arc), Technical Win (per-deal gap ledger), Trust check (CRM/platform-vs-call), Trend
(quarter-over-quarter, when present), and Council. Open in any browser.

Start by reading **RUNBOOK.md**.
