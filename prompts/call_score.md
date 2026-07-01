<!--
TEMPLATE: per-call technical-explainer scoring (the atom of the audit). ONE task per in-scope call.
Fill the {{PLACEHOLDERS}} and run it as one judgment task (a spawned subagent in host-agent mode, or one
engine/llm.py call in API mode). The task returns ONE JSON object matching the call_out shape in
schema/DATA_CONTRACTS.md. The number of tasks MUST equal the number of in-scope transcripts.

PSCraft scores the TECHNICAL EXPLAINER(S) on this call: whoever carried the technical discovery, demo,
POC, and objection load. Usually the SE/SC/SA; a seller who did the technical explaining is scored for
it. Score CRAFT only. The JSON key stays "reps" (the plumbing reads it) but each entry is a technical
explainer, not a commercial seller.

Placeholders:
  {{ORG}}              seller org name
  {{ONELINER}}         one-line description of what the org sells
  {{COMPANY_CONTEXT}}  the product/competitor/security source-of-truth (company_context.md), ~6500 chars
  {{ACCOUNT}}          the prospect account on this call
  {{SE_STAGE}}         inferred SE stage for this call (intro_qualify|tech_discovery|tailored_demo|poc_pov|tech_validation|proposal_negotiation), or "unknown"
  {{ARC}}              one line per PRIOR call on this deal ("- <date>: <one line>"), or "(first recorded call)"
  {{REPS}}             one line per technical explainer to score: "- <name> [<key>] = <archetype> (<label>); RESPONSIBLE DIMS: <ids>. <responsibility>"
  {{RUBRIC_ANCHORS}}   the rubric dimensions with their 1-5 anchors and the stage_expectations matrix (from schema/rubric.template.json)
  {{DEMO_CALIBRATION}} the demo_calibration block (the So-What test + the four lenses)
  {{POC_CRITERIA}}     this deal's agreed POC/POV exit criteria if a doc exists ("- <criterion>"), or "(no POC criteria doc)"
  {{COMPETITOR}}       the incumbent/alternative in play on this deal if known, or "(none named)"
  {{TRANSCRIPT}}       the FULL call transcript
-->

{{ORG}}: {{ONELINER}}

PRODUCT / SECURITY SOURCE-OF-TRUTH (judge technical accuracy, substance, and competitive claims against this; a claim not supported here may be an overclaim. Naming a real customer, integration, cert, or fact that appears below is accurate, not an overclaim):
{{COMPANY_CONTEXT}}

You are scoring how each {{ORG}} technical explainer performed ON THIS ONE CALL with {{ACCOUNT}}. Score CRAFT only (never the deal result, never whether the technical win happened later).

WHERE THIS CALL SITS IN THE DEAL (judge from the CALL ITSELF; do NOT score prior calls):
  SE-stage hint (a hint only, never ground truth): {{SE_STAGE}}
  Prior calls on this deal:
{{ARC}}
  Agreed POC/POV exit criteria on file (authoritative for WHAT the criteria are; the transcript decides whether the explainer scoped/controlled them):
{{POC_CRITERIA}}
  Competitor/alternative in play: {{COMPETITOR}}

TECHNICAL EXPLAINERS to score (score each ONLY on their RESPONSIBLE DIMS; every other dim = "NA"):
{{REPS}}

RUBRIC (score 1-5 or "NA"; use the stage_expectations matrix to decide what is DUE vs NA at this call's SE stage):
{{RUBRIC_ANCHORS}}

DEMO CALIBRATION (apply when a demo occurred; return the per-lens read in demo_lenses):
{{DEMO_CALIBRATION}}

Return ONE JSON object:
{"reps":[{"rep_key":"...","rep_name":"...","archetype":"...","kind":"dedicated_se|seller_doing_technical",
  "scores":{"<DIM_ID>":{"score":4,"confidence":"high|medium|low","why":"<one line: the read>","quote":"<the single most load-bearing VERBATIM line spoken BY THE EXPLAINER>","evidence":"<the minimal SELF-CONTAINED exchange, verbatim and speaker-labelled, across as many turns as it takes to make this score obvious to someone who did NOT hear the call: the buyer's setup or question AND the explainer's reply (and a follow-up turn if the read hinges on it). Reason about how much to include, enough to be self-evident, no more.>"}, ... one entry per responsible dim ...},
  "demo_lenses":{"demo2win_tell_show_tell":"<one line: was it Context->Capability->Impact?>","great_demo_last_thing_first":"<did they open with the compelling outcome?>","anti_feature_dump":"<feature-dump instances, or 'none'>","persona_tailoring":"<was depth tuned to who was in the room?>"}  (or null if no demo occurred on this call),
  "gap_contributions":[{"gap":"<a technical/security/integration concern the PROSPECT voiced on THIS call>","status":"addressed_written|addressed_verbal|acknowledged_open|ignored","quote":"<the explainer's line addressing it, or '' if ignored>"}],
  "failure_points":[{"label":"<short>","dim":"<DIM id>","buyer_quote":"<verbatim buyer line that set it up, or ''>","rep_quote":"<verbatim explainer line that is the failure>","why":"<why it cost technical conviction>"}],
  "signature":{"label":"<the explainer's best moment on THIS call, or null>","dim":"...","quote":"<verbatim explainer line>","why":"..."},
  "buyer_reaction":{"state":"engaged|neutral|skeptical|annoyed|disengaged","evidence":"<verbatim>"}
}]}

RULES (these define the method):
- EVIDENCE MUST BE SELF-EVIDENT. For each scored dimension, `evidence` is the exchange a reader needs to AGREE with your score WITHOUT opening the recording. Reason about how much to print: one line when a single line proves it; the buyer's setup plus your two or three reply turns when the read depends on the back-and-forth. Speaker-label every turn (e.g. "Buyer: ..." / "Rep: ..."). Keep it verbatim. Never make the reader go to the recording to understand why the score is what it is, and never pad it beyond what the judgment needs.
- QUALITATIVE FIRST: failure_points are the point. Each must cite the EXPLAINER's own line (rep_quote) as the failure, not just the buyer's concern. 1-3 per explainer.
- QUOTE = THE EXPLAINER'S WORDS. For any craft dimension the evidence quote must be a line spoken BY THE EXPLAINER being scored. A buyer's objection is the setup, never the score: find the explainer's reply and quote THAT.
- READ THE WHOLE TURN. When the buyer raises a technical/security/integration concern, quote the explainer's reply. If they answered with a concrete mechanism, architecture, doc, or config, the floor is 2, not 1.
- DEMO = SO WHAT, NOT FEATURE COUNT. Screen-share narration ("so here you can see...") is NOT credit. A shown capability earns DEMO_CRAFT credit ONLY if it was tied to a discovered pain and a business impact was stated. Feature-dump = low DEMO_CRAFT even if the tour was smooth. Fill demo_lenses whenever a demo occurred.
- POC SCOPING IS EARNED ON THE CALL. Judge POC_SCOPE from what the explainer actually scoped/controlled here (criteria, timeline, owners, a written exit), measured against the POC criteria doc if one is on file. A POC with no criteria and no timebox is a low mark, not NA.
- ACCURACY vs SUBSTANCE. "No overclaim" alone is a 3, never a 5. A false integration/security/scale claim left standing is a 1. Hand-waving ("AI handles it", "fully automated") with no mechanism is low SUBSTANCE even if technically true.
- CRAFT != OUTCOME. Score the move, not the result. Whether a Technical Win or the deal happened is NOT shown and must not be guessed. Buyer sentiment IN the call is craft-relevant.
- STAGE-AWARE / GATED NA. Work out where this call sits from its CONTENT first (a discovery call sounds nothing like a demo or a POC readout). A move not yet due at that stage is "NA", not 1. TECH_OBJ / COMPETE / KN_GAP are observability-gated: NA if no objection / no competitor / no out-of-depth question arose.
- CALIBRATION: do not default to 3. A strong explainer shows 4-5 with their own quote; a weak one 1-2 with their own quote; both show NA on moves that never came up. score is an integer 1-5 or "NA".
- Plain declarative prose. NEVER an em-dash or en-dash. Banned: delve, leverage, robust, seamless, cutting-edge, unlock, synergy. Return only JSON.

THE CALL (read it in full):
{{TRANSCRIPT}}
