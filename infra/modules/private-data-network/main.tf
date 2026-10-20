resource "azurerm_virtual_network" "this" {
  name                = "${var.name}-vnet"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = [var.vnet_address_space]
  tags                = var.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_subnet" "oracle" {
  name                            = "${var.name}-oracle"
  resource_group_name             = var.resource_group_name
  virtual_network_name            = azurerm_virtual_network.this.name
  address_prefixes                = [var.oracle_subnet_prefix]
  default_outbound_access_enabled = false

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_subnet" "gateway" {
  name                            = "${var.name}-gateway"
  resource_group_name             = var.resource_group_name
  virtual_network_name            = azurerm_virtual_network.this.name
  address_prefixes                = [var.gateway_subnet_prefix]
  default_outbound_access_enabled = false

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_network_security_group" "oracle" {
  name                = "${var.name}-oracle-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  security_rule {
    name                       = "allow-gateway-oracle-listener"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "1521"
    source_address_prefix      = "${var.gateway_private_ip}/32"
    destination_address_prefix = "${var.oracle_private_ip}/32"
  }

  security_rule {
    name                       = "deny-all-inbound"
    priority                   = 4095
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "deny-all-outbound"
    priority                   = 4095
    direction                  = "Outbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_network_security_group" "gateway" {
  name                = "${var.name}-gateway-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  security_rule {
    name                       = "deny-all-inbound"
    priority                   = 4095
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "allow-gateway-to-oracle-listener"
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "1521"
    source_address_prefix      = "${var.gateway_private_ip}/32"
    destination_address_prefix = "${var.oracle_private_ip}/32"
  }

  security_rule {
    name                       = "deny-all-outbound"
    priority                   = 4095
    direction                  = "Outbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_subnet_network_security_group_association" "oracle" {
  subnet_id                 = azurerm_subnet.oracle.id
  network_security_group_id = azurerm_network_security_group.oracle.id

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_subnet_network_security_group_association" "gateway" {
  subnet_id                 = azurerm_subnet.gateway.id
  network_security_group_id = azurerm_network_security_group.gateway.id

  lifecycle {
    prevent_destroy = true
  }
}
