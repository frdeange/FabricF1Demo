# Sources

[Repository map](../docs/engineering/repository-layout.md)

Reserved source-native packages: [Oracle](oracle/README.md),
[Salesforce](salesforce/README.md), [SAP](sap/README.md) and
[sports](sports/README.md). These packages do not yet contain native metadata,
source loaders or qualified connector implementations.

Keep native schemas/metadata, endpoint-specific migrations, explicit/idempotent
seed adapters and connector configuration distinct within each source package
when its owner selects supported tooling. Those child names are placement
examples, not executable capabilities or approved formats.
Logical synthetic generation remains #18-owned in `scripts/volume_fixture.py`,
not copied into each source. Source schema deployment must not reset seeded data.
Fabric ingestion item definitions belong in [Fabric](../fabric/README.md);
source credentials and real bindings never belong in Git.
