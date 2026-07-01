# Subskill — intake (Phase 1)

You take the operator's data folder, work out what is actually in it, and write a manifest that the
rest of the run reads. You do not parse transcripts for meaning here, you do not score anything, and
you do not normalize yet. You classify files and record what is present. The normalizer
(`scripts/normalize.py`, Phase 3) does the parsing; it reads the manifest you write.

The one hard rule: **transcripts are required, everything else is optional and never blocks.** A run
with transcripts only must succeed. When the optional inputs are absent the pipeline degrades to a
craft-only audit later, and that is fine.

## Input

A single argument: the path to the operator's data folder (the skill's `argument-hint`). If the
operator did not give one, ask for it once. Resolve it to an absolute path. If it does not exist or
is empty, stop and say so plainly.

You also have a working folder for this run (`<workdir>`, created in Phase 0). The manifest you write
goes there, not in the operator's data folder.

## What to do

### 1. Discover every file

Walk the data folder recursively. List each file with its path, extension, and size. Ignore obvious
noise (`.DS_Store`, `Thumbs.db`, empty files, lock files, anything zero bytes).

### 2. Classify each file by inspecting it

Open each file and read enough of it to decide what it is. You are a model: judge by content, not by
filename alone. A file named `export.csv` could be deals or notes or stage history; a `.json` could
be a Read.ai transcript or a generic deal dump. Decide each file into exactly one of these buckets,
and also record the detected **format** so the normalizer knows which parser to use.

| bucket | what it is | typical formats |
|---|---|---|
| `transcript` | a single call or demo recording: speaker turns, a meeting header, attendees | Read.ai markdown/json, Gong, Chorus, Fireflies, Otter, Zoom VTT, plain text, generic JSON array of turns |
| `crm_deals` | one row per opportunity/deal: account, owner, SE owner, stage, amount, competitor, a technical-win flag, maybe MEDDIC columns | CSV, XLSX, JSON |
| `crm_notes` | free-text notes attached to deals: author, date, content, a deal reference | CSV, XLSX, JSON |
| `stage_history` | one row per stage change: a deal reference, from-stage, to-stage, a timestamp | CSV, XLSX, JSON |
| `se_platform` | a Vivun / Prelay / Cuvama export: SE owner, technical-win flag, POC status, evaluation criteria, activity | CSV, XLSX, JSON |
| `poc_doc` | a POC / POV plan or success-criteria doc: the exit criteria a proof is judged against | pdf, docx, md, txt |
| `map_doc` | a mutual action plan / close plan: dated steps with owners | pdf, docx, md, txt |
| `security_doc` | a security questionnaire or RFP/RFI (SIG, CAIQ, VSQ): the buyer's written technical concerns | xlsx, docx, pdf |
| `design_doc` | a solution-design or architecture doc | pdf, docx, md, txt |
| `company_doc` | operator's own product/competitor/pitch material to fold into company research | pdf, docx, md, txt, pptx |
| `unknown` | you genuinely cannot tell | any |

The four SE-artifact doc buckets (`poc_doc`, `map_doc`, `security_doc`, `design_doc`) are read IN FULL by a model in Phase 3.5 (`prompts/poc_ingest.md`), not parsed by keyword. Place them under `raw/poc`, `raw/map`, `raw/security`, `raw/design` respectively so the doc-ingest pass and `collect_artifacts` find them.

How to tell them apart:

- **transcript vs CRM export.** A transcript is one conversation: it has speaker labels and turns, or
  WebVTT cue blocks, or a meeting header (date, attendees, recording link). A CRM export is tabular:
  many rows, each a deal/note/stage-change, with column headers. If a `.json` has a `transcript`
  key or a `turns`/`segments` array, it is a transcript; if it is an array of deal-shaped objects, it
  is a CRM export.
- **deals vs notes vs stage_history** (all tabular). Read the header row. Columns like
  *Account / Owner / Stage / Amount / ARR / Close Date* mean `crm_deals`. A long free-text *Content /
  Note* column with a deal reference means `crm_notes`. Columns naming a *from-stage* and a *to-stage*
  (or *Moved To* / *Stage Duration* / *Modified Time*) mean `stage_history`. When one export bundles
  several of these as separate sheets or files, record each separately.
- **company_doc.** A pitch deck, a one-pager, a product PDF, a competitor sheet. Not a call, not a
  table of deals. Hand these to company research (Phase 2), not the normalizer.

For each transcript file, also note the detected vendor/format (`readai_json`, `readai_md`, `gong`,
`fireflies`, `otter`, `zoom_vtt`, `plain_text`, `markdown`, `generic_json`) so the normalizer can
dispatch. If a whole directory is one vendor, you can record the directory once with a file count
rather than every file, but the transcript count must be exact.

### 3. Transcripts are required

Count the `transcript` files. If there are **none**, stop. Tell the operator the audit needs call
transcripts and there are none in the folder, name the formats the skill reads (Read.ai, Gong,
Fireflies, Otter, Zoom VTT, plain text, markdown, generic JSON), and ask them to point at the right
folder. Do not proceed to research or scoring without transcripts.

### 4. Ask once for the optional inputs

After classifying, look at what optional buckets are missing. Ask the operator **one** consolidated
question: do they have any of these that were not in the folder? Make clear each is optional and what
each one buys:

- **CRM deal export** turns the craft scores into a deal-by-deal audit, a funnel, the business outcome,
  and a CRM-vs-call trust check. Without it the audit is craft-only (still useful).
- **POC / POV success-criteria docs** give the exit criteria POC scoping is judged against.
- **Security questionnaires** (SIG / CAIQ / VSQ / RFP / RFI) show the buyer's written technical concerns.
- **SE-platform export** (Vivun / Prelay / Cuvama) adds a technical-win flag and POC status, checked
  against the calls.
- **Mutual action plans, solution designs, rep notes** add corroborating evidence between calls.
- **Company docs** sharpen the product, competitor, and security context the scorer grounds on.

If they have a file, take the path and re-classify it into the manifest. If they have nothing, say so
and move on. **Never loop or block on this** — one ask, then continue with whatever is present.

### 5. Write the manifest

Write `<workdir>/intake.json`. This is the single record of what Phase 3 will normalize. Shape:

```json
{
  "data_folder": "/abs/path/the/operator/gave",
  "as_of_date": "YYYY-MM-DD",
  "transcripts": {
    "present": true,
    "count": 137,
    "files": [
      {"path": "/abs/.../2025-06-16_lake-trans.md", "format": "readai_md", "bytes": 41233},
      {"path": "/abs/.../calls", "format": "readai_md", "is_dir": true, "count": 136}
    ]
  },
  "crm_deals":     {"present": true,  "files": [{"path": "/abs/.../deals.csv",   "format": "csv"}]},
  "crm_notes":     {"present": true,  "files": [{"path": "/abs/.../notes.csv",   "format": "csv"}]},
  "stage_history": {"present": false, "files": []},
  "se_platform":   {"present": false, "files": []},
  "poc_docs":      {"present": true,  "files": [{"path": "/abs/.../poc",    "is_dir": true}]},
  "map_docs":      {"present": false, "files": []},
  "security_docs": {"present": false, "files": []},
  "design_docs":   {"present": false, "files": []},
  "company_docs":  {"present": true,  "files": [{"path": "/abs/.../onepager.pdf","format": "pdf"}]},
  "unknown":       [{"path": "/abs/.../weird.bin", "reason": "could not classify"}],
  "notes_for_operator": "Short plain-language summary of what was found and what is missing."
}
```

Rules for the manifest:

- `transcripts.present` must be `true` or you should have stopped at step 3.
- Set `present: false` and `files: []` for any optional bucket that has nothing. The normalizer keys
  off `present`, so a missing bucket means no `deals.json` / `notes.json` / `stage_history.json` gets
  written, and the pipeline degrades cleanly.
- Every transcript file (or directory-with-count) carries a `format` so `normalize.py` can dispatch.
- Paths are absolute.
- `company_docs` are recorded for Phase 2 (company research); the normalizer ignores them.

### 6. Hand off

Print a short summary for the operator: how many transcripts, what optional inputs are present, what
is missing and what that costs the audit. Then say the next step is normalization (Phase 3), which
will need a column mapping for any CRM/notes/stage export (produced from `prompts/crm_mapping.md`).

## Boundaries

- You classify and record. You do not parse transcript text for meaning, you do not read a call to
  judge it, you do not score. That is later phases.
- You never invent inputs. If a bucket is absent, it is absent; record it as such.
- Keep prose plain. No em-dashes, no en-dashes, no buzzwords.
