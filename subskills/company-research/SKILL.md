# Subskill — company research (Phase 2)

You build the product/competitor/customer source-of-truth that every downstream scorer grounds on.
The output is one file, `company_context.md`, written to the operator's working folder root. The call
scorer, the post-mortem writer, the role inference pass, and the adherence check all read it to decide
what good discovery is, what a credible value claim is, what a real qualification looks like, and
whether a rep claim is supported or an overclaim. If this file is thin or wrong, every score above it
is wrong.

You are the conductor. You do the planning and the synthesis. The gathering is fanned out to
subagents you spawn (host-agent mode, the default engine). The web research uses ONLY the host CLI's
own web tools (WebSearch / WebFetch). No MCP, no API key, no private knowledge base, no paid data
provider. The recipient of this skill has none of those, so neither do you.

Read `schema/company_context.template.md` before you start. That template is the exact shape of your
output. Read `prompts/research_plan.md` and `prompts/research_synthesize.md`. They are the two model
templates this phase runs.

## Inputs you are handed

From Phase 1 (intake):
- **Company name** (the selling org) and **domain** (the org's website / email domain).
- Optionally, **operator documents** dropped into `raw/docs/` (pitch decks, one-pagers, case-study
  PDFs, pricing sheets, battlecards, an existing competitive teardown). These are gold: they are the
  operator's own ground truth and override stale web copy where they conflict.
- Optionally, a sample of transcripts already in `canonical/transcripts.json`. You may skim these for
  the names of customers, competitors, and modules the reps actually say out loud. Do not score them
  here. Use them only as leads for what to research.

The working folder is resolved the same way every script resolves it: the `AUDIT_WORKDIR` environment
variable or a `--workdir` argument. Everything you write goes under it.

## Step 0 — Entity disambiguation (do this before any gathering)

Name collisions are the single most common way this phase goes wrong. "Atlas", "Apollo", "Apex", "Orion",
"Notion", "Metadata" each name several real companies. If you research the wrong "Atlas", every score
in the report is grounded on a different company's product, and the operator will not catch it because
the report still looks plausible.

Confirm you have the right company before you gather anything else:

1. Start from the **domain**, not the name. The domain is the identity. Fetch the homepage of the
   stated domain with WebFetch. Read what the company actually sells off its own site.
2. Run one WebSearch for `"<company name>" <domain>` and one for `"<company name>" <one or two words
   from the homepage, e.g. the product category>`. Confirm the search results describe the same
   company the homepage describes.
3. If the name is generic, pin the entity with discriminators you can see: the domain, the
   headquarters location, the product category, the founder or CEO name, the funding round if public.
   Write these down. Every research subagent gets them so it cannot drift to a namesake.
4. If you cannot confirm a single entity (two companies share the name AND the domain is ambiguous, or
   the operator gave a name with no domain), STOP and ask the operator one question: which company,
   with the domain. Do not guess. A wrong entity poisons the whole audit.

Record the confirmed entity (name, domain, category, location, one discriminator) at the top of your
working notes. This is the `entity_check` you carry into every subagent prompt.

## Step 1 — Plan where the knowledge lives

Run `prompts/research_plan.md`. Give it the company name, the domain, the confirmed entity facts from
Step 0, and anything already known (from the homepage, from operator docs, from transcript leads). It
returns a JSON research plan: an `entity_check` string and a prioritized list of `targets`, each with
a `source_type`, a few `queries`, a `why`, and a `priority`.

The plan must reason about where THIS company's product, customers, and competitive positioning
actually live. That differs by company:

- A **public company** has earnings calls, investor decks, and 10-K/annual-report language that state
  the segment, the named flagship customers, and the competitive set in the company's own words.
  Prioritize the investor relations page and the latest earnings transcript.
- A **venture-backed startup** has its story on Crunchbase / PitchBook (what they do, who funded
  them, headcount band) and its positioning on its own site, in G2 / Capterra / TrustRadius reviews,
  and in any Gartner / Forrester category writeup. Reviews are where you find the named competitors
  buyers actually compared them against and the pains those buyers had.
- A **category with an analyst Magic Quadrant or Wave** (CRM, observability, CDP, ERP, security)
  gives you the incumbent set and the category name for free. Pull it.
- A **services or niche B2B company** may have almost nothing on review sites; lean on the official
  site's customers/case-studies pages, press, and LinkedIn for size and segment.

Source types the plan should consider, and what each is good for:

| source_type | what it gives you |
|---|---|
| `official_site` | product, modules, pricing tiers, named customers, case studies, the company's own positioning. The spine. |
| `g2` / `capterra` / `trustradius` | review-sourced positioning, the competitors buyers actually compared, recurring praise and complaints, segment fit. |
| `gartner` / `forrester` | the category name, the Magic Quadrant / Wave incumbents, analyst framing. |
| `crunchbase` | one-line "what they do", funding, stage, rough headcount, founders. |
| `linkedin` | employee count band, the segment they sell into, sales-team shape (SDR/AE/SE presence). |
| `news` / press | recent launches, customer wins, raises, pivots, leadership changes. |
| `earnings` | for public companies: segment, named customers, competitive set, guidance, in the company's words. |
| `competitor` | the displacers' own sites, to learn how THEY position against this company. |
| `docs` | the operator's own documents in `raw/docs/`. Highest trust. |

Prioritize. You do not have unlimited fan-out. Priority 1 is the official site plus whichever of
{reviews, earnings, Crunchbase} is richest for this company type. Priority 2 fills the competitive set
and the customer proof. Priority 3 is nice-to-have color (press, LinkedIn headcount).

## Step 2 — Extract operator documents (deterministic, before the swarm)

If `raw/docs/` has any operator files, turn them into plain text first so the synthesis step can read
them and a subagent can be handed an excerpt:

```
python3 scripts/extract_docs.py raw/docs --out <workdir>/docs_text
```

(Resolve `<workdir>` from `AUDIT_WORKDIR` or pass `--workdir`.) The script handles TXT / MD / CSV with
the standard library and TRIES optional libraries for PDF / XLSX / PPTX / DOCX. When an optional
library is missing it prints a note naming the file; for those files, read the file yourself with your
own file-reading tool and paste the text into the synthesis input. Never let a missing dependency drop
an operator document. The operator's own pricing sheet or battlecard outranks anything on the web.

## Step 3 — Fan out the research swarm (parallel subagents)

For each target in the plan (in priority order, and you may cap to your host's parallel limit), spawn
one subagent. Each subagent:

- carries the `entity_check` string so it cannot drift to a namesake,
- is told its one `source_type` and its `queries`,
- uses WebSearch to find pages and WebFetch to read the few most relevant ones in full,
- returns a compact findings bundle: for each fact it found, the fact, a short verbatim snippet or
  quote that supports it, and the source URL and page title.

Spawn the priority-1 targets together, in one batch, so they run at once. Then priority 2, then
priority 3 if the picture is still thin. Independent targets must go in parallel; never serialize them.

Tell every subagent the same discipline you will enforce in synthesis:
- A named customer, competitor, module, or number is only worth returning if a real source states it.
  Return the source with it.
- Do not infer a customer or capability the page does not state. "Logos on the homepage" is a real
  source for "these are customers"; a guess is not.
- Prefer the company's own words (its site, its earnings call, its docs) for what it sells, and
  third-party words (reviews, analysts) for how it is positioned against rivals.

Collect every subagent's findings bundle. Keep the source URL and snippet attached to each fact; the
synthesis step needs them to decide what is supported.

## Step 4 — Synthesize company_context.md

Run `prompts/research_synthesize.md` over the full pile: the swarm's findings bundles, the fetched
page text, the extracted document text, and your entity-check notes. It returns `company_context.md`
in the exact shape of `schema/company_context.template.md`:

- **What the company sells** — the product, the technical buyer, the problem, where it sits in the stack.
- **Products, modules, and integrations** — the real modules and the integrations/APIs a source states,
  so technical accuracy and objection handling can be judged.
- **Who buys it and why** — the technical buyer and the champion the SE enables, the economic buyer, the
  security reviewer, the buying trigger, deal size and cycle.
- **What a credible technical claim sounds like** — what the product can and cannot truthfully do, plus
  the overclaim traps (a false integration, a roadmap "yes", a scale claim it cannot back).
- **The competitive set, technical differentiation** — the named incumbents and the SPECIFIC technical
  distinctions that win or lose an evaluation, so competitive displacement can be judged.
- **Security and compliance posture** — certs, data residency, agent vs agentless, the common
  security-questionnaire areas, so security and integration objections can be judged.
- **POC / POV and evaluation norms** — what a well-scoped POC looks like, common exit criteria, timeline,
  and how POCs derail, so POC scoping can be judged.
- **Presales motion and roles** — who does technical discovery, who demos, who runs the POC, who closes,
  including sellers who carry the technical explaining, so technical-explainer inference is anchored.
- **Known good and known bad** — optional calibration if it surfaced.

Plus the products/modules list and the real named customers with their use-cases and ROI where a
source gave them (see `schema/company_context.template.md` for the structure and the depth to aim for).

Critically, the synthesized file must open with a short header that tells the downstream scorer:
naming a real customer, competitor, or fact that appears in a source below is **accurate, not an
overclaim**; only flag an overclaim when a rep claim CONTRADICTS this file or invents something no
source supports. Without that header the scorer false-flags every true customer name a rep says.

Write the result to `<workdir>/company_context.md`.

## Step 5 — Sanity-check before you hand off

- Is the entity unambiguously the right company? (Re-read the header; would a stranger know which
  "Atlas" this is?)
- Is every named customer and competitor traceable to a source you gathered? Drop any that are not.
- Does the file say what the product CANNOT do, not only what it can? The scorer needs the overclaim
  traps.
- Is the prose plain? No em-dashes or en-dashes, no buzzword filler (delve, leverage, robust,
  seamless, cutting-edge, synergy, and the rest). Verbatim source quotes are exempt; your own prose is
  not.

When this passes, Phase 2 is done. The file at `<workdir>/company_context.md` is now the
source-of-truth every later phase prepends to its prompts.

## What you must not do

- Do not invent a customer, a competitor, a module, or a number. If no source states it, it does not
  go in the file.
- Do not reach for any data source the recipient would not have. Web tools and operator documents
  only.
- Do not editorialize or sell. This is a factual reference, not marketing copy.
- Do not let a namesake company's facts leak in. When in doubt about the entity, stop and ask.
