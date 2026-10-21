resource "azurerm_resource_group" "demo" {
  name     = var.resource_group_name
  location = var.location

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_fabric_capacity" "demo" {
  name                   = var.fabric_capacity_name
  resource_group_name    = azurerm_resource_group.demo.name
  location               = azurerm_resource_group.demo.location
  administration_members = var.capacity_administration_members

  sku {
    name = "F2"
    tier = "Fabric"
  }

  lifecycle {
    prevent_destroy = true
  }
}

data "fabric_capacities" "all" {
  depends_on = [azurerm_fabric_capacity.demo]
}

locals {
  # ARM resource IDs and Fabric capacity GUIDs are different identifiers.
  demo_capacity_matches = [
    for capacity in data.fabric_capacities.all.values : capacity
    if capacity.display_name == azurerm_fabric_capacity.demo.name &&
    capacity.region == "Sweden Central" &&
    capacity.sku == "F2"
  ]
}

resource "fabric_workspace" "dev" {
  display_name = var.dev_workspace_name
  capacity_id  = try(local.demo_capacity_matches[0].id, "")

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = length(local.demo_capacity_matches) == 1
      error_message = "Expected exactly one F2 capacity with this name in Sweden Central; resolve duplicate or missing matches before assigning workspaces."
    }
  }
}

resource "fabric_workspace" "pro" {
  display_name = var.pro_workspace_name
  capacity_id  = try(local.demo_capacity_matches[0].id, "")

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = length(local.demo_capacity_matches) == 1
      error_message = "Expected exactly one F2 capacity with this name in Sweden Central; resolve duplicate or missing matches before assigning workspaces."
    }
  }
}
