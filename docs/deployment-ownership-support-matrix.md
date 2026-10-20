# Deployment ownership and support matrix

The #8 foundation provides local and GitHub Actions validation plus a manual read-only DEV identity pilot. Cloud deployment workflows are intentionally unimplemented. The foundation and pilot are merged into `main` through [PR #17](https://github.com/frdeange/FabricF1Demo/pull/17); issue #8 is closed. Separately, the existing [#3](https://github.com/frdeange/FabricF1Demo/issues/3) owner handoff records a separately approved four-resource Terraform deployment: `rg-f1demo-swc`, F2 `f1democapswc` in Sweden Central, and `f1-dev` / `f1-pro` on that capacity. The capacity was Active at verification; this is not a fresh live-state check. The handoff records infrastructure changes uncommitted on the separate #3 branch; this scaffold does not inspect or change that delivery.

Infrastructure deployment does not qualify workloads or unattended deployment. `f1-pro` is a stable demo workspace, not production. No additional infrastructure, budgets, autopause or autoscale are configured; F4 requires separate approval. Do not add a deploy workflow or change resources from this alignment.

## Deployment qualification beyond the closed foundation

Issue #8 is closed for the merged foundation; this is not unattended deployment acceptance. A future unattended deployment pilot from a clean runner must prove the approved revision against the approved DEV target, repeat without duplicating items or resetting data, and record drift handling. Current cloud deploy acceptance is **BLOCKED** on an approved unattended deployment identity and permissions, protected state, coordination and recovery for infrastructure, and a qualified clean-runner test. The manual read-only identity pilot does not prove those write operations. The existing bootstrap targets are not wholly unapproved; they are also not evidence of workload or unattended readiness. Confirm scope, cost and rollback separately for any future pilot.

## Principles

The closed #8 issue is foundation evidence, not the owner of future deployment
execution. Routine deployment/orchestration has no assigned follow-up issue yet;
assign a bounded package before starting it. Coordinate infrastructure readiness
with #3 and app/runtime qualification with #9 without transferring their ownership.

- One writer per artifact and destination. Do not mix Git sync, fabric-cicd, Rayfin CLI, REST updates, manual portal edits, and migrations against the same target without a documented owner.
- Prefer OIDC/federated identity for GitHub Actions when the target APIs support it, scoped to the repository and environment. Persistent secrets require explicit approval, minimum scope, rotation, and storage in approved GitHub Environments or a vault.
- Keep deployment configuration secret-free in Git. Environment variables may name approved targets, but credentials, tenant IDs considered sensitive, service principal secrets, tokens, and connection strings must not be committed.
- Validation workflows use read-only permissions. Deploy jobs must not run for fork PRs or `pull_request_target` until a separate security design is approved.

## Matrix

| Area | Single writer / artifact owner | Documented facts | Tenant qualification pending | Credential and OIDC caveats | Current implementation state |
| --- | --- | --- | --- | --- | --- |
| Existing infrastructure | Terraform under #3 ownership: resource group, capacity and two workspaces | The #3 handoff records the four-resource deployment and no-change post-apply plan. Terraform uses one external local state. Do not create another active state or blindly apply an empty state to existing resources. | Protected state, coordination and recovery before multi-operator or unattended infrastructure deployment; shared F2 workload fit remains unqualified. Future networking, workers, gateways, storage and other expansion require separate tooling/ownership, resource, cost and rollback approval. | The approved bootstrap operator is not a qualified unattended identity. OIDC and permissions must be proven per operation; do not grant access or add secrets here. | Infrastructure deployed according to #3 evidence; uncommitted IaC on its separate branch. No unattended infrastructure deploy workflow exists. |
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
