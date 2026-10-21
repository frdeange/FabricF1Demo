# Issue #3 readiness handoff

## Preservation and reproducibility follow-up (2026-10-21)

Status: documentation and local preservation authorized; no cloud execution.

The user authorized preserving the pending infrastructure work in local commits,
documenting the manual commissioning steps, and assessing automation. Keep all
cloud compute off. No push, PR, merge, VM start, capacity resume, access change
or destructive rebuild is authorized by this follow-up.

1. Preserve the existing Terraform root, network-module changes, lock file,
   tests and untracked workload configuration in explicit local commits.
   Exclude credentials, state, plans, provider caches and private references.
2. Add a reconstruction runbook covering guest installation, Oracle provider
   registration, gateway registration, Oracle logging, connectivity, table scope,
   verification and unresolved CDC/recovery limitations. Distinguish recorded
   success from proposed automation and from clean-machine validation.
3. Run local checks and obtain independent actual-diff review before the final
   preservation handoff. Do not treat a local commit as a deployment or a PR.
4. Only after a directly confirmed destination and coordinated project/session
   migration, consolidate or relocate checkouts using Git-aware operations.
   Preserve every branch and pending change and verify the backend before
   retiring a worktree. This step is not a prerequisite for infrastructure work.
   Do not move `.git`, remove checkouts or change project roots in phase 1.

The unique state remains in the shared `.local\terraform` directory. Never
create a second active state. Saved plans from before its relocation are not
approved for reuse.

Local preservation evidence: Terraform formatting/validation and five
mock-provider tests passed; repository validation and 58 credential-free
unit tests passed. Independent review of the actual public diff, including
the untracked workload and reconstruction runbook, returned no actionable
findings. No deployed-state refresh, cloud plan/apply or clean-machine
reconstruction was performed. The infrastructure snapshot is preserved in
local commit `4f1ca65`; documentation is committed separately. Checkout
consolidation/removal remains pending the directly confirmed destination and
project/session coordination.

Before any future root consolidation, account for the repository validator:
it currently traverses local paths and rejects the private reference directory
even if Git ignores it. Qualify validation/archive tooling to exclude private
local content before placing that content under a Git root. `.gitignore` alone
does not make every filesystem tool safe for the proposed layout.

Model recommendation: `gpt-5-mini`, reasoning effort `medium`, for bounded
documentation and mechanical preservation after scope approval. Recommend an
independent `gpt-5.6-sol` reviewer with effort `high` for the actual Terraform
diff, secret-exclusion and migration gates. Escalate on conflicting worktrees,
resource address changes, installer behavior, Oracle privilege/container
questions or state discrepancies rather than improvising fixes. These are
recommendations, not a claim about Auto's underlying model or review execution.

## Initial deployment handoff (historical)

The recorded first-deployment preflight treated an absent Terraform state as
not applicable after confirming the external local backend was initialized and
empty; it did not create or fabricate state. The exact user-approved plan was
then applied successfully: one resource group, one F2 Fabric capacity, and two
workspaces. The capacity was left active as approved at that time. This is a
historical handoff record, not a statement of current Azure, Fabric, billing, or
Terraform-state status; verify those facts before any future operation.

## Deployed environment

The initial minimum execution environment was deployed:

- Azure resource group: `rg-f1demo-swc`
- Fabric capacity: `f1democapswc`
- Fabric workspaces on that capacity: `f1-dev` and `f1-pro`
- Region: Sweden Central
- Initial capacity: F2 PAYG, Active at the recorded handoff; current status must be rechecked

Terraform preparation and validation were read-only with respect to Azure. A
separate user-approved apply created only the listed targets; this document
does not authorize extra resources or access changes.

Subsequent separately approved work added the Oracle/gateway VMs and private
network preserved in `infra/workload.tf`. The
[reconstruction runbook](../docs/runbooks/oracle-gateway-reconstruction.md)
records guest installation, Managed ODP.NET, gateway registration, logging,
manual corrections, automation candidates and remaining CDC/recovery gates.
The original four-resource checks below are historical, not validation of
those later additions or of a complete rebuild.

## Decisions carried into this repo

- Use Terraform directly.
- Keep the unique state local, ignored and separate from tracked files.
- The initial slice excluded private networking and database backups; later
  explicit approvals covered the pilot network/VMs and Oracle backups.
  No remote state, storage accounts, runners or extra shared infrastructure
  are authorized by this follow-up.
- Do not add budgets, alerts, reservations, autoscale, or overage activation.
- Treat this slice as a technical-debt waypoint, not a complete production platform.
- `f1-pro` is a stable demo workspace, not real production.
- Any move from F2 to F4 requires a new approval.
- Approximately 20 active hours per month is an estimate, not a runtime limit or
  evidence that F2 can handle the complete demo.

## Repository artifacts

- `infra/` contains the Terraform root for the resource group, capacity,
  workspaces and separately approved pilot network/VMs.
- `README.md` links to this handoff document.
- `.gitignore` excludes Terraform state, lock-adjacent scratch files, plans, and private variable files.

## Terraform baseline used for this prep

- `hashicorp/azurerm` `5.10.0`
- `microsoft/fabric` `1.14.0`
- `terraform` CLI `1.16.6`

Schema checks during this prep confirmed:

- `azurerm_fabric_capacity` requires a nested `sku` block with `name` and `tier`.
- `fabric_workspace` accepts `display_name` and a Fabric capacity GUID in `capacity_id`.
- The capacity list data source filters by exact display name, region, and SKU,
  then requires exactly one match before workspace assignment. The ARM resource
  ID must not be passed as a Fabric GUID.
- The Fabric provider data sources used here support service-principal authentication.

These notes describe the static configuration prep only. They are not a deployment authorization and they do not replace a live preflight against the final operator identity.

Source basis: Terraform Registry provider documentation plus local `terraform providers schema -json` inspection after `init`.

## Local state rule

Use one stable local backend path outside both Git checkouts and outside
disposable session directories. The user-approved shared project-local folder
is `.local` in the parent directory of the sibling checkouts. Canonical shape:

`<shared-project-folder>\.local\terraform\terraform.tfstate`

On 2026-10-21, the existing local secrets and state directories were moved from
`%LOCALAPPDATA%\FabricF1Demo` into that shared `.local` folder, with file
integrity checks and local backend reconfiguration. The former directories
are no longer canonical. Credentials are under `.local\secrets`; supply the
private variable file explicitly when needed. No cloud resources were changed.
Do not reuse saved plans generated before the move; regenerate and review them
against the canonical backend before an approved execution.

Do not publish the actual operator path in this repository. Do not create a remote backend for this slice.
Use one operator and one Terraform execution at a time. Do not create active
copies of the state for different worktrees. The local backend's locking is not
a multi-machine coordination solution.

From the repository root, initialize an explicit stable state path:

```powershell
$sharedProjectDir = Split-Path -Parent (Get-Location).Path
$stateDir = Join-Path $sharedProjectDir ".local\terraform"
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
$statePath = Join-Path $stateDir "terraform.tfstate"
terraform -chdir=infra init -input=false "-backend-config=path=$statePath"
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate -no-color
terraform -chdir=infra test -no-color
```

These checks do not require private input values or create cloud resources.
The tests use mocked providers, not a real Azure/Fabric deployment.

## Exact deployment names

These names must be rechecked before any future apply:

| Kind | Name |
| --- | --- |
| Resource group | `rg-f1demo-swc` |
| Capacity | `f1democapswc` |
| Workspace | `f1-dev` |
| Workspace | `f1-pro` |

## Future debt that remains open

- Shared or remote Terraform state
- Backup and recovery design
- Multi-operator coordination and locking beyond local disk
- Private endpoints, VPN, runner infrastructure, and storage-backed state
- Any Azure-side automation or unattended deployment workflow

**Accepted technical debt:** local state is machine-dependent, with no designed
shared storage or managed recovery. No NAS or backup configuration is part of
this issue. Losing the state can require reviewed import/reconciliation of
existing resources; never blindly apply an empty state to recreate them.
Resolve protected shared state, coordination and recovery before multi-operator
or unattended infrastructure deployment. This future work is relevant to
[issue #8](https://github.com/frdeange/FabricF1Demo/issues/8), not implemented here.

## Preflight and separate deployment approval

1. Privately confirm the exact signed-in operator, subscription UUID, tenant
   UUID, approved names, cost, and rollback. Supply `subscription_id`,
   `tenant_id`, and the approved existing `capacity_administration_members`
   privately through `TF_VAR_*` environment variables or an external variable
   file. Do not commit those values or use conflicting authentication overrides.
2. Immediately before the first apply, verify `Microsoft.Fabric` is already
   registered, refresh F2 availability and regional CU quota, and check
   exact-name collisions for all four resources, including a tenant-wide Fabric
   capacity list filtered by exact name, region, and SKU. Repeat the collision
   check if any time passes or another operator may have created resources.
   Never adopt, import, overwrite or reuse unrelated resources without approval.
3. Verify the operator can create workspaces, assign this capacity, administer
   the approved targets and perform capacity read/write/suspend/resume actions.
   Azure management access does not imply Fabric or tenant-setting permissions.
4. Qualify Fabric Apps/Rayfin availability and workload fit separately; neither
   is proven by this Terraform configuration. Validate appropriate Power BI
   per-user licensing below F64. Do not enable tenant features or grant roles
   to bypass a failed preflight.
5. Review the exact Terraform plan privately. It must contain only the approved
   resource group, F2 capacity, two workspaces and approved administrator list.
   No deletion, replacement, extra providers or unapproved access changes.
6. Stop for independent implementation review and the user's reviewed-result
   approval before any PR. Obtain separate explicit cloud approval before
   applying anything. Do not use automatic approval or automatic destroy.

Resource `prevent_destroy` guards are an additional safeguard, not a substitute
for reviewing a plan or protecting the local state. Do not remove the guards or
resource definitions to bypass them. After a permitted apply, re-plan with the
same state and require no unexpected changes.

The Fabric capacity list used to resolve the new capacity's Fabric GUID is read
after Azure creates that capacity. Therefore the Terraform uniqueness guard can
detect a duplicate only after the resource group and capacity may already have
been created. A duplicate discovered at that point is a partial deployment:
stop immediately, do not create workspaces, do not retry or destroy, retain the
local state and existing resources, and request review for a safe recovery plan.
The mandatory immediate pre-apply collision check reduces this risk but cannot
eliminate a concurrent-create race.

## Manual operation and nondestructive rollback

1. Confirm the exact project capacity and that both workspaces still target it.
   Resume only that capacity through the approved operational route. Poll until
   it is ready, with a bounded wait; stop and report failures.
2. Check dependencies, service readiness and freshness before starting selected
   jobs, replay or ingestion. A stopped Fabric process cannot wake its own
   capacity; missed schedules are not assumed to replay automatically.
3. Avoid heavy concurrent DEV processing during a demonstration in `f1-pro`.
4. Before pausing, stop new producers/schedules and check for active users and
   jobs in **both** workspaces. Drain or safely finish work. If quiescence cannot
   be established, report it rather than pausing blindly.
5. Pause the capacity and verify the completed paused state. Neither workspace
   is operational while paused. OneLake storage can remain billable, and
   cumulative overages/smoothed operations may be settled when pausing.
6. On a failure, retain state, workspaces and data; safely stop work and pause
   new compute where possible. Any deletion or access expansion requires fresh
   approval. Never use `terraform destroy` as the routine rollback.

No budgets, reservations, autoscale or overage billing are configured. The
public retail rate observed for Fabric capacity usage in Sweden Central was
USD 0.19 per CU-hour. F2 has 2 CUs, so the base estimate is about USD 0.38 per
active hour, or USD 7.60 for 20 active hours in a month. This is not an invoice
cap: OneLake storage, overages and settlement of smoothed operations when
pausing are additional. When active, the capacity continues to accrue usage
charges until the operator pauses it; verify its current status before
estimating charges. See
[regional retail prices](https://prices.azure.com/api/retail/prices).

## Static validation for this prep

- `terraform fmt -check`
- `terraform init` against the local backend path
- `terraform validate`
- `terraform test` with mocked providers

### Required validation checks

Required recipe checks: installed tooling, approved authentication/context,
local backend initialization, formatting, validation, private read-only plan,
state inspection, unresolved-template scan and variable-file syntax if present.
For a verified first deployment, state inspection is not applicable until a
real apply creates state; never create placeholder state to satisfy this check.
Record each as passed, blocked or not applicable; do not infer workload
performance from static validation.

## 7. Historical Validation Proof

The results below record checks reported for the initial deployment. They are
not current preflight results and must not replace fresh checks before future
infrastructure operations.

| Check | Result |
| --- | --- |
| Pinned-provider initialization with external local backend | Passed |
| `terraform fmt -check -recursive` | Passed |
| `terraform validate -no-color` | Passed |
| `terraform test -no-color` | Four mocked invalid-input tests passed; no cloud apply |
| Capacity lookup ambiguity guard | Exact display name, region, and SKU filter with an exactly-one-match precondition on both workspace resources; duplicate fixture not directly tested without creating a capacity |
| Native read-only plan with privately verified operator/context | Exactly four creates: resource group, F2 capacity, two workspaces; no updates/deletes |
| Official Terraform recipe preflight | Passed after apply with an in-memory compatibility correction for the installed PowerShell runner: init, fmt, validate, plan, authentication, state list, and template scan passed; `main.tfvars.json` check skipped because the file is absent |
| First-deployment state handling | Pre-apply state inspection was `SKIP` because the initialized backend was empty. After apply, the real state was moved to the approved external local path and is readable there; no placeholder state was created |
| Azure subscription RBAC | Read-only check confirmed the operator has subscription Owner; no RBAC grants are in the Terraform configuration |
| Fabric workspace creation settings | Read-only tenant-settings check reports “Create workspaces” and “Users can create Fabric items” enabled; no tenant settings were changed |
| Resource and Fabric name collision checks | No matching resource group, visible Fabric capacity, or workspace named `f1-dev` / `f1-pro` immediately before apply |
| Fabric regional availability/quota | Azure quota tools list Sweden Central for `Microsoft.Fabric/capacities`; usage reports “No Limit”. F2 availability was confirmed in Sweden Central |
| Static access review | Capacity administrator input was limited to the approved existing operator; no Azure RBAC role assignments or new identities were created |
| Approved Terraform apply | Exactly four resources created; zero changed or destroyed |
| Post-apply resource verification | Resource group and F2 capacity verified in Sweden Central; `f1-dev` and `f1-pro` both report the same Fabric capacity GUID. The capacity state is Active. Private resource IDs are intentionally omitted |
| Post-apply Terraform plan | No changes; infrastructure matches configuration |
| Formal Azure validation status | `Validated` for the recorded checks; this does not qualify Rayfin/workload performance |

The installed PowerShell recipe runner's `$Args` parameter shadows PowerShell's
automatic argument variable. For validation, its argument name was corrected in
memory without changing the installed skill. Before apply, `state list` was
`SKIP` only after verifying that the initialized backend was empty for this
first deployment. Following apply, the real state was moved out of the repository
to the stable external path, the backend was reconfigured without state migration,
and a subsequent full preflight passed including `state list`. The azure-validate
workflow completed; validation itself did not create resources or placeholder
state.

This branch starts from `main`, which does not yet contain the Python checks or
ownership matrix from the unmerged #8 branch. Those files have not been copied
here, and their tests are not claimed.

Official references:
[Fabric Terraform provisioning](https://learn.microsoft.com/fabric/fundamentals/understand-best-practices-fabric-cicd#how-can-you-automate-fabric-ci-cd)
and [capacity pause/resume](https://learn.microsoft.com/fabric/enterprise/pause-resume).

No cloud mutation was performed during validation. The separately approved
deployment operation completed with the exact four-resource plan; no other
resources, Azure RBAC assignments, or tenant settings were changed.
