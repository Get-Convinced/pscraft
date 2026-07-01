<!--
TEMPLATE: SE-artifact document ingest (judgment reading, structure-preserving). ONE task per document.
A model reads ONE artifact document IN FULL and returns a structured canonical record. This is judgment,
not keyword scraping: the model reads every word and preserves the full text in raw_text so nothing is
lost. Emits into canonical/poc_plans.json | map_plans.json | security_qs.json | solution_designs.json
depending on {{DOC_KIND}}. See schema/DATA_CONTRACTS.md.

Placeholders:
  {{DOC_KIND}}     one of: poc | map | security | design
  {{DEAL_HINT}}    the deal/account this document belongs to, if the operator said ("account: X; deal_id: Y"), or "(unknown; infer the account from the document)"
  {{SOURCE_DOC}}   the file name (echo it back as source_doc)
  {{DOC_TEXT}}     the FULL extracted text of the document
-->

You read ONE {{ORG_OPTIONAL}}presales artifact document IN FULL and return a structured record. Read
every word. Do not summarize away detail; preserve the complete text in raw_text. You are turning a
document into a canonical shape the audit can join and cite, not judging anyone.

Document kind: {{DOC_KIND}}
Deal/account hint: {{DEAL_HINT}}
Source file: {{SOURCE_DOC}}

Return JSON for the matching kind:

If {{DOC_KIND}} == "poc"  (a POC / POV plan or success-criteria doc):
{
  "kind":"poc","deal_id":"<or null>","account":"<the customer this is for>","source_doc":"{{SOURCE_DOC}}",
  "criteria":[{"id":"<c1..>","text":"<the exit/success criterion, verbatim or lightly cleaned>","metric":"<the measure, or ''>","target":"<the pass target, or ''>","status":"open|met|failed|unknown"}],
  "timeline":"<the stated POC timeline/dates, or ''>",
  "owners":["<named owners on either side, or empty>"],
  "raw_text":"<the FULL document text>"
}

If {{DOC_KIND}} == "map"  (a mutual action plan / close plan):
{
  "kind":"map","deal_id":"<or null>","account":"<customer>","source_doc":"{{SOURCE_DOC}}",
  "steps":[{"step":"<the action>","owner":"<who owns it, or ''>","due":"<date, or ''>","done":true}],
  "raw_text":"<the FULL document text>"
}

If {{DOC_KIND}} == "security"  (a security questionnaire / RFP / RFI: SIG, CAIQ, VSQ, etc.):
{
  "kind":"security","deal_id":"<or null>","account":"<customer>","source_doc":"{{SOURCE_DOC}}",
  "framework":"SIG|CAIQ|VSQ|RFP|RFI|other",
  "items":[{"area":"<the control/topic area, e.g. data residency, SSO, encryption>","question":"<the question asked, verbatim or lightly cleaned>"}],
  "raw_text":"<the FULL document text>"
}

If {{DOC_KIND}} == "design"  (a solution-design / architecture doc):
{
  "kind":"design","deal_id":"<or null>","account":"<customer>","source_doc":"{{SOURCE_DOC}}",
  "summary":"<one factual paragraph of what the design proposes>",
  "raw_text":"<the FULL document text>"
}

Rules:
- READ EVERY WORD. raw_text must contain the complete document text (not a summary). The audit later
  cites it, so nothing may be dropped.
- Extract structure faithfully. A POC criterion is a thing the customer must see to accept the solution;
  capture its metric and pass target when stated, else leave ''. Do not invent criteria that are not in
  the document.
- account: infer the customer this document is for from its content if the hint is unknown. Never invent
  a deal_id; leave null and let the plumbing join by account.
- Do NOT judge or score. This is ingestion. If the document is empty or unreadable, return the shape with
  empty lists and raw_text as whatever text exists.
- Plain prose in any summary field, no em-dash or en-dash, no buzzwords. Return only the JSON.

THE DOCUMENT (read it in full):
{{DOC_TEXT}}
