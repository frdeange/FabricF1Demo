# Infrastructure and bootstrap

[Repository map](../docs/engineering/repository-layout.md)

Reserved navigation entry point, not new IaC. #3 retains the existing Terraform
resource ownership and single external local state on its separate delivery.
Do not copy, move, inspect state, import resources, create a second state or
blindly apply an empty state to those resources. Agree the nested IaC path with
the owner before adding configuration here.

#21 owns future Oracle host/gateway qualification. Other networking/workers/
storage expansion needs separate resource/tool/identity/budget/region/rollback
approval. Bootstrap is distinct from routine deployment; no provisioning or cloud
operation is authorized or implemented by this directory.
See the [ownership matrix](../docs/deployment-ownership-support-matrix.md).
