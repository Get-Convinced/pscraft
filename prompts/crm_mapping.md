# Prompt — CRM / SE-platform column mapping (one export at a time)

You map the real column headers of one tabular export onto the skill's canonical fields. The normalizer
(`scripts/normalize.py`) is pure plumbing: it cannot guess that a column called `Opp Owner` is the deal
owner or that `Amt (USD)` is the ARR. You make that call once, it applies it to every row. You never
read the rows for meaning, you only read enough to recognize what each column holds.

This runs once per CRM/notes/stage/SE-platform file the intake manifest marked `present`. The export's
`kind` (`crm_deals`, `crm_notes`, `stage_history`, or `se_platform`) tells you which output block to fill.

## Input

You are given, for one file: its `kind`, the header row (column names), and 3 to 5 sample rows so you can
recognize what each column contains.

## Output

Return JSON exactly in this shape. Fill only the block matching this file's `kind`; emit the others as
empty objects or omit them. Every canonical field maps to a **source column name** (a string in the
header) or `null`. Never invent a column name that is not in the header.

```json
{
  "kind": "crm_deals",
  "deals": {
    "deal_id":            "<source column or null>",
    "deal_name":          "<source column or null>",
    "account":            "<source column or null>",
    "owner":              "<source column or null>",
    "se_owner":           "<the Sales Engineer / Solution Engineer / Presales owner column, or null>",
    "stage":              "<source column or null>",
    "amount_arr":         "<source column or null>",
    "amount_otc":         "<source column or null>",
    "created_date":       "<source column or null>",
    "close_date":         "<source column or null>",
    "products":           "<source column or null>",
    "region":             "<source column or null>",
    "competitor":         "<the incumbent/primary-competitor column, or null>",
    "technical_win":      "<a technical-win flag column, or null>",
    "next_step":          "<source column or null>",
    "meddic_metric":            "<source column or null>",
    "meddic_economic_buyer":    "<source column or null>",
    "meddic_decision_process":  "<source column or null>",
    "meddic_decision_criteria": "<source column or null>",
    "meddic_champion":          "<source column or null>",
    "meddic_pain":              "<source column or null>",
    "meddic_competition":       "<source column or null>",
    "meddic_paper_process":     "<source column or null>"
  },
  "notes": {
    "deal_id":      "<source column or null>",
    "deal_name":    "<source column or null>",
    "author":       "<source column or null>",
    "created_date": "<source column or null>",
    "content":      "<source column or null>"
  },
  "stage_history": {
    "deal_id":      "<source column or null>",
    "deal_name":    "<source column or null>",
    "from_stage":   "<source column or null>",
    "to_stage":     "<source column or null>",
    "duration_days":"<source column or null>",
    "moved_at":     "<source column or null>"
  },
  "se_platform": {
    "deal_id":            "<source column or null>",
    "account":            "<source column or null>",
    "se_owner":           "<source column or null>",
    "technical_win_flag": "<source column or null>",
    "poc_status":         "<source column or null>",
    "eval_criteria":      "<source column or null>",
    "activity_count":     "<source column or null>"
  }
}
```

## What each canonical field means

**deals** — `deal_id` is the stable opportunity id (the join key; null falls back to `deal_name`).
`account` is the buying company. `owner` is the deal owner; `se_owner` is the assigned Sales/Solution
Engineer if a separate column exists. `stage` is the raw pipeline label, verbatim (do not map to a rung
here). `amount_arr`/`amount_otc` are recurring/one-time amounts. `competitor` is the named incumbent or
alternative. `technical_win` is any column flagging that the deal was technically won (a claim until a
call proves it). The eight `meddic_*` slots map any column clearly holding that content; most exports
carry only a few, leave the rest `null`.

**notes** — `content` is the note body (load-bearing; if absent the file is not really notes). The rest
reference the deal and the author/date.

**stage_history** — `from_stage`/`to_stage` are the transition; `moved_at` its timestamp; `duration_days`
days in the prior stage if recorded.

**se_platform** (a Vivun/Prelay/Cuvama-style export) — `technical_win_flag`, `poc_status`, and
`eval_criteria` capture the platform's own view of the evaluation; `activity_count` is SE touches.
Everything here is a CLAIM the calls must corroborate.

## Rules

- **Map only to columns that exist.** Every value is a literal header string or `null`.
- **Tolerate missing fields.** A sparse export is normal; mark absent fields `null`. Only `content` (for
  notes) is load-bearing.
- **Keep raw labels raw.** Do not normalize stage names, dates, or amounts; the normalizer parses and the
  linker maps stages. You only point at columns.
- **One file, one block.** Set `kind` to this file's kind and fill that block only.
- Return only the JSON.
