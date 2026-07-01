# Prompt — generate config.json (once per run)

You write the run's `config.json`. Everything org-specific lives in this one file so the rest of the
skill stays company/CRM/stack agnostic. You fill it from the intake manifest (what inputs exist) and the
short company-research summary. The shape and field docs are in `schema/config.template.json`; produce a
complete config that validates against it.

## Input

- `<workdir>/intake.json` — the Phase 1 manifest: whether deals / notes / stage history / POC docs / MAPs
  / security questionnaires / solution designs / SE-platform export exist, the transcript count, the date
  range hint.
- The company-research summary from Phase 2 (or `company_context.md`): org name, domain(s), product
  one-liner, presales motion and roles, the competitive set, the security posture.
- If a CRM deals export exists, the **distinct raw stage labels** seen in it (the linker needs these for
  `stage_map`). If you do not have them yet, leave `stage_map` empty and note it gets filled later.

## Output

A single JSON object: the complete `config.json`. Match `schema/config.template.json` exactly. Drop the
`_doc`/`_example` helper keys. Fill:

```json
{
  "org_name": "<the selling org's name>",
  "product_oneliner": "<one plain sentence: what they sell, to whom, solving what>",
  "as_of_date": "<YYYY-MM-DD, the run date or the manifest's latest call date>",
  "org_domains": ["<email domain(s) of the selling org>"],

  "scope": { "date_from": null, "date_to": null, "sample_deal_ids": null },

  "stage_map": { },
  "stage_order": ["intro_qualify", "tech_discovery", "tailored_demo", "poc_pov", "tech_validation", "proposal", "negotiation", "won", "lost", "stalled"],

  "stalled_definition": { "derived_from": "auto", "stage_names": [], "inactivity_days": null },

  "technical_win": { "source": "inferred", "crm_or_platform_flag_column": null },

  "roles": { "overrides": [], "name_fixes": [] },

  "rubric": { "overrides": {} },

  "reporting": { "levels": ["call", "se", "deal"], "quarter_trend": "auto", "min_quarters": 2 },

  "min_calls_to_rank_se": 3,

  "caveats": [ ],

  "org_asr_aliases": [ ],
  "exclude_accounts": [ ],
  "account_aliases": [ ]
}
```

## How to fill each field

- **org_name / product_oneliner** — from research; one plain factual sentence for the one-liner.
- **as_of_date** — the run date, or the latest call date if you want "stalled / no recent activity"
  anchored to the corpus.
- **org_domains** — the email domain(s) of the selling org (how the pipeline splits internal explainers
  from external buyers). Include every domain; if research did not surface it, infer from recurring
  transcript-header emails and say it is inferred.
- **stage_map** — map each raw CRM stage label to a canonical PSCraft rung (`intro_qualify`,
  `tech_discovery`, `tailored_demo`, `poc_pov`, `tech_validation`, `proposal`, `negotiation`, `won`,
  `lost`, `stalled`). If you do not have the labels yet, leave `{}` and flag that the linker prints them.
  With no CRM, leave `{}` (the funnel is skipped, craft-only).
- **stage_order** — the default SE rung order is right for most orgs; reorder only if the motion differs.
- **technical_win** — leave `source: "inferred"` (a model reads the corpus and decides the state). Only
  set `crm_or_platform_flag_column` if a CRM/SE-platform export carries a technical-win flag you want
  cross-checked; the flag is a claim, never proof.
- **reporting** — leave `quarter_trend: "auto"` and `min_quarters: 2`: the QoQ trend renders only if the
  corpus spans at least two distinct quarters (inferred from call dates), else it is skipped with a
  caveat.
- **roles** — leave `overrides`/`name_fixes` empty; Phase 5 fills role overrides. Do not pre-guess people.
- **min_calls_to_rank_se** — default 3; lower to 2 only for a very small corpus.
- **caveats** — start with the three standing caveats (calls are one channel so absence is flagged not
  penalized; craft is separated from both the Technical Win and the business outcome; PSCraft scores the
  technical explainer whoever carried it). Add one line per missing optional input the manifest shows (no
  CRM = craft-only, no funnel; no POC docs = POC scoping judged from the calls alone; no SE platform = no
  flag cross-check; etc.). State the corpus size and date range. One plain sentence each.
- **currency** — discover it from the CRM amount column and how money is spoken on calls; set `symbol`,
  `code`, and `style` (`indian` only if amounts are in lakh/crore, else `short`).
- **org_asr_aliases** — common ASR mis-hearings of the org/product name, `{wrong, right}` style. `[]` if none.
- **exclude_accounts** — non-buying accounts to drop (the selling org itself, advisory firms, partners
  that are not the end customer, test accounts). `[]` if none.
- **account_aliases** — fold spelling/legal-suffix variants of one company onto a canonical name so an
  opportunity does not split across keys. `[]` otherwise.

## Rules

- Produce a **complete** config that validates against `schema/config.template.json`. Do not omit
  required keys; use empty/null defaults where you have nothing.
- Never fabricate org domains, stage labels, or accounts. Where you inferred a value, note it in `caveats`.
- The config must degrade with the inputs: transcripts only means the CRM/POC/SE-platform fields are empty
  and the caveats say craft-only.
- No em-dashes, no en-dashes, no buzzwords in any prose. Return only the JSON.
