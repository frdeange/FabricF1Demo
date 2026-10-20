# Salesforce source

[Sources](../README.md) | [Repository map](../../docs/engineering/repository-layout.md)

Reserved: #20 owns native object/field metadata, idempotent seed adapter,
source rights/quotas and ingestion qualification. Preserve native metadata
filenames/layout from the selected supported tooling. Do not invent Oracle-style
SQL migrations for Salesforce. #18 logical fixtures do not establish real object
creation or data loading. Connector configuration stays public-safe; auth and org
bindings are resolved externally. No Salesforce project is supplied here yet.
