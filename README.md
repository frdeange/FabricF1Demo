# FabricF1Demo

A Microsoft Fabric and managed-Rayfin demo for a Grand Prix promoter and fan
experience.

## Project status

The approved design is tracked in the [English execution plan](EXECUTION-PLAN.md)
and the [GitHub roadmap issue](https://github.com/frdeange/FabricF1Demo/issues/1).
This repository currently contains the plan and a validation-only CI foundation.
The existing [issue #3](https://github.com/frdeange/FabricF1Demo/issues/3)
owner handoff records a separately approved Terraform deployment of
`rg-f1demo-swc`, F2 capacity `f1democapswc` in Sweden Central, and workspaces
`f1-dev` and `f1-pro` on that capacity. The capacity was Active at verification;
this is historical evidence, not a fresh live-state check. `f1-pro` is a stable
demo workspace, not production. The handoff and Terraform changes remain
uncommitted on the separate #3 branch; the CI foundation remains on the
unmerged #8 branch, not `main`.

Infrastructure deployment does not qualify workloads or unattended deployment.
Fabric Apps/Rayfin, workload identities and permissions, applicable licensing,
and F2 workload fitness remain unqualified. Terraform uses one external local
state; unattended infrastructure deployment remains blocked on protected state,
coordination, recovery and a qualified clean-runner identity. No additional
infrastructure, budgets, autopause or autoscale are configured; F4 requires
separate approval. This update authorizes no cloud operation. See the
[deployment ownership and support matrix](docs/deployment-ownership-support-matrix.md).

## Contributing

Read [AGENTS.md](AGENTS.md) and the package issue before making changes. Project
content and partner-facing deliverables are authored in English. Keep internal
reference material, credentials, tenant details, and unapproved licensed data
out of this public repository.
