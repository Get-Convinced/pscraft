<!--
TEMPLATE: account naming + call triage + technical-explainer + SE-stage tag. ONE task per call. This is
what lets link.py join a call to the right deal, decide scope, know who to score, and know what SE stage
the call sits at. Read the WHOLE call (titles lie, ASR mangles names). Returns ONE JSON object written
to the task's out_path; a collector merges them into analysis/call_company.json.

Placeholders:
  {{ORG}}             selling org name
  {{ONELINER}}        one-line description of what the org sells
  {{ORG_DOMAINS}}     the org's own email domains (comma-separated), to tell sellers from buyers
  {{COMPANY_CONTEXT}} company_context.md (helps recognize the org's own name when ASR garbles it)
  {{CALL_ID}}         the call id (echo it back)
  {{TRANSCRIPT}}      the FULL transcript including the header (attendees, emails)
-->

You read ONE call transcript in full and return structured facts about it. You are not scoring here. You
are identifying and triaging the call so it can be joined to the right deal, scored against the right
people, and placed at the right SE stage.

Selling org: {{ORG}} - {{ONELINER}}
The org's own people use these email domains: {{ORG_DOMAINS}}

PRODUCT CONTEXT (helps you recognize the org's own name even when ASR garbles it):
{{COMPANY_CONTEXT}}

Read the entire transcript, header and body. Then return JSON exactly:

{
  "call_id": "{{CALL_ID}}",
  "company": "<the external customer or prospect company this call is about, as a clean real-world name; the partner org for a partner-led call; or null if purely internal>",
  "company_aliases": ["<other spellings or ASR manglings of the company heard in the call>"],
  "bucket": "external_customer | partner | internal | unknown",
  "call_status": "live | no_show | aborted",
  "transcript_quality": "good | fair | poor",
  "call_phase": "presale | postsale | internal",
  "is_sales_relevant": true,
  "se_stage": "intro_qualify | tech_discovery | tailored_demo | poc_pov | tech_validation | proposal_negotiation | unknown",
  "primary_external_participants": ["<names or roles of customer-side people>"],
  "org_participants": ["<names of {{ORG}} people who actually SPOKE>"],
  "technical_explainers": ["<the org participants who CARRIED the technical explaining on THIS call: technical discovery, the demo, POC scoping, security/integration answers. Often one SE; may be a seller who did the technical work; may be empty on a purely commercial call>"],
  "one_line": "<one factual sentence on what this call was>"
}

Rules:
- Read the whole call. Classify from content, not the filename. The org's own name is often garbled.
- bucket = external_customer if a prospect or customer is present; partner if reseller/SI-led (company = the END customer, note the partner in company_aliases); internal only if every participant is on the org's domains with no customer present.
- call_phase = postsale for onboarding/support/QBR with an existing customer; internal for internal-only; presale for everything else (the calls that get scored).
- se_stage: judge from CONTENT. intro_qualify = first contact / light qualification. tech_discovery = mapping the buyer's current stack, constraints, success criteria. tailored_demo = a product demonstration. poc_pov = scoping or running a proof of concept/value. tech_validation = confirming the solution meets the technical bar / technical decision. proposal_negotiation = commercial/paper stage with the SE supporting. "unknown" only if genuinely unclear.
- technical_explainers = the org people who did the technical explaining, by the names they go by on the call. If a seller (not a dedicated SE) carried it, still list them. If nobody did (pure commercial/intro), return [].
- company is the BUYING organization, never a product or a person. Do not invent a company. If you cannot tell, company = null and bucket = unknown.
- Return only the JSON.

THE CALL (read it in full):
{{TRANSCRIPT}}
