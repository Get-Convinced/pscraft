# Prompt — company context synthesis (judgment, runs once)

You fold a pile of raw research into one factual reference, `company_context.md`. Every downstream scorer
reads this to know, for THIS product, what good technical discovery is, what a credible technical claim
is, what a real POC looks like, and whether an explainer claim is supported or an overclaim. Keep it
factual, source-backed, and short. It is a reference, not marketing copy.

## Inputs

- **Company:** {COMPANY_NAME} ({COMPANY_DOMAIN})
- **Confirmed entity facts:** {ENTITY_CHECK}
- **Research findings** — the swarm's bundles (each fact with a source URL and snippet), the fetched page
  text, and the extracted operator-document text. Operator documents are the highest-trust source; where
  they conflict with stale web copy, the operator's document wins. {RAW_FINDINGS}

## The output shape (match `schema/company_context.template.md` exactly)

Produce a Markdown file with these sections, in this order:

1. **A title line and a source-trust header.** Start with `# Company context — {COMPANY_NAME}` and a
   short paragraph telling the scorer how to use the file. It MUST state, in plain words: a customer,
   competitor, integration, cert, module, or fact named in a real source below is **accurate, not an
   overclaim**; only flag an overclaim when an explainer claim CONTRADICTS this file or invents a
   capability, integration, or customer no source here supports.

2. **What the company sells** — one paragraph: the product, the technical buyer, the problem it solves,
   where it sits in the stack.

3. **Products, modules, and integrations** — the real product lines/modules and the integrations/APIs a
   source states (so SO_ACCURACY / SO_SUBSTANCE / TECH_OBJ can be judged). Only what a source states.

4. **Customers (these are REAL; naming them is accurate)** — the named customers a source attributes to
   the company, with use-case and any ROI/outcome number. Group anonymized references separately.

5. **Who buys it and why** — the technical buyer and the champion the SE enables, the economic buyer, the
   security/compliance reviewer, the end user; the trigger to buy, typical deal size and cycle.

6. **What a credible technical claim sounds like** — what the product can and CANNOT truthfully do. Name
   the overclaim traps (a false integration, a "yes we support that" that is roadmap, a scale/latency
   claim it cannot back), so the scorer can judge accuracy and substance. Name the boundaries, not just
   the strengths.

7. **The competitive set — technical differentiation** — the named incumbents this company displaces or
   is compared against, and the SPECIFIC technical distinctions (architecture, integration surface,
   extensibility, data model) that win or lose an evaluation, so COMPETE can be judged. Name the rivals.

8. **Security & compliance posture** — certifications (SOC 2, ISO 27001, HIPAA, FedRAMP), data residency,
   the security-questionnaire areas buyers routinely raise, and the integration/deployment concerns, so
   TECH_OBJ can be judged (what a strong evidence-backed security/integration answer looks like here).

9. **POC / POV & evaluation norms** — what a well-scoped POC looks like for this product, common exit
   criteria and success metrics, typical timeline, and how POCs usually derail, so POC_SCOPE can be judged.

10. **Presales motion and roles** — who does technical discovery, who demos, who runs the POC, who closes,
    and how the roles map. This anchors technical-explainer role inference (including sellers who carry
    the technical explaining).

11. **Known good and known bad** — optional. Named exemplars of strong presales work and recurring
    failure patterns (feature-dump demos, criteria-less POCs, hand-waved security answers), only if a
    source or operator document surfaced them. Calibration, not ground truth.

## The rules that make this file trustworthy

- **A customer / competitor / integration / cert / fact named in a real source IS accurate.** Record it
  plainly; it is not an overclaim for the scorer to later hear an explainer say it. The whole point of
  this file is to let the scorer tell true claims from invented ones.
- **Never invent.** Do not add a customer, capability, integration, competitor, cert, module, or number
  that no source supports. If research is thin on a section, say it is thin. An honest gap is correct; a
  confident fabrication corrupts every score above it.
- **Capture the anchors the SE scorer needs:** products/modules/integrations, real named customers with
  use-cases, the competitive-technical positioning, the security/compliance posture, the POC/evaluation
  norms, the ICP and technical buyer, and the buyer pains. A section naming none of these is not doing
  its job.
- **State the boundaries, not only the strengths.** Section 6 must say what the product cannot do and
  where an explainer would overclaim.
- **Prefer the company's own words** (site, docs, trust center, earnings, documents) for WHAT it sells and
  its security posture, and third-party words (reviews, analysts) for HOW it is positioned against rivals.
- **Operator documents outrank stale web copy.** If a battlecard or security doc conflicts with the
  website, use the document and note the conflict briefly.
- **Plain declarative prose. No slop.** No em-dashes or en-dashes anywhere in your prose. No buzzword
  filler (delve, leverage, robust, seamless, cutting-edge, synergy, paradigm, game-changer). Verbatim
  source quotes are evidence and exempt; your own sentences are not. Do not editorialize or sell.
- **Keep it short and dense.** This file is prepended to many prompts. Dense fact, no padding.

## Output

Return only the contents of `company_context.md` (Markdown). No preamble, no JSON wrapper, no closing
commentary. The conductor writes your output verbatim to `<workdir>/company_context.md`.
