locals {
  workload_name = "f1demo"
  vnet_cidr     = "10.200.100.0/27"
  oracle_ip     = "10.200.100.4"
  gateway_ip    = "10.200.100.20"

  tags = {
    project = "f1demo"
    purpose = "oracle-mirroring-pilot"
  }

  # Source used by Bastion Developer's shared pool to reach the VMs; verify on first connection.
  bastion_source = "168.63.129.16/32"

  platform_rule = {
    name                       = "allow-azure-platform"
    priority                   = 190
    direction                  = "Outbound"
    protocol                   = "*"
    destination_port_ranges    = ["53", "80", "32526"]
    source_address_prefix      = "*"
    destination_address_prefix = "168.63.129.16/32"
  }
}

module "private_data_network" {
  source = "./modules/private-data-network"

  resource_group_name   = azurerm_resource_group.demo.name
  location              = azurerm_resource_group.demo.location
  name                  = local.workload_name
  vnet_address_space    = local.vnet_cidr
  oracle_subnet_prefix  = "10.200.100.0/28"
  gateway_subnet_prefix = "10.200.100.16/28"
  oracle_private_ip     = local.oracle_ip
  gateway_private_ip    = local.gateway_ip
  tags                  = local.tags

  oracle_additional_security_rules = [
    local.platform_rule,
    {
      name                       = "allow-bastion-ssh"
      priority                   = 110
      direction                  = "Inbound"
      protocol                   = "Tcp"
      destination_port_ranges    = ["22"]
      source_address_prefix      = local.bastion_source
      destination_address_prefix = "${local.oracle_ip}/32"
    },
    {
      name                       = "allow-internet-web-egress"
      priority                   = 200
      direction                  = "Outbound"
      protocol                   = "Tcp"
      destination_port_ranges    = ["80", "443"]
      source_address_prefix      = "${local.oracle_ip}/32"
      destination_address_prefix = "Internet"
    },
  ]

  gateway_additional_security_rules = [
    local.platform_rule,
    {
      name                       = "allow-bastion-rdp"
      priority                   = 110
      direction                  = "Inbound"
      protocol                   = "Tcp"
      destination_port_ranges    = ["3389"]
      source_address_prefix      = local.bastion_source
      destination_address_prefix = "${local.gateway_ip}/32"
    },
    {
      name                       = "allow-https-egress"
      priority                   = 200
      direction                  = "Outbound"
      protocol                   = "Tcp"
      destination_port_ranges    = ["443"]
      source_address_prefix      = "${local.gateway_ip}/32"
      destination_address_prefix = "Internet"
    },
  ]
}

resource "azurerm_public_ip" "nat" {
  name                = "${local.workload_name}-nat-pip"
  location            = azurerm_resource_group.demo.location
  resource_group_name = azurerm_resource_group.demo.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.tags
}

resource "azurerm_nat_gateway" "egress" {
  name                = "${local.workload_name}-nat"
  location            = azurerm_resource_group.demo.location
  resource_group_name = azurerm_resource_group.demo.name
  sku_name            = "Standard"
  tags                = local.tags
}

resource "azurerm_nat_gateway_public_ip_association" "egress" {
  nat_gateway_id       = azurerm_nat_gateway.egress.id
  public_ip_address_id = azurerm_public_ip.nat.id
}

resource "azurerm_subnet_nat_gateway_association" "workload" {
  for_each       = module.private_data_network.subnet_ids
  subnet_id      = each.value
  nat_gateway_id = azurerm_nat_gateway.egress.id
}

resource "azurerm_bastion_host" "admin" {
  name                = "${local.workload_name}-bastion"
  location            = azurerm_resource_group.demo.location
  resource_group_name = azurerm_resource_group.demo.name
  sku                 = "Developer"
  virtual_network_id  = module.private_data_network.virtual_network_id
  tags                = local.tags
}

resource "azurerm_network_interface" "oracle" {
  name                = "${local.workload_name}-oracle-nic"
  location            = azurerm_resource_group.demo.location
  resource_group_name = azurerm_resource_group.demo.name
  tags                = local.tags

  ip_configuration {
    name                          = "primary"
    subnet_id                     = module.private_data_network.subnet_ids["oracle"]
    private_ip_address_allocation = "Static"
    private_ip_address            = local.oracle_ip
  }
}

resource "azurerm_network_interface" "gateway" {
  name                = "${local.workload_name}-gateway-nic"
  location            = azurerm_resource_group.demo.location
  resource_group_name = azurerm_resource_group.demo.name
  tags                = local.tags

  ip_configuration {
    name                          = "primary"
    subnet_id                     = module.private_data_network.subnet_ids["gateway"]
    private_ip_address_allocation = "Static"
    private_ip_address            = local.gateway_ip
  }
}

resource "azurerm_linux_virtual_machine" "oracle" {
  name                            = "${local.workload_name}-oracle-vm"
  location                        = azurerm_resource_group.demo.location
  resource_group_name             = azurerm_resource_group.demo.name
  size                            = "Standard_B2s"
  admin_username                  = var.vm_admin_username
  disable_password_authentication = true
  network_interface_ids           = [azurerm_network_interface.oracle.id]
  tags                            = local.tags

  admin_ssh_key {
    username   = var.vm_admin_username
    public_key = var.oracle_admin_ssh_public_key
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
    disk_size_gb         = 128
  }

  source_image_reference {
    publisher = "Oracle"
    offer     = "Oracle-Linux"
    sku       = "ol98-lvm-gen2"
    version   = "9.8.3"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_windows_virtual_machine" "gateway" {
  name                  = "f1gwvm"
  computer_name         = "f1gwvm"
  location              = azurerm_resource_group.demo.location
  resource_group_name   = azurerm_resource_group.demo.name
  size                  = "Standard_D4s_v5"
  admin_username        = var.vm_admin_username
  admin_password        = var.gateway_admin_password
  network_interface_ids = [azurerm_network_interface.gateway.id]
  tags                  = local.tags

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
    disk_size_gb         = 128
  }

  source_image_reference {
    publisher = "MicrosoftWindowsServer"
    offer     = "WindowsServer"
    sku       = "2022-datacenter-g2"
    version   = "20348.5761.261013"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# Deallocates both VMs daily at 18:00 Stockholm time (DST-aware); startup stays manual.
resource "azurerm_dev_test_global_vm_shutdown_schedule" "workload" {
  for_each = {
    oracle  = azurerm_linux_virtual_machine.oracle.id
    gateway = azurerm_windows_virtual_machine.gateway.id
  }

  virtual_machine_id    = each.value
  location              = azurerm_resource_group.demo.location
  enabled               = true
  daily_recurrence_time = "1800"
  timezone              = "W. Europe Standard Time"

  notification_settings {
    enabled = false
  }
}
