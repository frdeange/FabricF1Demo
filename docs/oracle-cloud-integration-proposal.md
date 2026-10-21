# Oracle cloud integration proposal (#19)

**Status:** integration reference, not deployment evidence. On 2026-10-20 the
user explicitly approved applying the minimum Oracle/gateway resources in the
existing target resource group and region, with variable Azure charges and no
numeric cost ceiling. The user separately approved accepting Oracle Database
26ai Free terms and installing it. Execution was transferred to the existing
root-operating session as the sole operator; this source worktree does not
operate that backend. No successful Oracle/gateway deployment, database load,
or native Mirroring result has yet been reported here.

Those approvals do not authorize new role assignments, changes to existing
bootstrap resources or `f1-pro`, destructive recovery, or resuming F2. Resource
candidates below are not assertions of deployed resources. Independent final
diff review and the user's reviewed-result approval remain required before PR
creation; an agent must not submit that approval as the user.

## Target and ownership

The requested outcome is an Oracle source on an Azure VM, a standard Windows
On-premises Data Gateway, and native Fabric Oracle Mirroring verified in OneLake.
The intended target labels are the GPS Demo subscription, Sweden Central, and
the `f1-dev` workspace. Keep `f1-pro` and the existing bootstrap resources
unchanged. The demo audience is internal, the user has not requested a cost
ceiling, and both VMs must be deallocated every day at 18:00
`Europe/Stockholm`, with manual start only.

The apply approval above supersedes the earlier preparation-only boundary.
The latest read-only inventory reported only the Fabric capacity in the target resource
group and no Oracle VM, gateway, VNet, egress service, or private admin path.
The capacity was paused at that observation. Refresh target state immediately
before any proposed operation; do not resume capacity as part of this proposal.

| Owner | Owns | Integration boundary |
| --- | --- | --- |
| #3 | The single Terraform root, existing bootstrap resources, and its one external local state | Integrates caller resources through its existing root and the approved operator. No second root/state, import, re-ownership, state read, or checkout edit is proposed here. |
| #21 | Network, Oracle host, Windows gateway host, and their operational qualification | Supplies approved IPAM, routes, egress/admin choices, VM bootstrap, and host/gateway acceptance. |
| #19 | Oracle-native schema/seed and native Mirroring qualification | Keeps the fixture source limited to events, circuit zones/base capacity, products/SKUs, bundle components, and effective-dated prices. |
| #18 | Synthetic fixture/generator and canonical contracts | Remains the only owner of logical fixture generation; #19 consumes its generated Oracle files rather than copying its generator or data. |

The existing root and its single external local state remain the only
operational configuration. The user explicitly transferred execution to the
existing root session; all other sessions must avoid parallel root/state
operations. Bootstrap review and documentation corrections were reported;
publication and final integration review must be established from actual Git
and review evidence, not inferred from this handoff.

## Proposed root integration contract

Reuse the merged [PR #25 network module](https://github.com/frdeange/FabricF1Demo/pull/25);
do not duplicate its VNet/subnet/NSG implementation. The root call belongs in
the existing #3 root only after the module is available on the one agreed
integration branch. The caller's inputs and outputs are:

| Module contract | Root binding |
| --- | --- |
| Required inputs: `resource_group_name`, `location`, `name`, `vnet_address_space`, `oracle_subnet_prefix`, `gateway_subnet_prefix`, `oracle_private_ip`, `gateway_private_ip` | Use the root's existing resource-group reference and approved region. Obtain all address and host IP values from #21 IPAM; do not commit guessed CIDRs or host addresses. |
| Optional input: `tags` | Pass only the existing root's non-sensitive tags. |
| Outputs: `virtual_network_id`, `subnet_ids.oracle`, `subnet_ids.gateway`, `network_security_group_ids.oracle`, `network_security_group_ids.gateway` | Feed the existing root's VM NICs and any separately approved route/admin/egress resources. Do not log runtime resource IDs in public output. |

The module currently enforces one RFC1918 `/27`, two `/28` workload subnets,
fixed private host IP inputs, and a default-deny NSG baseline. It creates no VM,
NIC, egress, route, DNS, Bastion, storage, or administrative access. Both
subnets disable default outbound access. Its sole workload allowance is
gateway-to-Oracle TCP 1521; all other new inbound and outbound flows are denied.
Those controls are a secure foundation, not an operational network.

Conceptually, the existing root will call the module with values supplied by
its own variables and references; the following is an interface sketch, not
deployable configuration:

```hcl
module "private_data_network" {
  source = "./modules/private-data-network"

  resource_group_name     = azurerm_resource_group.existing.name
  location                = var.approved_location
  name                    = var.approved_network_name
  vnet_address_space      = var.ipam_approved_vnet_cidr
  oracle_subnet_prefix    = var.ipam_approved_oracle_subnet
  gateway_subnet_prefix   = var.ipam_approved_gateway_subnet
  oracle_private_ip       = var.ipam_approved_oracle_host_ip
  gateway_private_ip      = var.ipam_approved_gateway_host_ip
  tags                    = var.approved_tags
}
```

The module's current `/27` shape cannot also contain Azure Firewall's dedicated
`AzureFirewallSubnet` (minimum `/26`). Keeping two `/28` workload subnets and
adding a `/26` firewall subnet requires at least a `/25` VNet, plus an IPAM
collision review. This is a change to the #25 module contract and must be
designed/reviewed with #3/#21 before integration; do not make an out-of-band
address change or silently copy the module.

## Minimum functional resource proposal

These are candidates for the single owner-controlled root, not a deployed
inventory or an exact reviewed plan. The operator must confirm regional SKU availability, quotas, naming,
addresses, backup destination, and source/gateway compatibility before the root
is changed.

| Resource | Candidate | Minimum functional requirement / owner |
| --- | --- | --- |
| Network module | PR #25 child module, subject to the selected egress/admin design | #3 calls it from the existing root; #21 supplies reviewed IPAM. Preserve private IPs and no VM public IPs. |
| Oracle VM | Linux Oracle Linux 9, `Standard_B2s`, 64-GB E6 OS disk plus 64-GB E6 data disk | #21 owns host/bootstrap; #19 owns schema, seed, and Oracle qualification. Oracle Free's 2-CPU, 2-GB database-memory, and 12-GB user-data limits require an isolated synthetic-only source. Measure RAM, I/O, and redo before accepting the size. |
| Gateway VM | Windows Server 2022 Desktop Experience, `Standard_F8s_v2`, 128-GB E10 OS/spool disk | #21 owns host/gateway qualification. The 8-core candidate meets Microsoft's 8-core recommendation; smaller 4-core candidates are below that recommendation. No public IP. Install the current supported Standard gateway release only after rechecking its exact version, hash, and terms. |
| Fabric Mirror | One native Oracle Mirroring item and OneLake mirrored database in `f1-dev` | #19 owns setup and proof. Confirm workspace capacity/eligibility, workspace role, gateway region/reachability, and exact Oracle Free LogMiner support first. The prior inventory observed F2 paused; do not resume it implicitly. |
| Human administration | Bastion Developer candidate, browser RDP to Windows and SSH to Linux sequentially | #21/#3 confirm the operator and least-privilege Azure/VM roles. No public VM IP. The VM NSGs must permit only the verified Bastion-to-target administration source and ports; do not add a broad VNet or Internet inbound rule. |
| Scheduled deallocation | Azure Automation account, managed identity, daily runbook schedule at 18:00 `Europe/Stockholm` | #3/#21 own the root/operations integration. Runbook deallocates both named VMs, checks the resulting deallocated power state, and logs its job result. Do not create a start schedule. The identity's role must be limited to the two VM resources. |
| Recovery destination | Separate, owner-approved backup destination; candidate is encrypted Oracle RMAN backup plus archived redo outside the Oracle VM | #3/#21 select and own the storage/network/retention implementation; #19 tests a restore. No independent backup storage was found in the prior inventory. Keep the gateway recovery key and database credentials in an approved secret store, never in Git or public logs. |

### Egress and private administration alternatives

No approved shared firewall/proxy or private administration route was identified
in the reported subscription inventory. That does not rule out an enterprise
service outside the queried resource group/subscription; #3/#21 should confirm
whether one exists before new resources are proposed.

| Option | What it provides | Network/root impact | Assessment |
| --- | --- | --- | --- |
| Existing enterprise egress + private admin route | Reuses an already approved firewall/proxy and private access path, if the owner confirms the route, policy, DNS, capacity, and target authorization | Lowest new resource count. The owner must provide reachable egress and admin contracts, not just a service name. The current module NSGs still need precise approved rules. | First option to investigate; not available until confirmed. |
| Azure Firewall Basic + Bastion Developer | FQDN application rules for HTTP/S and private browser access to same-VNet VMs; Bastion Developer is free, supports Sweden Central, does not need a dedicated subnet, and allows only one VM connection at a time | Firewall requires its own `/26` subnet; with the module's two `/28`s this means redesigning the current `/27` module/VNet to at least `/25`. Firewall Basic uses Azure DNS (no DNS proxy), supports SNI-based HTTP/S FQDN filtering, but not network-level FQDN filtering for arbitrary protocols. Bastion requires VM/NIC Reader access plus VM login rights and target RDP/SSH exposure to the verified Bastion path. | Smallest self-managed fallback to evaluate if Relay HTTPS mode and all egress dependencies are proven. A candidate only, not a decision. |
| NAT Gateway + Bastion Developer | Outbound SNAT without public VM addresses plus the same sequential private admin option | NAT attaches to workload subnets; it does not filter or authorize destination FQDNs. The current deny-all NSGs remain blocking until narrowly reviewed outbound rules are added. Allowing broad outbound TCP 443 would not be equivalent to FQDN filtering. | Potentially lower complexity than a firewall, but not equivalent security. Do not select if FQDN-restricted egress is required. |
| Azure Firewall Standard + Bastion Developer | FQDN filtering for network rules in addition to HTTP/S application rules, plus Azure DNS proxy/custom DNS | Also requires a dedicated `/26` firewall subnet and at least the same `/25` address-plan change. Adds higher fixed and data-processing charges than Basic. | Use only if a required gateway/source flow cannot be constrained through Basic HTTPS application rules or a shared service. |

**Gateway flow design:** run the gateway in HTTPS mode and test its actual
network-port diagnostics against the Fabric tenant. Microsoft's gateway
documentation says the gateway requires no inbound port; outbound TCP 443 is
used by HTTPS-mode Azure Relay, and the registered gateway can be limited to
Relay endpoints. Initial installation, registration, authentication, gateway
management, certificate revocation, and OS/software updates have additional
FQDN dependencies. Create a staged build/update policy and a separately
verified runtime allowlist; do not enable the generic port list wholesale.
If any required path needs AMQP 5671/5672 or other non-HTTP/S traffic, Firewall
Basic cannot supply FQDN network rules for it; use a qualified shared route or
re-evaluate Standard. Preserve default deny for all other traffic.

For private admin, Bastion Developer fits an internal development/demo session
pattern: Sweden Central is listed, the VMs can remain private, and two hosts can
be visited one at a time. It is shared-pool, has no VNet peering or concurrent
connections, and Microsoft says it is not suitable for production workloads.
Its target-side NSG source must be confirmed from the current service guidance
and tested; the module currently denies all target inbound, so RDP 3389 and SSH
22 are not available until an exact, narrow, owner-reviewed rule is agreed.
Dedicated Bastion Basic/Standard would require a reserved `/26` subnet and
public IP and is not compatible with the current `/27` allocation.

## Daily shutdown and manual start

Do not rely on the VM auto-shutdown default: Microsoft's VM page says the time
zone defaults to UTC. Use one Azure Automation daily schedule explicitly set to
`Europe/Stockholm` and a cloud runbook with an exact two-VM allowlist. Microsoft
documents that Automation schedules handle daylight-saving time and accept
either an IANA or Windows time-zone ID. The runbook must call deallocation (not
guest shutdown alone), verify both VMs reach `VM deallocated`, and report a
failure rather than silently treating it as success. Configure no automatic
start; the approved operator starts the VMs manually and checks Oracle,
gateway, and Mirror health. The Automation account, role assignment, runbook,
schedule, job logging/retention, and any monitoring cost still need owner
approval and pricing.

## Identity, source configuration, and recovery

- Use separate Oracle DBA/schema/seed and Mirroring synchronization identities.
  Keep the Mirroring account scoped to the dedicated synthetic database and
  grant only the exact Microsoft-documented Mirroring privileges after the
  Oracle edition and PDB/CDB behavior are qualified. The documented privilege
  set is broad (including catalog, dictionary, table, flashback, and LogMiner
  access); do not grant it to the VM administrator or seed identity.
- The Azure operator, #3 root operator, #21 host operator, Fabric workspace
  administrator, Oracle DBA, and Mirroring principal are separate responsibilities.
  Their real names/IDs are not known and must be resolved privately before
  role assignments or sign-in. The previously observed CI OIDC read access is
  not write authority.
- Use only internal synthetic fixture rows from #18. Preserve immutable
  canonical keys and the `(sourceSystem, sourceTenant, sourceEntity, sourceKey)`
  cross-reference, source/effective/ingestion timestamps, ISO currency and
  integer minor-unit prices. Oracle owns only catalog/master facts; orders,
  reservations, and sold-allocation state remain outside Oracle.
- Enable only the Oracle settings proven necessary for Mirroring on the isolated
  synthetic database: write mode, `ARCHIVELOG`, supplemental logging, and
  documented LogMiner privileges. Measure redo volume and storage before setting
  retention; the earlier 48-hour retention suggestion is a sizing hypothesis,
  not a fixed value or approved policy. Back up before and after configuration
  changes; never delete redo to hide lag.
- Use an independent backup destination and test restore before calling the
  source recoverable. The candidate is RMAN full/incremental backup plus redo
  to separately approved encrypted storage with a tested restore procedure.
  Storage location, network path (service endpoint vs private endpoint), access
  identity, retention, RPO/RTO, and cost remain unselected. A disk on the Oracle
  VM is not an independent backup. A VM image/backup alone is not proof of an
  Oracle-consistent database restore.
- Keep the gateway recovery key and source credentials in an approved secret
  store; verify the gateway can be rebuilt and re-registered without putting
  secrets into Terraform variables, state output, fixtures, logs, or Git.

## Cost envelope and unknowns

Current Azure retail pricing lookup for Sweden Central returned the following
compute rates (USD, Consumption; rate records effective 2025-10-01):

| Component | Candidate | Published rate | 730-hour reference |
| --- | --- | ---: | ---: |
| Oracle Linux VM | `Standard_B2s` | $0.0432/hour | $31.54/month |
| Windows gateway VM | `Standard_F8s_v2` | $0.74/hour | $540.20/month |
| Both VMs, compute only | — | $0.7832/hour | $571.74/month |
| Bastion Developer | Free tier | $0/hour | $0/month |

The 730-hour figure is a continuous-running reference, not the requested
operating pattern. Deallocation at 18:00 reduces compute charges while running;
manual start means actual daily hours are variable. Managed disks continue to
incur charges while VMs are deallocated.

The proposed disks are Oracle E6 x2 and gateway E10 x1. The previous estimate
was $19.20/month for those disks, but the current exact-SKU pricing lookup
returned no disk meters, so that is not a current quote. Current lookups also
returned no pricing rows for Firewall Basic, NAT Gateway Standard, or Bastion
Developer; Bastion's free status is confirmed in its SKU documentation, while
the other prices remain unknown rather than zero. The all-in cost is therefore
not yet computable.

Still to price/confirm: egress fixed/data-processing charges, public IP, backup
storage and operations, Automation/jobs/logging, firewall log retention,
Windows licensing/activation, Oracle Free hosting and terms, VM/disk backup,
Fabric F2 runtime and capacity use, data transfer, and any external shared
service charge. The user does not require a cap; these unknowns must still be
shown in the final exact approval packet, not hidden or treated as free.

## Integration and acceptance sequence

1. The sole root operator preserves the existing bootstrap changes and external
   state, consumes the merged PR #25 module, and validates/reviews the complete
   integration diff. Other sessions do not initialize, plan, or apply against
   that backend. Retain final-result user approval before PR creation.
2. #21 confirms whether approved shared egress/admin paths exist. Otherwise,
   compare the above candidates, settle IPAM, the Firewall subnet/module impact,
   Bastion target NSG source, private DNS needs, gateway HTTPS mode, and exact
   FQDN/port tests. No default route or broad outbound rule is implied.
3. #3/#21 finalize VM/dependency resources, backups, recovery, schedule/identity
   role, quotas, regional SKU availability, and complete costs. #19 qualifies
   the exact Oracle Free build, licensing, Mirroring compatibility, CDB/PDB
   grants, supported table types, and gateway version before source changes.
4. Review the single-root diff and sanitized plan. The apply/spend and Oracle
   terms/install approvals are recorded above; do not restart those generic
   approval questions. Stop only for concrete changes outside their scope or
   a failed prerequisite. No second state, bootstrap
   re-creation, resource import, F2 resume, or unrelated workspace change.
5. Deploy the native Oracle Mirroring item in `f1-dev`; verify the OneLake
   mirrored database and SQL endpoint. Apply a bounded synthetic-only test:
   10 inserts, 3 updates, 2 deletes, rollback checks, key/value/count
   reconciliation, then gateway outage and recovery reconciliation. Record
   actual results before claiming success.
6. Verify the daily schedule on both VMs reaches `VM deallocated` at 18:00
   Stockholm time across a daylight-saving transition and confirm there is no
   automatic start. Test the backup restore and gateway re-registration path.

## Official references

- [PR #25 private data network module](https://github.com/frdeange/FabricF1Demo/pull/25)
- [Fabric Oracle Mirroring](https://learn.microsoft.com/fabric/mirroring/oracle)
- [Oracle Mirroring limitations](https://learn.microsoft.com/fabric/mirroring/oracle-limitations)
- [On-premises data gateway communication and ports](https://learn.microsoft.com/data-integration/gateway/service-gateway-communication)
- [Azure Firewall features by SKU](https://learn.microsoft.com/azure/firewall/features-by-sku)
- [Azure NAT Gateway overview](https://learn.microsoft.com/azure/nat-gateway/nat-overview)
- [Azure Bastion SKU comparison](https://learn.microsoft.com/azure/bastion/bastion-sku-comparison)
- [Azure Bastion Developer quickstart](https://learn.microsoft.com/azure/bastion/quickstart-developer-sku)
- [Manage Azure Automation schedules](https://learn.microsoft.com/azure/automation/shared-resources/schedules)
- [New-AzAutomationSchedule and time-zone parameter](https://learn.microsoft.com/powershell/module/az.automation/new-azautomationschedule)
- [Azure VM auto-shutdown](https://learn.microsoft.com/azure/virtual-machines/auto-shutdown-vm)
- [Oracle AI Database Free](https://www.oracle.com/database/free/)
- [Oracle Free Use Terms](https://www.oracle.com/downloads/licenses/oracle-free-license.html)
