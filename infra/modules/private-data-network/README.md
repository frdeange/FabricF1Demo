# Private data network module

Related work: [#3](https://github.com/frdeange/FabricF1Demo/issues/3). This is a reviewable network foundation, not the completed execution environment or deployment approval.

This child module creates one caller-owned-resource-group VNet, dedicated Oracle and gateway subnets, and subnet-associated NSGs. Its only allowed workload flow is gateway-to-Oracle TCP 1521, with the Oracle listener rule restricted to the gateway host's supplied private IPv4 address.

The module intentionally creates no compute, NICs, public IPs, administration route, NAT, firewall, route table, or Private DNS. Both subnets disable default outbound access and both NSGs deny all other inbound and outbound traffic. As a result, this network cannot host a working VM or gateway until an egress design and private administration path are approved and implemented separately.

All address ranges and host IPs are mandatory inputs with validation. Select them only after IPAM review; no example deployment values are provided. The caller must pass the existing resource group and approved location. The existing Terraform root remains the sole owner of its backend, state, resource group, Fabric capacity, and workspaces.

## Interface and ownership

Required inputs are `resource_group_name`, `location`, `name`, `vnet_address_space`, `oracle_subnet_prefix`, `gateway_subnet_prefix`, `oracle_private_ip`, and `gateway_private_ip`. Optional `tags` defaults to an empty map. The module accepts only a canonical RFC1918 IPv4 `/27`, divided into two different `/28` subnets. Host addresses must be usable within their respective subnet; Azure-reserved addresses are rejected. IPAM approval and collision checks outside this VNet remain operator responsibilities.

Outputs are `virtual_network_id`, `subnet_ids`, and `network_security_group_ids`. No credentials or host addresses are output. Runtime resource IDs still belong in the operator environment, not public logs or Git. The module declares its provider source but has no provider configuration, backend, data source, or state access. The owning root supplies the AzureRM configuration and version selection.

Future caller code must consume the existing root's resource group references. Do not recreate or import its resource group, Fabric capacity, or workspaces; do not initialize a second operational root. Integration requires coordination with the root owner and review of the combined code. A review of this child module does not approve that future integration.

## Local validation without a deployment

Compatibility baseline: Terraform `>= 1.16.0, < 2.0.0` and AzureRM `5.10.0`, matching the existing root's declared versions. All test runs use `mock_provider "azurerm"` and `command = plan`; none apply resources or require Azure credentials.

To validate independently of the operational backend, create a disposable directory outside every checkout. Copy only this module's `.tf` files and `tests` directory. In that copy, set `required_version` to the baseline and add `version = "= 5.10.0"` to the existing `required_providers.azurerm` declaration. Do not copy any state, backend metadata, `.terraform`, private variable files, or credentials. Use a separate `TF_DATA_DIR` and a clean Terraform CLI configuration, clear Azure and Terraform credential/argument environment variables in the validation process, and run from the copy:

```powershell
terraform init -backend=false -input=false
terraform validate
terraform test
terraform fmt -check -recursive
```

Initialization restores the declared provider dependency; it does not initialize a backend. The test harness is never an operational root or a deployment entry point. Keep its generated lockfile and provider directory outside Git and remove the disposable directory after validation. A mock test verifies configuration and addressing rules, not live routing, firewall behavior, quotas, policy, or service compatibility.

## Deployment and recovery gates

Before adding workload resources or applying this foundation, the owners must approve the exact target, identities, IPAM, egress, private administration, VM sizing and bootstrap, Oracle/Mirroring compatibility, budget, and recovery actions. This module does not install or register a gateway and does not automate any credential or license step. NSGs are stateful; response traffic to an allowed connection is permitted, but new sessions remain subject to the rules. Azure platform traffic has separate platform handling; these rules are not a claim of host-level isolation from every platform service.

The resources use `prevent_destroy` to block planned deletion or replacement while their declarations remain present. It does not protect resources if their configuration is removed or against out-of-band operations. Do not remove those guards or declarations as an unreviewed teardown. Any later execution must use the original owner's single external state, verify its expected resources before planning, stop on missing or unexpected state, and review a saved plan before separately approved application. Never apply this module as a new root against an empty state or import/re-own existing resources.

Recovery remains an approved operator procedure: retain and protect the original state, stop concurrent operations on that backend, review failed or partially completed operations with the owner, and restore configuration or perform a separately approved corrective plan. Do not blindly reapply, destroy, or roll back state to hide drift. No state inspection or recovery action is authorized by this README.
