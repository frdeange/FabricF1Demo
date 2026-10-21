variable "subscription_id" {
  description = "Approved Azure subscription ID, supplied privately by the operator."
  type        = string
  sensitive   = true
  nullable    = false

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "Supply the explicitly approved subscription UUID."
  }
}

variable "tenant_id" {
  description = "Approved Entra tenant ID for both providers, supplied privately."
  type        = string
  sensitive   = true
  nullable    = false

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.tenant_id))
    error_message = "Supply the explicitly approved tenant UUID."
  }
}

variable "capacity_administration_members" {
  description = "Approved existing capacity administrator UPNs, supplied privately. Applying this list requires explicit access approval."
  type        = set(string)
  sensitive   = true
  nullable    = false

  validation {
    condition     = length(var.capacity_administration_members) > 0 && alltrue([for member in var.capacity_administration_members : length(trimspace(member)) > 0])
    error_message = "Supply at least one explicitly approved existing capacity administrator."
  }
}

variable "location" {
  description = "Azure region for the demo resources."
  type        = string
  default     = "swedencentral"
  nullable    = false

  validation {
    condition     = var.location == "swedencentral"
    error_message = "This approved slice is restricted to Sweden Central (swedencentral)."
  }
}

variable "resource_group_name" {
  description = "Azure resource group name."
  type        = string
  default     = "rg-f1demo-swc"
}

variable "fabric_capacity_name" {
  description = "Fabric capacity name."
  type        = string
  default     = "f1democapswc"
}

variable "dev_workspace_name" {
  description = "Development workspace name."
  type        = string
  default     = "f1-dev"
}

variable "pro_workspace_name" {
  description = "Stable demo workspace name."
  type        = string
  default     = "f1-pro"
}

variable "vm_admin_username" {
  description = "Administrator username for the workload VMs."
  type        = string
  default     = "f1admin"
}

variable "oracle_admin_ssh_public_key" {
  description = "SSH public key for the Oracle VM, supplied privately."
  type        = string
  sensitive   = true
  nullable    = false
}

variable "gateway_admin_password" {
  description = "Local administrator password for the gateway VM, supplied privately."
  type        = string
  sensitive   = true
  nullable    = false

  validation {
    condition     = length(var.gateway_admin_password) >= 16
    error_message = "Use a password of at least 16 characters."
  }
}
