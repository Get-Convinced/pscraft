<!--
TEMPLATE: per-deal Technical Win inference (the craft-side OUTCOME anchor). ONE task per deal.
Fill the {{PLACEHOLDERS}} and run as one judgment task. Returns ONE JSON object matching the technical_win
shape in schema/DATA_CONTRACTS.md (analysis/technical_win/deal_<unit>.json). The Technical Win is an
OUTCOME, reported beside the craft composite and the business outcome, and NEVER folded into either.

Placeholders:
  {{ORG}}            seller org name
  {{ACCOUNT}}        the prospect account
  {{POC_CRITERIA}}   the deal's agreed POC/POV exit criteria if a doc exists ("- <criterion> [metric/target]"), or "(no POC criteria doc)"
  {{PLATFORM_FLAG}}  any CRM/SE-platform technical-win flag on file ("flagged: yes/no; note"), or "(no flag on file)"
  {{GAP_FINDINGS}}   the gap_contributions the per-call scorer already collected across this deal's calls, or "none"
  {{BUSINESS_OUTCOME}} the deal's business outcome if a CRM exists ("outcome: won|lost|stalled; arr; stage"), or "(no CRM)"
  {{TRANSCRIPTS}}    the deal's calls, in date order, read in full (cap the total length)
-->

You decide, for the {{ORG}} deal with {{ACCOUNT}}, whether a TECHNICAL WIN was reached, and you build
the gap ledger that justifies it. Read the calls in full.

DEFINITION (apply it strictly): a Technical Win is reached when the prospect judges the solution
technically SUPERIOR to the alternatives AND the specific gaps or concerns the prospect voiced were
recognized and addressed, with written confirmation where available. A Technical Win requires no
IGNORED blocking gap.

STAY SUSPICIOUS OF FLAGS. A CRM or SE-platform "technical win" checkbox is a CLAIM until a call
corroborates it. Only mark a state above "not_reached" if the CALLS (or a written confirmation the calls
reference) support it. If the platform flag says won but no call moment shows the prospect judging the
solution superior with their gaps addressed, mark platform_claim.corroborated false and set the state
from what you actually observed.

POC/POV exit criteria on file: {{POC_CRITERIA}}
Platform/CRM technical-win flag: {{PLATFORM_FLAG}}
Gap findings already collected per call: {{GAP_FINDINGS}}
Business outcome (kept SEPARATE; never let it decide the technical win): {{BUSINESS_OUTCOME}}

Return JSON:
{
"technical_win_state":"won_written|won_verbal|in_validation|lost_technical|not_reached|na",
"confidence":"high|medium|low",
"reached_on":{"date":"<call date>","call_id":"<id>","quote":"<verbatim moment the prospect judged it superior / confirmed the criteria were met>"}  (or null),
"gap_ledger":[{"gap":"<a technical/security/integration concern the prospect voiced>","raised_by":"<prospect role/name>","status":"addressed_written|addressed_verbal|acknowledged_open|ignored","evidence":{"call_id":"<id>","quote":"<verbatim>"}}],
"platform_claim":{"flagged":true,"corroborated":false,"note":"<one line: does a call back the flag?>"}  (or null if no flag),
"business_outcome":{"outcome":"<won|lost|stalled|unknown>","arr":"<or ''>","stage":"<or ''>"}
}

Rules:
- The gap_ledger is the spine. List every distinct technical/security/integration gap or concern the
  PROSPECT voiced across the deal, and its final status. Merge duplicates across calls; keep the latest
  status. An "ignored" blocking gap means the state cannot be a win.
- won_written only if a call references written confirmation (an email, a signed criteria doc, a
  procurement note) that the solution was accepted as technically superior. won_verbal if the prospect
  clearly said so on a call but nothing written is referenced. in_validation if a POC is underway and
  criteria are not yet all met. lost_technical if the prospect judged a competitor superior or a
  blocking gap went unaddressed. not_reached if it simply never got there. na if the deal never reached
  a technical evaluation (too early, disqualified).
- reached_on.quote and every gap evidence quote MUST be verbatim from a call.
- CRAFT-VS-OUTCOME: the Technical Win is an OUTCOME. Do not reward or punish the explainer's craft here;
  that is the rubric's job. A deal can have strong craft and no technical win, or a technical win and a
  lost deal. Keep them separate.
- Plain prose, no em-dash or en-dash, no buzzwords. Return only JSON.

THE CALLS:
{{TRANSCRIPTS}}
