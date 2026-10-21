mock_provider "azurerm" {}
mock_provider "fabric" {}

variables {
  subscription_id                 = "00000000-0000-0000-0000-000000000000"
  tenant_id                       = "22222222-2222-2222-2222-222222222222"
  capacity_administration_members = ["fabric-admin@example.invalid"]
  oracle_admin_ssh_public_key     = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGvo+mu7dhReK6jqjGwdLY8JcNAn/Uqh91KqkL2fY1NI test-only"
  gateway_admin_password          = "Example-Only-Passw0rd!"
}

run "reject_short_gateway_password" {
  command = plan

  variables {
    gateway_admin_password = "short"
  }

  expect_failures = [var.gateway_admin_password]
}

run "reject_other_region" {
  command = plan

  variables {
    location = "northeurope"
  }

  expect_failures = [var.location]
}

run "reject_empty_administrators" {
  command = plan

  variables {
    capacity_administration_members = []
  }

  expect_failures = [var.capacity_administration_members]
}

run "reject_invalid_subscription" {
  command = plan

  variables {
    subscription_id = "not-a-subscription-id"
  }

  expect_failures = [var.subscription_id]
}

run "reject_invalid_tenant" {
  command = plan

  variables {
    tenant_id = "not-a-tenant-id"
  }

  expect_failures = [var.tenant_id]
}
