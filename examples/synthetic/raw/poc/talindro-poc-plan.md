# Talindro Freight - Nimbus Data POC Plan

Account: Talindro Freight
Timeline: 3 weeks (2026-02-26 to 2026-03-19)
Scope: billing pipeline plus two upstream schemas
Owners: Marcus Whitfield (Talindro, validation), Sam Rivera (Nimbus, setup)

## Exit criteria (technical decision is made if both are met)
1. Detect at least 90% of freshness and volume incidents before a business user reports them. Metric: incidents detected first by Nimbus / total incidents. Target: >= 90%.
2. Mean time to resolve incidents under 30 minutes. Metric: average time from alert to resolution. Target: < 30 min.

## Security prerequisites
- SOC 2 Type II report shared
- Agentless, read-only Snowflake role, region pinned, metadata only
