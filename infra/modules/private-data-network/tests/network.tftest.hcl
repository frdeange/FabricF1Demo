mock_provider "azurerm" {}

variables {
  resource_group_name   = "existing-resource-group"
  location              = "swedencentral"
  name                  = "f1-data"
  vnet_address_space    = "10.42.0.0/27"
  oracle_subnet_prefix  = "10.42.0.0/28"
  gateway_subnet_prefix = "10.42.0.16/28"
  oracle_private_ip     = "10.42.0.4"
  gateway_private_ip    = "10.42.0.20"
}

run "private_subnets_and_single_listener_flow" {
  command = plan

  assert {
    condition     = azurerm_subnet.oracle.default_outbound_access_enabled == false
    error_message = "The Oracle subnet must not receive default outbound access."
  }

  assert {
    condition     = azurerm_subnet.gateway.default_outbound_access_enabled == false
    error_message = "The gateway subnet must not receive default outbound access."
  }

  assert {
    condition = (
      one([
        for rule in azurerm_network_security_group.oracle.security_rule : rule
        if rule.name == "allow-gateway-oracle-listener"
      ]).source_address_prefix == "${var.gateway_private_ip}/32" &&
      one([
        for rule in azurerm_network_security_group.oracle.security_rule : rule
        if rule.name == "allow-gateway-oracle-listener"
      ]).destination_address_prefix == "${var.oracle_private_ip}/32" &&
      alltrue([
        for rule in azurerm_network_security_group.oracle.security_rule :
        rule.access == "Allow" && rule.direction == "Inbound" &&
        rule.protocol == "Tcp" && rule.destination_port_range == "1521" && rule.priority == 100
        if rule.name == "allow-gateway-oracle-listener"
      ])
    )
    error_message = "The Oracle NSG must define the narrowly scoped gateway listener rule."
  }

  assert {
    condition     = contains([for rule in azurerm_network_security_group.oracle.security_rule : rule.name], "deny-all-inbound")
    error_message = "The Oracle NSG must explicitly deny all remaining inbound traffic."
  }

  assert {
    condition = (
      one([
        for rule in azurerm_network_security_group.gateway.security_rule : rule
        if rule.name == "allow-gateway-to-oracle-listener"
      ]).destination_address_prefix == "${var.oracle_private_ip}/32" &&
      one([
        for rule in azurerm_network_security_group.gateway.security_rule : rule
        if rule.name == "allow-gateway-to-oracle-listener"
      ]).source_address_prefix == "${var.gateway_private_ip}/32" &&
      alltrue([
        for rule in azurerm_network_security_group.gateway.security_rule :
        rule.access == "Allow" && rule.direction == "Outbound" &&
        rule.protocol == "Tcp" && rule.destination_port_range == "1521" && rule.priority == 100
        if rule.name == "allow-gateway-to-oracle-listener"
      ])
    )
    error_message = "The gateway NSG must allow only the Oracle listener flow."
  }

  assert {
    condition     = contains([for rule in azurerm_network_security_group.gateway.security_rule : rule.name], "deny-all-outbound")
    error_message = "The gateway NSG must explicitly deny all other outbound traffic."
  }

  assert {
    condition     = contains([for rule in azurerm_network_security_group.gateway.security_rule : rule.name], "deny-all-inbound")
    error_message = "The gateway NSG must explicitly deny all inbound traffic."
  }

  assert {
    condition     = contains([for rule in azurerm_network_security_group.oracle.security_rule : rule.name], "deny-all-outbound")
    error_message = "The Oracle NSG must explicitly deny all outbound traffic."
  }

  assert {
    condition = (
      length(azurerm_network_security_group.oracle.security_rule) == 3 &&
      length(azurerm_network_security_group.gateway.security_rule) == 3 &&
      alltrue([
        for rule in concat(
          tolist(azurerm_network_security_group.oracle.security_rule),
          tolist(azurerm_network_security_group.gateway.security_rule)
        ) :
        rule.access == "Deny" && rule.priority == 4095 && rule.protocol == "*" &&
        rule.source_port_range == "*" && rule.destination_port_range == "*" &&
        rule.source_address_prefix == "*" && rule.destination_address_prefix == "*" &&
        rule.direction == (rule.name == "deny-all-inbound" ? "Inbound" : "Outbound")
        if startswith(rule.name, "deny-all-")
      ])
    )
    error_message = "Each NSG must contain only one listener allow rule and complete inbound/outbound catch-all denies."
  }

}

run "reject_overlapping_subnets" {
  command = plan

  variables {
    gateway_subnet_prefix = "10.42.0.0/28"
  }

  expect_failures = [var.gateway_subnet_prefix]
}

run "reject_oracle_ip_outside_subnet" {
  command = plan

  variables {
    oracle_private_ip = "10.42.0.20"
  }

  expect_failures = [var.oracle_private_ip]
}

run "reject_non_private_address_space" {
  command = plan

  variables {
    vnet_address_space    = "198.51.100.0/27"
    oracle_subnet_prefix  = "198.51.100.0/28"
    gateway_subnet_prefix = "198.51.100.16/28"
    oracle_private_ip     = "198.51.100.4"
    gateway_private_ip    = "198.51.100.20"
  }

  expect_failures = [var.vnet_address_space]
}

run "reject_reserved_oracle_address" {
  command = plan

  variables {
    oracle_private_ip = "10.42.0.3"
  }

  expect_failures = [var.oracle_private_ip]
}

run "reject_gateway_broadcast_address" {
  command = plan

  variables {
    gateway_private_ip = "10.42.0.31"
  }

  expect_failures = [var.gateway_private_ip]
}

run "reject_malformed_gateway_address" {
  command = plan

  variables {
    gateway_private_ip = "not-an-ip"
  }

  expect_failures = [var.gateway_private_ip]
}

run "reject_subnet_outside_vnet" {
  command = plan

  variables {
    oracle_subnet_prefix = "10.42.1.0/28"
    oracle_private_ip    = "10.42.1.4"
  }

  expect_failures = [var.oracle_subnet_prefix]
}
