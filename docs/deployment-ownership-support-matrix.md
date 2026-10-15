# Deployment ownership and support matrix

This repository is ready only for local and GitHub Actions validation. Cloud deployment workflows are intentionally unimplemented until the user separately approves target resources, authentication, budget, and rollback expectations. Do not add a deploy workflow that can misfire.

## Issue #8 closure gate

Issue #8 must remain open after this foundation slice. It can close only after an unattended deployment pilot from a clean runner proves the approved revision against an approved DEV target, repeats without duplicating items or resetting data, and records drift handling. Current cloud deploy acceptance is **BLOCKED** on separately approved target identity, workspace, region, budget, and a qualified clean-runner test.

## Principles

- One writer per artifact and destination. Do not mix Git sync, fabric-cicd, Rayfin CLI, REST updates, manual portal edits, and migrations against the same target without a documented owner.
- Prefer OIDC/federated identity for GitHub Actions when the target APIs support it, scoped to the repository and environment. Persistent secrets require explicit approval, minimum scope, rotation, and storage in approved GitHub Environments or a vault.
- Keep deployment configuration secret-free in Git. Environment variables may name approved targets, but credentials, tenant IDs considered sensitive, service principal secrets, tokens, and connection strings must not be committed.
- Validation workflows use read-only permissions. Deploy jobs must not run for fork PRs or `pull_request_target` until a separate security design is approved.

## Matrix

| Area | Single writer / artifact owner | Documented facts | Tenant qualification pending | Credential and OIDC caveats | Current implementation state |
| --- | --- | --- | --- | --- | --- |
| Azure IaC | Azure IaC package, using Bicep and Azure CLI from GitHub Actions | Azure resources such as networking, workers, gateways, storage, and resource groups require explicit subscription/resource-group scope and cost visibility. | Subscription, region, resource group, quotas, budget, roles, naming, teardown, and approval flow. | Use GitHub OIDC to an approved Entra identity where supported. Do not create persistent secrets or assign roles from this repository slice. | Not implemented. No Azure deploy workflow exists. |
| fabric-cicd | Fabric item definition package per workspace/environment | fabric-cicd is suitable for supported Fabric item definitions with explicit scope; it is not a universal deployer for every Fabric or Rayfin artifact. Full-scope publication means item directories/types and orphan handling must be chosen deliberately. | Supported item types in the target tenant, dependency order, connection rebinding, service principal support per operation, and clean-runner repeatability. | TokenCredential/OIDC must be proven for the operation. Do not depend on interactive defaults. Do not run orphan deletion automatically. | Not implemented. Validation only. |
| Rayfin CLI and managed apps | Rayfin app package for each app item and environment | Rayfin is the required managed Fabric hosting path for the two apps. Evidence in the approved plan is from Rayfin 1.36.2. Rayfin 1.36.2 deployment pipeline excludes functions/secrets, so native AppBackend promotion must not be represented as a full app deployment. | Fabric Apps workload, capacity, workspace, item permissions, chosen Rayfin version, app endpoints, runtime identity, function deployment route, and app/database permissions. | Non-interactive auth and destination selection must be proven before CI deploy. Do not let a runner create a workspace or trial by default. Secrets and function/runtime configuration need an approved route. | Not implemented. No Rayfin project or deploy workflow exists. |
| REST and migrations | API/migration package owning each endpoint schema or non-Rayfin serving contract | DDL, serving contracts, and items not managed by Rayfin or fabric-cicd need versioned migrations/scripts and reconciliation evidence. Git sync is not a data migration mechanism. | Endpoint type, migration tool, rollback approach, compatibility rules, drift detection, and permissions per operation. | Use the least privileged approved identity for each endpoint. Avoid personal interactive sessions in repeatable deployment evidence. | Not implemented. No migration runner exists. |
| Source seeding | Source-specific seed package or adapter owning generated data and replay contracts | Repository data must be public-safe and reproducible. Simulated payments and synthetic source data are allowed when labeled. Internal reference material, credentials, tenant exports, customer data, and unapproved licensed datasets are not allowed. | SAP rights/source route, Salesforce policy, Oracle/gateway setup, seed volumes, external keys, reconciliation tests, and dataset license verification. | Source credentials must stay outside Git and be approved per environment. Do not seed from private folders or machine-local absolute paths. | Not implemented. No seeding workflow exists. |

## First deploy workflow requirements before implementation

Before adding any cloud deploy workflow, document and independently review:

1. Approved target workspace, capacity, region, subscription/resource group if Azure is involved, budget, and teardown/rollback expectations.
2. Approved deployment identity, exact permissions, OIDC or secret handling, and GitHub Environment gates.
3. Item-by-item writer ownership and exclusion rules, including Rayfin-managed children and fabric-cicd scope.
4. Clean-runner rehearsal command, expected evidence, idempotency criteria, and drift behavior.
5. Confirmation that DEMO targets cannot resolve DEV endpoints, item IDs, secrets, or source bindings.
