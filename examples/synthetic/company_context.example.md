# Company context — Nimbus Data

Use this file to judge technical craft for Nimbus Data. A customer, integration, cert, or fact named here is accurate, not an overclaim; only flag an overclaim when an explainer claim contradicts this file or invents a capability or integration no source here supports.

## What the company sells
Nimbus Data is an agentless data-pipeline observability platform for teams on dbt and Snowflake. It detects freshness, volume, and schema incidents and surfaces them to the data team before a business user notices.

## Products, modules, and integrations
Freshness and volume monitors inferred from the dbt manifest, anomaly detection, column-level lineage, and alerting into Slack and PagerDuty. Native integrations: Snowflake, BigQuery, dbt, Airflow. On-prem SQL Server is EARLY ACCESS only, read-through a cloud gateway, not a native connector.

## Who buys it and why
The technical buyer is the head of data or data platform lead; the champion is usually a senior data engineer. Security reviews are run by an infosec lead. The trigger is a public data incident (a bad number reaching finance or a customer).

## What a credible technical claim sounds like
Truthful: agentless, metadata and query-based checks through a read-only Snowflake role, row data stays in the customer account, dbt-native coverage day one. OVERCLAIM TRAPS: claiming a native on-prem SQL Server connector (it is early access only), claiming "we support every database," or claiming row data leaves the customer account (it does not; metadata only).

## The competitive set — technical differentiation
Primary competitor is Sentinel (the incumbent). Nimbus wins on agentless and dbt-native inference (checks are derived from the dbt graph, not authored per asset), which is why large-model-count trials with Sentinel stall. Nimbus is weaker than Sentinel on breadth of non-warehouse and on-prem sources.

## Security & compliance posture
SOC 2 Type II. Agentless: no agent runs in the customer data plane. Metadata only, region-pinned to the customer's Snowflake region. Common questionnaire areas: data residency, agent vs agentless, read-only access scope, subprocessors.

## POC / POV & evaluation norms
A good Nimbus POC fixes measurable exit criteria up front (for example detect a set percentage of incidents before a business user, and a mean-time-to-resolve target), runs three to four weeks on a named set of schemas, and ends in a written technical decision. POCs derail when success is never defined or when the source that holds the real pain is never connected.

## Presales motion and roles
An SE runs technical discovery, the tailored demo, and the POC. The AE owns commercial and paper. On some deals a seller carries the technical explaining themselves.
