output "virtual_network_id" {
  description = "ID of the private virtual network."
  value       = azurerm_virtual_network.this.id
}

output "subnet_ids" {
  description = "Subnet IDs keyed by workload role."
  value = {
    oracle  = azurerm_subnet.oracle.id
    gateway = azurerm_subnet.gateway.id
  }
}

output "network_security_group_ids" {
  description = "Network security group IDs keyed by workload role."
  value = {
    oracle  = azurerm_network_security_group.oracle.id
    gateway = azurerm_network_security_group.gateway.id
  }
}
