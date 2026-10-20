variable "resource_group_name" {
  description = "Name of the existing resource group owned by the caller."
  type        = string
  nullable    = false

  validation {
    condition     = length(trimspace(var.resource_group_name)) > 0
    error_message = "Supply the name of the existing resource group."
  }
}

variable "location" {
  description = "Azure region inherited from the owning root."
  type        = string
  nullable    = false

  validation {
    condition     = length(trimspace(var.location)) > 0
    error_message = "Supply the approved Azure region."
  }
}

variable "name" {
  description = "Short resource-name prefix; generated names append role-specific suffixes."
  type        = string
  nullable    = false

  validation {
    condition     = length(var.name) >= 1 && length(var.name) <= 40 && can(regex("^[A-Za-z0-9][A-Za-z0-9-]*$", var.name))
    error_message = "Use a 1-40 character name prefix containing only letters, numbers, and hyphens, starting with a letter or number."
  }
}

variable "vnet_address_space" {
  description = "Explicit private IPv4 /27 for the two-subnet pilot shape; select only after IPAM review."
  type        = string
  nullable    = false

  validation {
    condition = try(
      cidrnetmask(var.vnet_address_space) != "" &&
      tonumber(split("/", var.vnet_address_space)[1]) == 27 &&
      cidrhost(var.vnet_address_space, 0) == split("/", var.vnet_address_space)[0] &&
      (
        tonumber(split(".", cidrhost(var.vnet_address_space, 0))[0]) == 10 ||
        (
          tonumber(split(".", cidrhost(var.vnet_address_space, 0))[0]) == 172 &&
          tonumber(split(".", cidrhost(var.vnet_address_space, 0))[1]) >= 16 &&
          tonumber(split(".", cidrhost(var.vnet_address_space, 0))[1]) <= 31
        ) ||
        (
          tonumber(split(".", cidrhost(var.vnet_address_space, 0))[0]) == 192 &&
          tonumber(split(".", cidrhost(var.vnet_address_space, 0))[1]) == 168
        )
      ),
      false
    )
    error_message = "Supply one canonical RFC1918 IPv4 /27 address range approved by IPAM."
  }
}

variable "oracle_subnet_prefix" {
  description = "Explicit Oracle IPv4 /28 contained in the VNet address space."
  type        = string
  nullable    = false

  validation {
    condition = try(
      var.oracle_subnet_prefix == cidrsubnet(var.vnet_address_space, 1, 0) ||
      var.oracle_subnet_prefix == cidrsubnet(var.vnet_address_space, 1, 1),
      false
    )
    error_message = "Supply one of the two /28 subnet ranges fully contained in the approved VNet address space."
  }
}

variable "gateway_subnet_prefix" {
  description = "Explicit, non-overlapping gateway IPv4 /28 contained in the VNet address space."
  type        = string
  nullable    = false

  validation {
    condition = try(
      (
        var.gateway_subnet_prefix == cidrsubnet(var.vnet_address_space, 1, 0) ||
        var.gateway_subnet_prefix == cidrsubnet(var.vnet_address_space, 1, 1)
      ) &&
      var.gateway_subnet_prefix != var.oracle_subnet_prefix,
      false
    )
    error_message = "Supply the other /28 subnet range inside the VNet; it must not overlap the Oracle subnet."
  }
}

variable "oracle_private_ip" {
  description = "Explicit, IPAM-approved Oracle host IPv4 address; Azure-reserved subnet addresses are rejected."
  type        = string
  nullable    = false

  validation {
    condition = try(
      contains(
        [for host_index in range(4, 15) : cidrhost(var.oracle_subnet_prefix, host_index)],
        var.oracle_private_ip
      ),
      false
    )
    error_message = "Supply an available IPv4 address inside the Oracle subnet, excluding Azure-reserved addresses."
  }
}

variable "gateway_private_ip" {
  description = "Explicit, IPAM-approved gateway host IPv4 address used as the only Oracle listener source."
  type        = string
  nullable    = false

  validation {
    condition = try(
      contains(
        [for host_index in range(4, 15) : cidrhost(var.gateway_subnet_prefix, host_index)],
        var.gateway_private_ip
      ),
      false
    )
    error_message = "Supply an available IPv4 address inside the gateway subnet, excluding Azure-reserved addresses."
  }
}

variable "tags" {
  description = "Non-sensitive resource tags supplied by the owning root."
  type        = map(string)
  default     = {}
  nullable    = false
}
