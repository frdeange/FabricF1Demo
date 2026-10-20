# Agent playbook

Read the [repository map](repository-layout.md), [contribution guide](../../CONTRIBUTING.md)
and [AGENTS.md](../../AGENTS.md) before executing an issue.

A handoff identifies one package issue, outcome, owned paths, shared paths,
exclusions, acceptance checks, model/effort and escalation conditions.
Coordinate shared files with their active owners before editing. Do not move
another package's implementation to a reserved directory or duplicate its logic.

Use the lightest capable available model after scope is defined. Report actual
implementation model/effort separately from recommendations. Escalate concrete
design/debugging blockers, not routine file creation. A failed delegation must
not be represented as successful implementation.

Run package checks and repository checks, then arrange separate actual-diff review
for correctness, regressions, scope and repository rules. Resolve and reverify
findings. Present inspectable changes, exact validation results and limitations;
stop for explicit user approval before PR creation. No cloud, permissions, commit,
push, PR or merge authorization is implied by an implementation assignment.

The [deployment matrix](../deployment-ownership-support-matrix.md) assigns one
writer per artifact/destination. Resource bootstrap, source metadata/seeding,
Fabric definitions and Rayfin app deployment are separate responsibilities.
Preserve active data paths and Terraform state; do not inspect private references.
