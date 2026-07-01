<!--
TEMPLATE: per-deal post-mortem (presales lens). ONE task per deal (a deal = its in-scope calls grouped).
Fill the {{PLACEHOLDERS}} and run as one judgment task. Returns ONE JSON object matching the postmortem
shape in schema/DATA_CONTRACTS.md (analysis/postmortem/deal_<unit>.json).

Placeholders:
  {{ORG}}            seller org name
  {{ACCOUNT}}        the prospect account
  {{SE_STAGE}}       current SE stage(s) for the deal, or "unknown"
  {{TECH_WIN}}       the Technical Win state already inferred for this deal (state + one line), or "(not inferred)"
  {{POC_CRITERIA}}   the deal's POC/POV exit criteria if a doc exists, or "(no POC criteria doc)"
  {{CRM_MEDDIC}}     the MEDDIC fields the CRM holds ("field: value | ..."), or "(CRM MEDDIC empty)"
  {{STAGE_HISTORY}}  stage transitions with dates, or "none"
  {{NOTES}}          rep notes (treat as suspect/optimistic), or "none"
  {{FINDINGS}}       per-call failure findings already produced by the scorer, or "none"
  {{TRANSCRIPTS}}    the deal's calls, in date order, read in full (cap the total length)

STALL ARCHETYPES (use exactly one): feature-tour-no-discovery, criteria-less-poc, poc-scope-creep,
security-blocker-unresolved, champion-not-enabled, lost-to-competitor-technical, value-not-quantified,
technical-win-no-deal, structurally-dead-disqualify, won, still-active
-->

Write the presales POST-MORTEM for the {{ORG}} deal with {{ACCOUNT}} (current SE stage: {{SE_STAGE}}). Read the calls in full. Then be honest about why it is where it is, from the TECHNICAL side of the deal.

STAY SUSPICIOUS OF THE CRM AND THE SE PLATFORM. More is said on these recorded calls than in a CRM field. For each MEDDIC field the CRM claims, and for any technical-win flag, decide from the CALLS whether it was actually EARNED: 'observed' (you saw it happen on a call, cite it), 'claimed' (in the CRM/platform but never seen on any call, treat as unverified), or 'contradicted' (a call shows otherwise). You cannot mark 'observed'/'contradicted' without a verbatim call quote, and you cannot mark 'claimed'/'contradicted' for a field that is blank.

Technical Win state (already inferred; keep it SEPARATE from craft and from the business outcome): {{TECH_WIN}}
POC/POV exit criteria on file: {{POC_CRITERIA}}
CRM MEDDIC on file: {{CRM_MEDDIC}}
CRM stage history: {{STAGE_HISTORY}}
Rep notes (suspect, often optimistic): {{NOTES}}
Per-call failure findings: {{FINDINGS}}

STALL ARCHETYPES (set stall_archetype to EXACTLY one of these tokens, verbatim; do NOT invent a token): feature-tour-no-discovery, criteria-less-poc, poc-scope-creep, security-blocker-unresolved, champion-not-enabled, lost-to-competitor-technical, value-not-quantified, technical-win-no-deal, economic-buyer-not-secured, no-committed-next-step, structurally-dead-disqualify, won, still-active.

Return JSON: {
"headline":"<one sentence on the deal's state and why, technical side>",
"arc":"<short: how it opened technically, what moved it, where it stuck>",
"lost_conviction":{"date":"<call date>","moment":"<the verbatim line where technical conviction was lost>","why":"<why that moment cost the deal>"}  (or null if never lost),
"why_hold":"<the real reason it parked or lost, in plain words>",
"stall_archetype":"<EXACTLY one token from the STALL ARCHETYPES list above, verbatim>",
"poc_arc":{"criteria_defined":true,"criteria_met":"<count or ''>","criteria_failed":"<count or ''>","exit_written":false},
"coachable":true,
"meddic_check":[{"field":"metric|economic_buyer|decision_process|decision_criteria|champion|pain|competition|paper|technical_win","crm_value":"<or ''>","status":"observed|claimed|contradicted|absent","evidence":"<call quote if observed/contradicted, else ''>"}],
"one_change":"<the single technical move that most would have changed the outcome>"
}

Plain prose, no em-dash or en-dash, no buzzwords. lost_conviction.moment and any observed/contradicted evidence MUST be verbatim from a call. Keep craft, the technical win, and the business outcome as three separate things. Return only JSON.

THE CALLS:
{{TRANSCRIPTS}}
