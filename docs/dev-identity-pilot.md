# Read-only DEV identity pilot (#8)

## Scope and authorization

The user approved a dedicated `f1demo-github-dev` application/service principal,
GitHub environment-scoped OIDC federation and Contributor access in `f1-dev`.
Bootstrap readback confirmed no client secrets/certificates, no configured API
application permissions and no direct workspace role in `f1-pro`.
No Azure RBAC, Terraform/state, capacity or tenant-wide setting was changed.
Bootstrap evidence is recorded in issue #8; configuration is not proof of
unattended authentication or deployment.

GitHub Environment `dev` holds `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and
`FABRIC_WORKSPACE_ID` as variables outside Git. Its deployment branch policy
permits only `main`, with no allowed tags. Federation uses the exact subject
`repo:frdeange/FabricF1Demo:environment:dev`, issuer
`https://token.actions.githubusercontent.com` and audience
`api://AzureADTokenExchange`. No secrets or personal login cache are used.

## Execution

After independent review, user approval and merge of the workflow into `main`,
run **Verify DEV identity** from Actions on `main` (or
`gh workflow run verify-dev-identity.yml --repo frdeange/FabricF1Demo --ref main`).
The workflow also rejects other refs itself. Do not weaken the environment
policy to run a feature branch before review.

The Python standard-library verifier obtains a GitHub OIDC assertion, exchanges
it at Entra for a Fabric access token and calls only **GET workspace** for the
configured target. Both the returned ID and name must match the configured
workspace and `f1-dev`. It performs no writes, item/data access, deployment,
capacity resume/pause, role assignment or Terraform action.

All HTTP calls have timeouts and reject redirects. Requests never fall back to
developer credentials. Logs report fixed stages/status codes, not tokens,
response bodies or tenant/workspace coordinates.

## Evidence and failure handling

Record the successful Actions run URL, revision SHA and summary in issue #8.
A second manual run can confirm repeat authentication without mutations.
An absent, skipped or failed job is not a successful qualification.
Do not mark this pilot qualified until an actual clean-runner run succeeds.

A 403 can reflect tenant/API service-principal restrictions or workspace
authorization; diagnose the specific stage without automatically enabling
tenant-wide settings. Missing configuration, token exchange errors, unexpected
targets and network failures stop execution. Do not introduce a client-secret
fallback or expand permissions to make the check pass.

This proves only federated authentication and one workspace metadata read.
Rayfin CLI compatibility, per-operation permissions, workload fitness,
deployment, repeat deployment, runtime authorization and shared application
persistence remain separate acceptance gates: #9 owns app/runtime qualification,
and routine deployment requires an assigned follow-up package before execution.
The closed #8 foundation does not own pending deployment work. Infrastructure
automation requires #3 coordination and remains blocked on its accepted
state/coordination/recovery debt.
