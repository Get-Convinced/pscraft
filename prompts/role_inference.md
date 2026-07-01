# Prompt — technical-explainer role inference (judgment, one person at a time)

You decide what ONE person's role is at the selling org, so PSCraft scores the right people on the SE
rubric and holds them to the right bar. PSCraft scores the **technical explainer** on each call,
title-agnostic: whoever carries the technical discovery, demo, POC, and objection load. A dedicated SE
is the usual technical explainer; a seller who does the technical explaining on some calls is scored for
it; a seller who only runs commercial and never explains is context, not scored.

Context:
- Selling org: **{ORG_NAME}** — {PRODUCT_ONELINER}
- (Prepend `company_context.md`, especially its "Presales motion and roles" section.)

You are given, for this person:
- their identity (name, email — note whether the email is on the org's domains {ORG_DOMAINS}),
- the CRM deals they own or are the SE on (names, stages), may be empty,
- the full text of a sample of calls they spoke on (read them in full),
- how often and in what kind of call (intro / discovery / demo / POC / technical / commercial / internal) they appear.

Return JSON exactly:

```json
{
  "email": "<email or null>",
  "name": "<canonical display name>",
  "archetype": "solution-engineer | seller-doing-technical | se-leader | ae-nontechnical | partner-external",
  "kind": "dedicated_se | seller_doing_technical | other | external",
  "seniority": "associate | mid | senior | principal | lead",
  "seniority_inferred": true,
  "is_org_rep": true,
  "is_technical_explainer": true,
  "exclude_from_ranking": false,
  "joined_hint": "<YYYY-MM or null>",
  "left_hint": "<YYYY-MM or null>",
  "rationale": "<one or two plain sentences: what they actually do on calls (technical explaining or not) + own in CRM>",
  "evidence_call_ids": ["<2-4 call ids this rests on>"],
  "confidence": "high | medium | low"
}
```

Rules:
- **Judge from behavior, not title guesses.** Who carries the technical load: running technical
  discovery, demoing, scoping/driving the POC, answering security/integration/architecture depth,
  displacing a competitor on technical grounds? That person is the technical explainer.
- **solution-engineer** = a dedicated presales SE/SC/SA who is the technical explainer as their job
  (`kind: dedicated_se`, `is_technical_explainer: true`).
- **seller-doing-technical** = an AE/seller who, on some calls, carried the technical explaining
  themselves (`kind: seller_doing_technical`, `is_technical_explainer: true`). They ARE scored on the SE
  rubric for those moves. Say so in the rationale.
- **se-leader** = an SE manager / principal who leads and also runs technical on hard deals
  (`kind: dedicated_se`, `is_technical_explainer: true`, `seniority: lead` or `principal`).
- **ae-nontechnical** = a seller present but who did NOT carry the technical explaining (commercial only)
  (`kind: other`, `is_technical_explainer: false`, `exclude_from_ranking: true`). Recognized as context,
  not scored on the SE rubric.
- **partner-external** (`is_org_rep: false`, `kind: external`, `exclude_from_ranking: true`) if their
  email is NOT on the org's domains and they behave as a channel partner or customer-side participant.
- **Seniority** is your judgment from how they operate (depth, autonomy, whom they enable, how they run a
  room). Set `seniority_inferred: true` when you inferred it from the calls rather than being told; the
  bar for that level comes from the rubric's `seniority_bars`. If there is not enough signal, pick the
  closest level, mark confidence low, and note it.
- If someone spans roles, pick the dominant one and say so. Do not fabricate join/leave dates.
- Return only the JSON.
