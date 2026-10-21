# Oracle and gateway reconstruction

[Runbooks](README.md) | [Infrastructure](../../infra/README.md)

Issue #3 preserves the deployed infrastructure configuration and these
commissioning lessons. Coordinate Oracle schema/seed ownership with #19 and
host/gateway qualification with #21. This is a reconstruction checklist and
automation assessment, not evidence of a clean-machine rehearsal or permission
to run cloud operations.

## What is reproducible today

The Terraform root in `infra` describes the resource group, shared F2 capacity,
two workspaces, private network, NAT/public IP, Bastion Developer, NICs, Linux
Oracle VM, Windows gateway VM and daily VM shutdown schedules. Provider versions
and image versions are pinned. It does **not** install database/gateway software,
configure Oracle logging, register the gateway or create the Fabric connection
and mirror. Creating the VMs is not a complete commissioning procedure.

The recorded guest baseline was Oracle AI Database Free 23.26.3, AL32UTF8,
CDB `FREE`, PDB `FREEPDB1`, Oracle Linux 9.8 and Windows Server 2022. The gateway
version was 3000.334.9. PowerShell 7.4.6 was installed for the DataGateway module.
These are historical observations, not a recommendation to install obsolete
versions. Before a new build, qualify supported versions, module requirements,
Oracle edition/licensing and Mirroring compatibility together.

The Oracle schema and deterministic seed adapter were merged separately in
[PR #26](https://github.com/frdeange/FabricF1Demo/pull/26). Use those source-owned
artifacts from a revision containing that PR; do not recreate them in Terraform
or duplicate session-only generated SQL into the repository.

## Safety and local inputs

Use the single canonical local state described in the
[deployment handoff](../../.azure/deployment-plan.md#local-state-rule). Private
inputs and SSH keys belong in the shared ignored `.local\secrets` directory;
state/backups/plans belong in `.local\terraform`. Ignore rules are not access
control, encryption or recovery. Never commit their contents or include them
in a release archive. Do not reuse saved plans from before the state relocation.

Existing environments: use their existing state, resource addresses, gateway
registration and mirror. Stop on missing state or unexpected resource changes;
never initialize empty state and apply to recreate existing resources.
New independent environments require their own approved names, isolated state,
network/address review, identity, region, cost and rollback decisions. This root
contains pilot-specific names, addresses and region checks; it is not a generic
multi-environment module.

Keep one operator. Do not run Terraform/REST/portal writers concurrently. Do not
restart VMs or resume F2 without approval for the operating window and costs.
Never destroy/recreate a VM, grant access, overwrite a gateway registration,
delete archives or reset source data as an installation shortcut.

## Ordered reconstruction and commissioning

| Stage | Required action | Exit condition |
| --- | --- | --- |
| Preflight | Confirm approved identity, subscription/region, availability, image versions, names, disk sizing, licenses, network policies and costs. Initialize the correct existing backend and review an exact plan. | No unintended create, delete, replacement or access change; approved target and rollback. |
| Infrastructure | Separately approve and apply the reviewed Terraform plan. Keep resource addresses stable. | VMs, NICs, routes and NSGs match the approved configuration; no public VM NICs. |
| Oracle guest | Install/configure the qualified Oracle Free package, database services, listener and PDB startup persistence on the Linux VM. | Database/PDB open after reboot, listener reachable, AL32UTF8 and expected version verified. |
| Source data | Use the source-owned schema once and explicitly seed using its validated MERGE adapter under the approved source identity. | Counts and all-column reconciliation match; repeating the seed does not duplicate or reset data. |
| Oracle CDC prerequisites | Back up before/after ARCHIVELOG changes; configure archive destination, database and five-table supplemental logging and the separately approved sync account/grants. | Writable PDB, usable archived redo, sufficient disk space and required grants/logging verified. |
| Gateway guest | Install the standard x64 gateway and qualified PowerShell/DataGateway tooling on the Windows VM. | Gateway installation/version present; service healthy. Installation alone is not registration. |
| Oracle client | Install OCMT x64 Managed ODP.NET on the **gateway VM**, then verify the .NET Framework provider factory. | `Oracle.ManagedDataAccess.Client` loads in a fresh 64-bit Windows PowerShell process. |
| Registration | Authenticate interactively as the approved gateway operator and register the gateway, protecting its recovery key. Recover an existing registration only through a separately reviewed recovery flow. | Intended gateway cluster registered/online; no duplicate/overwritten cluster. |
| Fabric | Resume the shared capacity only for an approved window; wait for ready state. Configure the gateway-backed Oracle connection and mirror. | Exact connection and explicit five-table scope saved/read back; rows actually queryable. |
| Acceptance | Run baseline reconciliation, bounded insert/update/delete/rollback and outage/recovery checks. | Exact source/destination columns, timestamps/currency, no duplicates and unchanged original data; no unexplained CDC gaps. |
| Stop | Coordinate active users/jobs, pause F2 and deallocate both VMs. | Paused/deallocated status verified; residual charges explained. |

### Oracle/network corrections discovered during commissioning

The NSG listener allow rule was insufficient: the **Linux host firewall** also
needed a persistent rule permitting only the gateway's private address to TCP
1521. Preserve this source restriction when scripting; do not open the listener
to the Internet or disable the firewall. Check listener/PDB readiness separately
from TCP reachability.

ARCHIVELOG enabled did not mean archived redo existed: the first redo log had
not switched. A separately approved `ALTER SYSTEM ARCHIVE LOG CURRENT` generated
usable archives. A future installer must verify actual archive availability and
disk headroom, not just `V$DATABASE.LOG_MODE`. No automatic archive purge was
approved; retention/cleanup needs its own recovery-aware policy. The approved
sync identity is distinct from the application owner; do not use SYS as the
Fabric connection identity.

Bastion Developer connectivity required inbound SSH/RDP from its observed
platform source, declared in the workload configuration. External governance
later removed the gateway NSG rule. A compliant, owner-agreed resolution is
still required; do not disable governance or loop Terraform repairs against it.
An inaccessible Bastion session is not evidence of an Oracle/provider failure.

### Gateway and Oracle provider corrections

The gateway's bundled Oracle assemblies did not satisfy this Mirroring path.
The observed error was "Cannot load managed ODP.NET driver" / "Unable to find
the requested .Net Framework Data Provider". Copying a DLL or detecting a
bundled assembly was not enough.

OCMT 19.32 x64 was downloaded from Oracle, checked against Oracle's published
SHA256 and checked for a valid Oracle America signature. The recorded SHA256:

```text
DBD0360010661267B1BE764AC841ED5172A7AD4082F0BFBB16FA24D6C1BCAFC8
```

Do not assume a mutable download URL still serves those bytes. A future
installer must require a reviewed artifact version/hash and valid expected
publisher; stop on a mismatch rather than relaxing verification.

A silent InstallShield attempt returned `ResultCode=-3`; a response file was
required. Success came from the GUI in Bastion: **Custom > Managed ODP.NET**.
No tested silent OCMT response file or fully unattended bootstrap is delivered
here. Do not reuse the failed `/s /v...` invocation or hand-edit machine.config
as an unqualified workaround.

Validate in **64-bit Windows PowerShell 5.1 (.NET Framework)** on the gateway
VM, not PowerShell 7 (.NET) or the local developer machine:

```powershell
$ErrorActionPreference = 'Stop'
if (-not [Environment]::Is64BitProcess -or $PSVersionTable.PSEdition -ne 'Desktop') {
    throw 'Use 64-bit Windows PowerShell 5.1 on the gateway VM.'
}
$factory = [System.Data.Common.DbProviderFactories]::GetFactory(
    'Oracle.ManagedDataAccess.Client'
)
$factory.GetType().Assembly.FullName
Get-Service -Name PBIEgwService -ErrorAction Stop
Test-NetConnection -ComputerName <approved-oracle-private-ip> -Port 1521
```

The verified factory loaded assembly version 4.122.19.1 after OCMT installation;
the bundled 4.122.23.1 assembly alone had not solved registration. Check actual
factory loading rather than testing a file path or hard-coding those historical
assembly versions as a permanent compatibility rule. Service restart initially
failed (error 1064); a later start and the user's VM reboot restored a healthy
service. A future script must surface restart/reboot failures and require a
fresh post-reboot check, not report installation success from an exit code only.

### Gateway registration boundary

The installed DataGateway module required PowerShell 7.4, despite broader
minimums in some overview documentation. Qualify/pin the actual module version
and inspect its declared requirements and `Get-Command` parameter types.
Installation can be scripted with the supported `Install-DataGateway` cmdlet
and an approved installer; license acceptance must be explicit.

The successful interactive command shape on the Windows VM was:

```powershell
Connect-DataGatewayServiceAccount -ForceDeviceCodeAuthentication $true
$recoveryKey = Read-Host 'Recovery key' -AsSecureString
Add-DataGatewayCluster -GatewayName '<approved-gateway-name>' -RecoveryKey $recoveryKey
```

This block is a **state-changing registration step**, not a diagnostic or a
rerunnable installer. First check for an existing registration and choose a
reviewed recovery path when one exists. The Boolean `$true` is required here;
using the parameter as a switch failed. The recovery key must meet the gateway
minimum of eight characters; use a strong private key and retain it securely.
Do not pass it on a command line, print it or log it. Do not use
`-OverwriteExistingGateway`, create a service principal or broaden permissions
to avoid user authentication. The gateway region follows its cloud
registration/tenant configuration, not merely the Azure VM's region.

### Fabric and data verification boundary

The intended connection and mirror currently share the display name
`f1-dev-oracle-mirroring`. Do not recreate or delete either during checks.
Connection settings use the qualified Oracle PDB service through the gateway,
Basic authentication with the approved sync identity and Organizational privacy.
Resolve private bindings at execution time rather than storing IDs/credentials
in source control.

The accepted scope is the five `F1APP` tables `F1_EVENT`, `F1_ZONE`,
`F1_PRODUCT`, `F1_PRICE` and `F1_BUNDLE_COMPONENT`, explicitly selected.
`AUDSYS.AUD$UNIFIED` is excluded; it was not modified to make it mirrorable.
New tables require a deliberate scope/logging update. Auto-all mode would
include future tables and was superseded by the user's explicit five-table
decision.

A paused F2 produced generic Internal Server Error in the assistant. Wait for
capacity readiness before diagnosing connection failures. A connection test
reported Online before full commissioning; it did **not** qualify driver
loading, LogMiner or replicated data. Likewise, Running/Replicating status
does not prove exact data or reliable CDC.

Use the mirrored database's SQL endpoint to query the actual table values.
For the observed endpoint, the SQL database name was the mirror display name,
not an item GUID. Use properly scoped Entra authentication; do not embed tokens
or passwords in scripts. Compare every canonical column, normalize timestamp
sessions to UTC and compare numeric/currency precision, not just row counts.
Direct OneLake file verification was not performed in this commissioning.

## Automation assessment

| Candidate | Recommended implementation | Qualification/safety gate |
| --- | --- | --- |
| Azure resources | Keep existing Terraform resource/module ownership and pinned providers/images. | No resource renaming, imports, extra state or automatic replacement. Review image availability before a new build. |
| Gateway software | Separate versioned Windows installation script using approved signed artifacts and supported gateway install tooling; check installed versions before changing anything. | Pin version/hash/module requirements, fail on installer/service/reboot errors, rerun twice on a disposable approved VM. Never download arbitrary "latest" on every apply. |
| OCMT provider | Installer-specific reviewed response file or other Oracle-supported unattended route, followed by a fresh x64 Framework factory check. | Current silent attempt failed; response-file creation, license review and clean-machine/reboot rehearsal still required. Keep manual installation as a truthful interim gate. |
| Host connectivity | Small Oracle-Linux configuration/check script for persistent restricted firewall rule, listener/PDB readiness and restart persistence. | No blanket firewall disable, broader ingress or implicit Oracle container/privilege change. Test first/second run and reboot. |
| Oracle CDC prerequisites | Source-owned SQL/RMAN checks and explicitly approved setup steps, separate from seed execution and cloud resource lifecycle. | Backups before/after ARCHIVELOG transition, inspect existing settings/grants before modifying, no archive purge or data reset. |
| Gateway registration | Human-assisted checkpoint with secure recovery key and existing-cluster detection. | Do not put interactive credentials/recovery material in Terraform variables, extension public settings, output or logs. |
| Fabric bindings | Separately owned, parameterized connection/mirror configuration with discovery, saved-definition readback and data checks. | User-approved table scope, existing-object detection, no competing portal/API writer or delete/recreate loop. |
| Preflight/acceptance | Read-only guest checks plus separately invoked, guarded synthetic DML/recovery tests. | Nonzero exit for failures, bounded waits, recorded exact values and no automatic restart, repair or cleanup. |

Prefer keeping Terraform declarative and guest configuration explicit. A VM
extension may later invoke a qualified guest script, but that is a separate
reviewed infrastructure change: extension rerun/reboot behavior, secret handling
and recovery must be proven. Do not add `local-exec`/`remote-exec` provisioners
that silently install software, use personal sessions or mutate databases on
every Terraform run. Never pass database passwords or recovery keys as public
extension settings. Terraform `sensitive` flags redact display; they do not
remove secrets from local state.

## Current acceptance limits and reproducibility gate

Historical commissioning verified the original 13 destination rows (table
counts 1/2/4/4/2) and ten synthetic inserted event keys/names with non-null source
timestamps. Source canonical all-column reconciliation passed before those
inserts, and original destination row fingerprints were captured. This is not
full all-column source/destination reconciliation.

The three-update test was started and interrupted; its commit/replication
outcome is unknown. Inspect source and destination before repeating it.
Delete, rollback, outage/recovery, exact timestamp/currency reconciliation and
the complete CDC acceptance remain pending. ORA-65040 appeared during LogMiner
registration from the PDB even while inserts propagated. Do not call it fixed,
switch the connection to CDB root or broaden grants as an assumed workaround.

Both VMs were deallocated and F2 paused at the last verified shutdown. The user
subsequently chose to keep them off and leave these tests pending. No new
startup, repair or source writes are authorized by this runbook.

Before calling the rebuild agile/repeatable, prove a clean approved build:
record artifact versions/digests, execute guest setup twice and after reboot,
register/recover without duplicates, prove the complete acceptance suite, then
verify shutdown. This rehearsal has **not** been performed. NAT, public IP,
disks, storage and other retained services can still cost money while compute
is stopped; NAT cannot be paused. Do not delete resources to reduce those costs
without a separately reviewed approval.

## References

- [Oracle Mirroring setup](https://learn.microsoft.com/fabric/mirroring/oracle-tutorial)
- [Oracle Mirroring limitations](https://learn.microsoft.com/fabric/mirroring/oracle-limitations)
- [Gateway installation](https://learn.microsoft.com/data-integration/gateway/service-gateway-install)
- [Gateway PowerShell overview](https://learn.microsoft.com/powershell/gateway/overview)
- [Install-DataGateway](https://learn.microsoft.com/powershell/module/datagateway/install-datagateway)
- [OCMT downloads](https://www.oracle.com/database/technologies/appdev/dotnet/ocmt.html)
