# Infrastructure and bootstrap

[Repository map](../docs/engineering/repository-layout.md)

Issue #3 owns this Terraform root: the resource group, shared F2 capacity,
DEV/DEMO workspaces, approved Oracle/gateway VMs and private network. It includes
NAT/public IP, Bastion Developer and daily VM shutdown schedules; VM startup and
capacity pause/resume are not automated here. The VM images do not include the
configured Oracle database or commissioned gateway.

Use the [deployment handoff](../.azure/deployment-plan.md) for the unique shared
`.local` backend and private-input rules. Never initialize a second live state,
import/re-own resources or blindly apply empty state to existing resources.
Preserve resource addresses when consolidating local checkouts. A Git commit
does not change the deployed infrastructure.

The [Oracle/gateway reconstruction runbook](../docs/runbooks/oracle-gateway-reconstruction.md)
records guest setup, OCMT Managed ODP.NET registration, networking/logging fixes,
manual authentication and remaining CDC/recovery gates. Terraform provisioning
is distinct from guest commissioning, source seeding and workload acceptance.
#21 qualification and #19 source ownership remain separate; no additional
resources, privileges or cloud execution are authorized by these files.
See the [ownership matrix](../docs/deployment-ownership-support-matrix.md).
