# Prompt — the org diagnosis (judgment, runs once, leads the report)

You write the single most useful paragraph in the report: the org-level diagnosis that opens the
Diagnosis page. Leadership reads this first. It must name the CONCRETE moves the team misses on nearly
every call, in plain operator language, and say what to DO about each, so it is actionable rather than a
list of dimension names.

Input: `analysis/council_digest.json` (the run digest) — the org floor dimensions and their averages, the
stark failure examples with verbatim quotes, the per-rep craft spread, the stall-archetype clusters, the
Technical Win rate versus the business win rate, and the deal summaries. Read it in full.

## What a good diagnosis does
- Names the MOVE, not the metric. Not "POC scoping is 2.6" but "no proof of concept ever gets a written
  pass/fail number agreed up front, so the buyer decides on price instead."
- Ties the pattern to the outcome the org cares about (technical wins, deals) using the digest's own numbers.
- Is specific to THIS team's calls (use the concrete details and the verbatim examples in the digest).
- Ends each floor move with one concrete thing to change on the next call.

## Output — return ONLY this JSON
```json
{
  "headline": "<one sentence, specific and concrete, naming the through-line the team misses on nearly every call. Plain language, not dimension names. This becomes the report's opening headline.>",
  "floor_summary": "<2 to 3 sentences: the few moves the team misses on nearly every call, stated concretely, and what it is costing (cite the Technical Win vs business win gap and the floor from the digest). This becomes the opening paragraph.>",
  "fixes": [
    {"move": "<the floor move in plain words>", "what_happens": "<what it actually looks like on the calls, one concrete line grounded in the digest examples>", "do_this": "<one specific, actionable change a rep or manager can make on the very next call, concrete enough to coach against>"}
  ]
}
```
`fixes` has one entry per org floor dimension (usually 3 to 5), ordered worst first.

Rules: plain declarative prose, no em-dashes or en-dashes, no buzzwords (delve, leverage, robust,
seamless, cutting-edge, unlock, synergy). Ground every claim in the digest. Keep craft, the Technical
Win, and revenue as separate ideas. Return only the JSON.
