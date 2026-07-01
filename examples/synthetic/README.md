# PSCraft synthetic example

A tiny, fictional presales corpus for Nimbus Data (an agentless data-observability vendor) so you can see
a full PSCraft run without any real data. Everything here is invented.

## What is in it

- `raw/transcripts/` — four call/demo transcripts across two deals:
  - **Talindro Freight** (strong): technical discovery that sets a measurable bar, then a tailored,
    outcome-first demo that scopes a POC with written exit criteria and handles the security review.
  - **Crestpoint Foods** (weak): a feature-dump demo that ignores the buyer's stated pain, then a
    criteria-less POC that never connects the on-prem source and is lost on the technical evaluation.
- `raw/crm/deals.csv` — two deals with an SE owner, a competitor, and a (deliberately optimistic)
  `Technical Win` flag on Talindro that the calls do not yet corroborate.
- `raw/poc/talindro-poc-plan.md` — the POC success criteria the scoring judges POC control against.
- `raw/security/talindro-security-questions.md` — a security questionnaire excerpt.
- `company_context.example.md`, `config.example.json` — a ready company context and run config.

## Run it

```
/pscraft ./examples/synthetic/raw
```

Point PSCraft at the `raw/` folder. In the report, notice: Sam (a dedicated SE) scores far above Priya;
Dana (the AE) is scored in the SE lane on the POC call because she carried the technical explaining; the
Technical Win page shows Talindro **in validation** with the CRM "Yes" flag marked uncorroborated, and
Crestpoint **lost technical** with an ignored on-prem gap; and the Crestpoint demo is scored a feature-dump
from every lens. Craft, the Technical Win, and the business outcome stay three separate reads.
