# PSCraft

Turn a presales / sales-engineering team's real call and demo transcripts into an interactive audit
report: per-call scoring of the **technical explainer** on a role-attributed rubric, a **Technical Win**
gap ledger per deal, deal post-mortems, a CRM/SE-platform-vs-call trust check, per-SE radar with
per-spoke explainers and demo-lens breakdowns, an independent maker-checker pass, and a four-seat
consultant council. Craft is scored separately from **both** the Technical Win and the business outcome.
Every call is read in full; numbers only appear once they aggregate.

PSCraft is the presales sibling of [call-craft](https://github.com/Get-Convinced/call-craft) (which
audits AE/closer calls). It scores whoever carried the technical explaining on each call, title-agnostic:
usually the SE/SC/SA, and a seller who does the technical work is scored for it and recognized.

This skill is **self-contained and engine-agnostic**. It ships no API keys and no data. It runs inside
any agentic CLI that can read/write files, run Python (stdlib only), search the web, and spawn subagents
(Claude Code, Claude cowork, Codex, and similar). By default the judgment runs as subagents using **your**
CLI's own model, so there is nothing to sign up for.

## Install

Install straight from this repo with the [`skills`](https://github.com/vercel-labs/skills) CLI:

```bash
# Global — available in every project (~/.claude/skills/)
npx skills add -g Get-Convinced/pscraft

# Or project-local (./.claude/skills/)
npx skills add Get-Convinced/pscraft
```

Add `-a claude-code -y` for a non-interactive install, or `--list` to preview first. Restart your CLI,
then run `/pscraft`. Prefer to do it by hand? Clone this repo into `~/.claude/skills/pscraft`.

## What you provide

| Input | Required? | Formats |
|-------|-----------|---------|
| **Call / demo transcripts** | **Yes** | Read.ai, Gong, Chorus, Fireflies, Otter, Zoom, or plain text. One file per call, or an export. |
| CRM deal export | Optional | CSV / XLSX / JSON from Salesforce, HubSpot, Zoho, etc. Unlocks the funnel + trust check. |
| POC / POV success-criteria docs | Optional | PDF / DOCX / MD. The criteria POC scoping is judged against. |
| Mutual action plans | Optional | Any doc. Corroborates POC and deal control. |
| Security questionnaires (SIG / CAIQ / VSQ / RFP / RFI) | Optional | XLSX / DOCX. Corroborates technical-objection handling. |
| SE-platform export (Vivun / Prelay / Cuvama) | Optional | CSV. Technical-win flag, POC status, evaluation criteria. |
| Solution-design docs, rep notes | Optional | Any doc / text. Corroborating signal, never truth. |

Only transcripts are mandatory. Everything else is asked for but never blocks a run; the report degrades
cleanly (no CRM means craft-only scoring, no funnel, no trust check).

## How to run

```
/pscraft ./my-team-calls
```

It will: research the company off the web (product, competitors, security posture, POC norms) and fold
in any docs, read each POC/security/design doc in full into a canonical shape, infer who carried the
technical-explainer role on each call, read every call in full, score that explainer across the SE
rubric, infer a Technical Win per deal, write deal post-mortems, run an independent adherence check and
the council, and render one self-contained `report.html`.

## The three axes, never blended

1. **Craft** — the 1-5 rubric composite (technical discovery, tailored-demo craft, POC scoping,
   technical-objection handling, competitive displacement, champion enablement, defeating status-quo,
   plus technical accuracy, substance, and knowledge-gap handling).
2. **Technical Win** — the craft-side outcome: was the solution judged superior and were the prospect's
   voiced gaps closed? Tracked with a per-deal gap ledger.
3. **Business outcome** — won / lost / stalled, ARR, stage, when a CRM is present.

A strong SE who reached a Technical Win on a deal later lost to price is **not** marked down.

## Engine options

- **Default — host agents (no key):** scoring and research run as subagents in your CLI, with its model.
- **Optional — bring your own API:** point it at an OpenAI-compatible endpoint via a local `.env`.

## Privacy

Your transcripts, CRM data, docs, and the report never leave your machine (host-agent mode keeps
everything in your CLI session; API mode only sends transcripts to the endpoint you configure). The
skill ships no secrets, and `.gitignore` blocks `.env` and any work data from being committed.

New here? Open `docs/guide.html` for a plain-language overview. See `SKILL.md` for the method,
`SPEC.md` for the design, and `RUNBOOK.md` for the step-by-step procedure.
