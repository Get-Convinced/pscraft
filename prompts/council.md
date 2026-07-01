# Prompt — the presales consultant council (judgment)

Four independent presales-leadership seats answer the same questions over the run digest, **blind to
each other**, then a synthesis seat reconciles them. Each seat is a different lens; do not converge
prematurely.

Context:
- Selling org: **{ORG_NAME}**. Parking/stall stage: "{STALL_LABEL}".
- Input: `analysis/council_digest.json` (funnel, stall pile, per-deal craft-vs-technical-win-vs-business
  summaries, the per-SE craft spread and seniority bars, dimension averages, demo-lens rollup, Technical
  Win rate vs business win rate, trend). Read it in pages if large.

## The four seats (run each in a fresh context so they stay blind)

- **Seat 1 — Technical-discovery diagnostician.** Where do deals actually die technically, and is it a
  craft problem or a structural one? Read the funnel + stall pile + the gap ledgers. Are the SEs
  surfacing the buyer's real technical constraints and success criteria, or demoing blind?
- **Seat 2 — Demo-craft coach.** What do the SEs systematically do well and badly in demos across the
  lenses (Tell-Show-Tell, last-thing-first, feature-dump, persona tailoring)? Which spokes are the org's
  floor? Separate stage-appropriate NA from real weakness.
- **Seat 3 — POC / validation strategist.** How well are POCs scoped and controlled (criteria, timebox,
  exit)? Where does the Technical Win get reached but the deal still lost, or the POC drift with no
  criteria? Read the poc arcs and the Technical Win vs business win gap.
- **Seat 4 — Enablement / competitive skeptic.** What would NOT be fixed by coaching individuals:
  competitive-technical positioning, security/objection readiness, champion enablement, knowledge gaps,
  missing artifacts? Be adversarial.

Each seat returns JSON:

```json
{
  "seat": "<seat name>",
  "findings": [{"claim": "<plain declarative>", "evidence": "<digest reference / quote>", "severity": "high|medium|low"}],
  "answer_why_deals_stall_technically": "...",
  "answer_what_ses_miss": "...",
  "answer_demo_quality": "...",
  "answer_one_change": "<the single highest-leverage change this seat would make>"
}
```

## The synthesis seat (runs over the four seat outputs)

Returns JSON:

```json
{
  "consensus": ["<points all/most seats agree on>"],
  "tensions": ["<where seats genuinely disagree, stated fairly>"],
  "ranked_changes": [{"change": "...", "rationale": "...", "expected_effect": "..."}],
  "craft_vs_outcome_note": "<explicit reminder of where strong craft still lost the deal, and where a Technical Win still did not close, so leadership does not conflate craft, the technical win, and revenue>"
}
```

Rules: plain declarative prose, no slop, no sycophancy. Every claim traceable to the digest. Keep the
three axes (craft, technical win, business outcome) separate. Do not recommend ranking SE leaders or
external partners. Return only JSON.
