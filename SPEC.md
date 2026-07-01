# PSCraft — build spec & status

PSCraft (PreSales Craft) audits a B2B **presales / sales-engineering** team from real call and demo
transcripts and produces one interactive HTML report. It is a sibling of **call-craft** (which audits
AE/closer calls): it reuses call-craft's plumbing and hermetic engine, and rewrites the judgment layer
to score presales craft. **Separate skill, separate repo — it never touches call-craft.**

Grounded in a deep-research pass on how SEs are scored/coached (PreSales Collective, John Care's
"Technical Win", Consensus/Derrek Young/Vivun competency scorecards, Demo2Win / Great Demo!). Key
finding: the field already separates technical **craft** from commercial **outcome** and names the
craft-side outcome the **Technical Win** — so PSCraft's craft-vs-outcome split is validated, and the
per-transcript scoring is the novel layer PSCraft pioneers.

## Locked decisions (from the operator)

1. **Scored actor = the technical explainer on each call**, role-inferred and title-agnostic. Usually
   the SE/SC/SA; when a seller (AE) carries the technical explaining, they are scored in the SE lane
   for those moves and recognized for it. A participant who did not do the technical explaining is
   context, not scored.
2. **Technical Win (model-inferred)** = the prospect judges the solution technically superior AND the
   specific gaps/concerns they voiced were recognized and addressed, with written confirmation where
   available. Reported separately from craft and from revenue; never folded into the composite.
3. **Rubric = 10 craft spokes**: 7 SE dimensions (TD_DEPTH, DEMO_CRAFT, POC_SCOPE, TECH_OBJ, COMPETE,
   CHAMPION, STATUS_QUO) + 3 retained technical-precision spokes (SO_ACCURACY, SO_SUBSTANCE, KN_GAP).
4. **Demo craft = all methodologies** (Demo2Win Tell-Show-Tell, Great Demo! "Do the Last Thing First",
   anti-feature-dump "So What?", persona tailoring). Scored and reported per-lens (all angles), not one
   number.
5. **Benchmarks set by us, LLM reasoning does the heavy lifting:**
   - Seniority bars (expected composite): Associate 3.0 · Mid 3.25 · Senior 3.5 · Principal 3.75 ·
     Lead/Manager 3.75. Level model-inferred when unset; no data => relative-to-cohort, no absolute bar.
   - Demo/"So What?" calibration: a shown capability earns credit only if tied to a discovered pain and
     it states a business impact; screen-share narration ("here you can see…") is never credit by itself.
6. **Reporting levels: call · SE · deal are compulsory; quarter/QoQ is model-inferred, only if >= 2
   quarters of calls are present** (else skipped with a caveat).
7. **Plumb ALL artifacts (no v2):** transcripts (compulsory) + CRM, notes, POC/POV success-criteria
   docs, MAPs, security questionnaires (SIG/CAIQ/VSQ/RFP/RFI), SE-platform exports (Vivun/Prelay/Cuvama),
   demo recordings, solution-design docs. Docs are read in full by a model, never keyword-parsed.
8. **Stage-expectation map authored** (the NA logic) over 6 SE stages: intro_qualify, tech_discovery,
   tailored_demo, poc_pov, tech_validation, proposal_negotiation. Model infers each call's stage.

## Inherited from call-craft (unchanged principles)

Read every call in full; scripts are plumbing only (never score/classify by keyword); craft separate
from outcome; incomplete corpus => NA-not-a-low-mark; CRM/platform suspect until a call proves it;
stage-aware NA; the craft evidence quote is the explainer's own words; no slop in authored prose;
hermetic (ships no keys/data); host-agent engine by default, API optional.

## The three axes (never blended)

1. Craft composite (1-5 weighted mean of applicable spokes).
2. Technical Win state + gap ledger (craft-side outcome).
3. Business outcome (won/lost/stalled, ARR, stage) when CRM present.

## Build status

Legend: [x] done · [~] in progress · [ ] todo. Rule: read every call-craft source file in FULL before
porting it (no grep/regex).

- [x] Skeleton: copied call-craft plumbing into `pscraft/`, git re-initialized
- [x] `schema/rubric.template.json` — SE rubric (10 spokes, stage_expectations matrix, demo_calibration, technical_win def, role archetypes, seniority bars)
- [x] `schema/config.template.json` — artifact-extended (POC/MAP/security/design/SE-platform ingest, SE stages, technical_win + reporting blocks)
- [x] `schema/DATA_CONTRACTS.md` — extended (new canonical files, `explainers[]`, technical_win/, demo_lenses, quarters, three-axis separation)
- [x] `schema/company_context.template.md` — competitive-technical, security/compliance, POC-norms sections
- [x] `SKILL.md` — SE orchestrator (technical-explainer scoring, artifact phases, technical-win phase); skill registered as `/pscraft`, quoted frontmatter (npx-skills-add ready)
- [ ] `README.md`, `NOTICE`
- [ ] `RUNBOOK.md` — add Phase 3.5 (artifact ingest), SE stages, technical-win phase, QoQ; adapt every phase
- [x] `prompts/` — all 12 done: rewrote role_inference (technical-explainer), call_score (SE rubric + demo lenses + gap ledger), account_naming (+se_stage +technical_explainers), postmortem, council (4 SE seats), adherence_check (R1-R7 incl demo So-What), crm_mapping (+se_platform), config_generate, research_plan, research_synthesize; NEW technical_win + poc_ingest
- [ ] `subskills/` — intake (all artifacts), company-research (technical/competitive/security), add technical-win + poc subskills; adapt score-calls, adherence, council, postmortem, account-naming
- [ ] `scripts/` — extend normalize (POC/MAP/security/design/SE-platform + doc extraction), link (SE stage), aggregate (3 axes + quarters), report_app (SE pages + demo lenses + technical-win + QoQ), digest, build_tasks, merge_scores, lib/*
- [ ] `examples/` — SE synthetic corpus (transcripts + POC doc + CRM + security Q)
- [ ] `docs/guide.html` — SE version
- [x] **Scripts SE-adapted** (score_calls, aggregate, normalize, merge_scores, report_app) + fixed two latent call-craft bugs (aggregate read notes/deals unconditionally; per-call archetype not threaded into the rep rollup)
- [x] **End-to-end run PASSES** on a synthetic 2-deal SE corpus (`scratchpad/pscraft-run`): normalize -> link (gate green, 4/4) -> merge -> aggregate -> report_app -> anti-slop exit 0. Verified: technical-explainer scoring, Dana (AE) scored as seller-doing-technical, 3-axis separation, Technical Win gap ledgers + uncorroborated-flag trust check, demo lenses, quarters correctly suppressed at 1 quarter. Sample report: `~/Downloads/pscraft-sample-report.html`.
- [x] Fresh SKILL.md frontmatter (name: pscraft, quoted description) so `npx skills add` works
- [x] `build_tasks.py` technical_win + doc-ingest phases + postmortem SE placeholders (all phases smoke-tested)
- [x] `RUNBOOK.md` (13 SE phases), `README.md`, `NOTICE`, `docs/guide.html` (fresh SE guide), digest.py technical-win summary, link.py stat
- [x] `examples/synthetic/` SE corpus shipped (4 transcripts, CRM, POC plan, security questionnaire, example config + context, README)
- [x] All 7 `subskills/` adapted (intake asks for SE artifacts; company-research SE sections; council SE seats; adherence 7 rules; naming technical_explainers+se_stage; postmortem/score-calls relabeled)
- [x] **FINAL: full pipeline green** (normalize -> link -> merge -> digest -> aggregate -> report_app -> anti-slop exit 0), all scripts compile clean. **PSCraft is complete.**

## Known follow-ups (not blockers)
- Not yet a GitHub repo (`Get-Convinced/pscraft`) — local skill only; publish when ready.
- SE outcomes are attributed by CRM owner + se_owner; a purpose-built SE-attribution model could be richer.
- `lib/audit.py` docstring still says "call-craft" (harmless internal comment).

## Naming

Skill slug `pscraft`, command `/pscraft`, display "PSCraft". Repo (later): `Get-Convinced/pscraft`.
