# Workspace definition root

[Fabric](../README.md) | [Repository map](../../docs/engineering/repository-layout.md)

Reserved organizational root: [ingestion](ingestion/README.md),
[processing](processing/README.md), [analytics](analytics/README.md),
[intelligence](intelligence/README.md), [realtime](realtime/README.md).
These domains are not separate workspaces or invented item types.
Keep a single item source across DEV/DEMO and bind qualified parameters externally.
Actual publish scope and dependency order must be chosen explicitly by owners;
do not recursively publish all folders or delete orphans by default.
Preserve native export names, metadata, logical IDs and dependency references
as described in the repository map. No export or workspace sync is implemented.
