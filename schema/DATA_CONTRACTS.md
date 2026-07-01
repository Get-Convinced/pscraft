# Data contracts

The judgment engine and the plumbing meet at these JSON shapes. Whatever runs the model (host subagents
or the API drivers) must produce exactly these, because the aggregator and the renderer read them. All
files live under the operator's working folder. PSCraft's unit of judgment is one call, and the scored
actor is the **technical explainer** on that call (role-inferred, title-agnostic).

**Three separate axes — never blended.** (1) the craft **composite** (the 1-5 rubric), (2) the
**Technical Win** state + gap ledger (the craft-side outcome), and (3) the **business outcome**
(won/lost/stalled, ARR, stage) when a CRM is present. The composite never folds in axis 2 or 3.

## canonical/ (produced by normalize.py from the operator's raw inputs)

- `transcripts.json` — array of `{call_id, date, title, recording_url, participants:[...], transcript|segments, ...}`.
  `transcript` is the full text (or `segments:[{speaker, text, ts}]`). Never summarized.
- `deals.json` (optional) — array of `{deal_id, account, stage, owner, se_owner, amount, created, close_date, competitor, technical_win_flag, meddic:{metric,economic_buyer,decision_process,decision_criteria,champion,pain,competition,paper}}`.
- `notes.json` (optional) — array of `{deal_id|deal_name, author, created, content}`.
- `stage_history.json` (optional) — array of `{deal_id|deal_name, from_stage, moved_to, modified_time}`.
- `poc_plans.json` (optional) — array of `{deal_id|account, source_doc, criteria:[{id, text, metric, target, status:"open|met|failed|unknown"}], timeline, owners:[...], raw_text}`. The `criteria` are the exit criteria POC_SCOPE is judged against; `raw_text` is the full document (read in full by a model in Phase 3.5, never keyword-parsed).
- `map_plans.json` (optional) — array of `{deal_id|account, source_doc, steps:[{step, owner, due, done}], raw_text}` (mutual action plans).
- `security_qs.json` (optional) — array of `{deal_id|account, framework:"SIG|CAIQ|VSQ|RFP|RFI|other", source_doc, items:[{area, question}], raw_text}`. Corroborating evidence for TECH_OBJ (what security/integration concerns the buyer raised in writing).
- `solution_designs.json` (optional) — array of `{deal_id|account, source_doc, raw_text}`. Corroborating evidence for SO_SUBSTANCE / SO_DESIGN.
- `se_platform.json` (optional) — array of `{deal_id|account, se_owner, technical_win_flag, poc_status, eval_criteria, activity_count}`. A `technical_win_flag` here is a CLAIM until a call corroborates it.

## analysis/ intermediate (produced by the plumbing)

- `opp_index.json` (link.py) — the deal-units: `{unit_index, account, deal_ids, in_scope_call_ids, in_scope_call_count, outcome, arr, stage, competitor}`.
- `roles.json` (role inference, a judgment phase) — `{<norm_name>: {name, is_org_rep, archetype, kind, seniority, seniority_inferred:bool, is_technical_explainer:bool}}`.
- `call_company.json` (link.py + naming judgment) — per call: `{<call_id>: {org_participants:[...], technical_explainers:[<norm_name>], one_line, se_stage:"intro_qualify|tech_discovery|tailored_demo|poc_pov|tech_validation|proposal_negotiation", bucket, call_status, transcript_quality}}`.

## analysis/call_out/call_<id>.json (one per in-scope call — the scoring atom)

```
{call_id, unit_index, account, date, title, recording_url, se_stage,
 explainers:[{rep_key, rep_name, archetype, kind, composite,
        scores:{<DIM_ID>:{score:1-5|"NA", confidence:"high|medium|low", why, quote, evidence}},   // evidence = the minimal self-contained verbatim exchange (speaker-labelled) that makes the score self-evident without the recording
        demo_lenses:{demo2win_tell_show_tell, great_demo_last_thing_first, anti_feature_dump, persona_tailoring}|null,
        gap_contributions:[{gap, status:"addressed_written|addressed_verbal|acknowledged_open|ignored", quote}],
        failure_points:[{label, dim, buyer_quote, rep_quote, why}],
        signature:{label, dim, quote, why}|null,
        buyer_reaction:{state, evidence}}]}
```
Produced by filling `prompts/call_score.md`. `composite` is added by the plumbing (weighted mean over
non-NA dims), the model returns the rest. `demo_lenses` is present only when DEMO_CRAFT was scored (the
per-lens read of the demo). `gap_contributions` feed the deal-level Technical Win gap ledger. One file
per in-scope transcript (the read-every-call invariant). Note the key is `explainers`, not `reps`.

## analysis/technical_win/deal_<unit>.json (one per deal — the craft-side outcome)

```
{unit_index, account,
 technical_win_state:"won_written|won_verbal|in_validation|lost_technical|not_reached|na",
 confidence, reached_on:{date, call_id, quote}|null,
 gap_ledger:[{gap, raised_by, status:"addressed_written|addressed_verbal|acknowledged_open|ignored", evidence:{call_id, quote}}],
 platform_claim:{flagged:bool, corroborated:bool, note}|null,
 business_outcome:{outcome, arr, stage}}
```
Produced by filling `prompts/technical_win.md`. The `technical_win_state` and the `business_outcome` are
BOTH reported beside the craft composite and NEVER folded into it. A Technical Win requires no `ignored`
blocking gap.

## analysis/postmortem/deal_<unit>.json (one per deal)

```
{unit_index, account, technical_win_state, business_outcome, arr,
 headline, arc, lost_conviction:{date, moment, why}|null, why_hold,
 stall_archetype, coachable, one_change,
 poc_arc:{criteria_defined:bool, criteria_met, criteria_failed, exit_written:bool},
 crm_check:[{field, crm_value, status:"observed|claimed|contradicted|absent", evidence}]}
```
Produced by filling `prompts/postmortem.md`. `crm_check` includes the technical_win_flag: a CRM/platform
technical-win claim that no call corroborates is `claimed`, not `observed`.

## analysis/adherence_calls/check_<id>.json (maker-checker, sampled calls)

```
{call_id, account, date, note,
 explainers:[{rep_name, verdict:"pass|minor|major",
        violations:[{rule:"R1..R7", dim, detail}],
        rescore:[{dim, maker, checker, why}]}]}
```
Produced by filling `prompts/adherence_check.md`. `merge_scores.py` rolls these up into `analysis/adherence.json`.

## analysis/council_output.json (one, the judgment layer)

```
{seats:[{seat, findings:[{claim, evidence, severity}], answer_why_deals_stall_technically,
         answer_what_ses_miss, answer_demo_quality, answer_one_change}],
 synthesis:{consensus:[...], tensions:[...], ranked_changes:[{change, rationale, expected_effect}], craft_vs_outcome_note}}
```
Produced by filling `prompts/council.md` over `analysis/council_digest.json` (built by `digest.py`). The
four SE seats: technical-discovery diagnostician, demo-craft coach, POC/validation strategist,
enablement/competitive skeptic.

## analysis/report_data.json (produced by aggregate.py; the only input to report_app.py)

`{org{...,adherence,council}, calls[], deals[], explainers[], quarters[], dims, dim_names, dim_groups, groups, demo_lenses}`.
Numbers here are aggregates; the per-call qualitative detail lives in `calls[].explainers[]`. `explainers[]`
carries each technical explainer's composite, per-dim spread, seniority bar, Technical Win record, and
(separate) business outcomes. `quarters[]` is present only when the corpus spans >= config.reporting.min_quarters
distinct quarters (QoQ trend); otherwise it is empty and the trend page is hidden with a caveat. The renderer
is self-contained: `report_app.py` reads this and writes one `report.html`.
