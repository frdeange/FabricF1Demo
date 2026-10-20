# Oracle source

[Sources](../README.md) | [Repository map](../../docs/engineering/repository-layout.md)

Reserved: #19 owns source-native schemas, idempotent seed adapters and Oracle
Mirroring qualification. #21 owns host/gateway infrastructure; #18 owns logical
synthetic generation. Native Mirroring must not be silently replaced by Copy Job.
Future DDL/migrations follow the qualified Oracle version/tool; external keys and
reconciliation follow canonical contracts. Seed execution is explicit and
separate from schema deployment. No SQL scripts or connection setup exist here.
