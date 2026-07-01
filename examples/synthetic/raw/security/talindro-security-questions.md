# Talindro Freight - Vendor Security Questionnaire (excerpt)

Framework: SIG Lite
Vendor: Nimbus Data

## Data handling
- Does any agent run inside our data plane? Describe the access model.
- Where is customer data physically stored, and can the region be pinned?
- Is row-level data copied out of our warehouse, or is only metadata processed?

## Access and identity
- What is the scope of the warehouse role the product requires (read-only vs write)?
- Does the product support SSO / SCIM?

## Compliance
- Provide your SOC 2 Type II report and list of subprocessors.
- Confirm data residency options for regulated workloads.
