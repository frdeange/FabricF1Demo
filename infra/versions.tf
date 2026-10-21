terraform {
  required_version = ">= 1.16.0, < 2.0.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 5.10.0"
    }

    fabric = {
      source  = "microsoft/fabric"
      version = "= 1.14.0"
    }
  }

  backend "local" {}
}

provider "azurerm" {
  features {}

  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
  use_cli         = true

  resource_provider_registrations = "none"
}

provider "fabric" {
  tenant_id = var.tenant_id
  use_cli   = true
}
