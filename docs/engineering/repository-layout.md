# Repository layout and naming

This is the placement contract for [#22](https://github.com/frdeange/FabricF1Demo/issues/22).
See the [root entry point](../../README.md), [contribution guide](../../CONTRIBUTING.md)
and [machine-readable inventory](scaffold-inventory.json).
Areas marked reserved contain navigation documentation only; package status is
tracked per area in the inventory.

## Repository map

| Area | Purpose | Status and package owner |
| --- | --- | --- |
| [.github](../../.github/README.md) | Issue/PR templates and CI/CD navigation | #8 foundation implemented; future deployment package unassigned, readiness #3 |
| [apps](../../apps/README.md) | Independent [Hub](../../apps/hub/README.md) and [fan](../../apps/fan/README.md) Rayfin projects | Reserved (#9/#14/#10) |
| [packages](../../packages/README.md) | Shared [application contract bindings](../../packages/contracts/README.md) | Reserved; canonical business JSON remains authoritative (#5/#9) |
| [contracts](../../contracts/README.md) | Canonical business entities and invariants | Implemented (#5); do not duplicate into packages |
| [scenarios](../../scenarios/README.md) | Small deterministic scenario and journey fixture | Implemented (#5); volume generator belongs to #18 |
| [sources](../../sources/README.md) | Native source schemas/metadata, seed adapters and connector configuration | Partial: Oracle schema/seed #19; Mirroring qualification remains. Other owners: Salesforce #20, SAP #6/#15, sports #7 |
| [infra](../../infra/README.md) | Infrastructure/bootstrap ownership entry point | Reserved here; existing Terraform remains #3-owned, host/gateway #21 |
| [fabric](../../fabric/README.md) | Native item definitions below [workspace](../../fabric/workspace/README.md) | Reserved; ingestion #19/#20/#6, projections #4, intelligence #11, race path #7 |
| [deploy](../../deploy/README.md) | Environment bindings, orchestration and release records | Reserved; deployment follow-up unassigned, coordination #3/#9 and workload owners |
| [scripts](../../scripts/README.md) | Local validation/preflight and reconstruction entry points | Implemented validation; generator tracked separately in #18 |
| [tests](../../tests/README.md) | Credential-free checks and later integration tests | Implemented; each package owns its tests |
| [docs](../README.md) | Design, engineering rules and operations navigation | Implemented documentation, reserved runbooks |

Folder status in the inventory describes the area at this revision, not whether
every future capability is delivered. Package issues own implementation acceptance.
The [execution plan](../../EXECUTION-PLAN.md) remains the business roadmap.

## Naming

Use lower-kebab-case for new hand-authored directories and prose filenames.
Python modules and test filenames use snake_case (`test_repository_layout.py`).
Keep established root names (`README.md`, `AGENTS.md`, `CONTRIBUTING.md`,
`EXECUTION-PLAN.md`), GitHub filenames and existing authoritative JSON paths.
Use English identifiers and public-safe synthetic examples.

Native formats override these general rules. Preserve Rayfin CLI-generated
layout, Salesforce metadata names and native source schema identifiers.
Do not invent universal migration numbering: the owning issue selects the
supported endpoint tooling, naming and expand/contract recovery strategy.
Native seed adapters must be explicit/idempotent and distinct from schema
deployment; a logical fixture is not a source-native schema.

## Contracts, data and definitions

`contracts/canonical-contracts.json` is the authoritative business contract.
`packages/contracts` will hold derived application types/validation bindings,
not a second manually maintained canonical specification. Small canonical
fixtures stay in `scenarios`; do not turn that folder into a bulk export cache.

#18 owns the local generator at `scripts/volume_fixture.py` and the interface
`python -m scripts.volume_fixture generate|validate --output-path <path>`.
Its logical synthetic output families are `oracle`, `salesforce`, `sap_plan_b`
and `operational`, with `manifest.json` for counts/digests/reconciliation.
These generated records are not executable Oracle DDL, Salesforce metadata,
real SAP extracts or Rayfin-owned persistence. The Oracle source package maps
only its owned fixture families into its source-native schema and seed script.
The generator does not prescribe an output root.
Use an explicit external directory or optional ignored local `generated` or
`artifacts`; never commit bulk output. Tests use self-cleaning temp directories.

`sources` owns source-native schema/metadata, source-specific seed adapters and
connector configuration. `fabric/workspace` owns deployed Fabric definitions.
Rayfin-managed app/backend children stay with their app's supported tooling.
Source schemas, serving migrations and Git definition sync are different surfaces.

## Fabric native packaging

The reserved workspace root has documented [ingestion](../../fabric/workspace/ingestion/README.md),
[processing](../../fabric/workspace/processing/README.md),
[analytics](../../fabric/workspace/analytics/README.md),
[intelligence](../../fabric/workspace/intelligence/README.md) and
[realtime](../../fabric/workspace/realtime/README.md) domains. These are
organizational folders, not invented Fabric item types or separate workspaces.

Place qualified exported items under the appropriate domain, preserving their
native `{display name}.{public facing type}` directories (or native logical-ID
fallback names), case-sensitive types, `.platform` metadata and logical IDs.
Preserve dependency paths and semantic-model TMDL/PBIP internals. Examples such as
`fabric/workspace/analytics/Promoter.SemanticModel` illustrate future placement,
not an item delivered here. Do not fabricate metadata merely to fill the tree.

Git export support does not establish fabric-cicd support, reference rebinding,
service principal support or tenant availability. Verify each operation/type with
its owner and pinned version. Ontology and data agent formats remain conditional
on qualification. Do not impose formatting workarounds such as removing final
newlines without a representative native roundtrip.

Reference: [Microsoft Fabric Git source-code format](https://learn.microsoft.com/en-us/fabric/cicd/git-integration/source-code-format).
Installed Fabric Git integration guidance was consulted for this layout.

## Environments, ownership and release

Keep one source definition per item; do not create DEV/DEMO definition copies.
Use [environment contracts](../../deploy/environments/README.md) for secret-free
parameter placeholders and approved external binding resolution. A Variable
Library or `parameter.yml` must use its qualified native format when implemented;
neither automatically configures Rayfin runtime.

One writer per artifact/destination: Terraform #3 retains its existing resources
and single external local state. Do not import/re-own them, create a second state
or add nested IaC without owner coordination. Future source host/gateway resources
remain #21-owned and unapproved by this scaffold.
Fabric-cicd, native Git, Rayfin tooling and migrations must never compete for the
same item. See the [deployment ownership matrix](../deployment-ownership-support-matrix.md).
Pin executable tools/locks when selected; keep actions pinned to full SHAs.
No empty deployment workflows are allowed to stand in for actual capability.

[Release documentation](../../deploy/releases/README.md) defines future evidence,
not generated evidence of a release. Environment names are `dev` and `demo`;
the stable demo destination is not production.

## Guardrails

The validator checks inventory schema/unique safe paths/status, required
scaffold documents and relative Markdown links (including heading fragments)
in inventory-listed documents. It does not check remote availability, deploy
native artifacts, enforce naming on exports or require code-example future
paths to exist. Add a new scaffold README to the inventory and repository map
when extending this contract. Negative tests exercise missing/invalid entries
and navigation failures.
