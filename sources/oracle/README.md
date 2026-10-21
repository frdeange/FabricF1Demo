# Oracle source

[Sources](../README.md) | [Repository map](../../docs/engineering/repository-layout.md)

Issue #19 owns source-native Oracle schemas, idempotent seed adapters and native
Mirroring qualification. #21 owns host/gateway infrastructure; #18 owns logical
synthetic generation. Native Mirroring must not be silently replaced by Copy Job.

`schema/001_catalog.sql` creates the five synthetic catalog tables without
dropping or resetting existing objects. It uses Oracle `VARCHAR2`, `NUMBER`, and
`TIMESTAMP WITH LOCAL TIME ZONE` columns, primary/foreign keys, and source-reference
uniqueness. Schema creation is a one-time operation and must follow exact Oracle
edition and Mirroring compatibility qualification.

Generate the deterministic SQL*Plus-compatible seed script from a validated #18
fixture export:

```text
python -m scripts.volume_fixture generate --output-path <external-fixture-directory> --customer-count 30 --order-count 600
python -m sources.oracle.seed export --fixture-path <external-fixture-directory> --output-path <external-seed-directory>/seed.sql
```

The adapter validates the complete fixture, emits only Oracle-owned event,
zone, product, price, and bundle-component records, and uses `MERGE` keyed by
canonical source keys. The generated SQL path must be outside the fixture
directory and cannot overwrite an existing file. The adapter never connects to
Oracle or executes SQL; run the generated script only as an explicit seed
action against a qualified, synthetic-only database, using a separately
approved Oracle identity. Fixture generation and seed execution are distinct
from schema deployment. No Oracle credentials or live connection setup are
stored here.

The default `multi-event-v2` fixture exports **1,692 Oracle rows** into the same
five tables: 12 events, 96 zones, 288 products, 1,152 price versions and 144
bundle components. Use `--catalog-profile single-event-v1` for the original
13-row commissioning baseline. Both profiles are validated before SQL export;
the rich profile has isolated keys and does not replace or delete old rows.
The [shared generator contract](../../docs/canonical-business-data-contracts.md)
defines global customer/order totals, event attribution and effective prices.
Generating richer SQL is not proof of a live load or native Mirroring acceptance;
coordinate any source write and preservation/recovery of commissioning data
with the #19 operator.

Use an `AL32UTF8` database and a UTF-8 SQL*Plus client (`NLS_LANG` character
set `AL32UTF8`). The exporter rejects values exceeding declared character
widths, the standard 4000-byte text limit, or declared integer precisions.
It splits text expressions and SELECT projections into short physical lines
and encodes control characters as `CHR` expressions for SQL*Plus.
The seed session is explicitly UTC before assigning normalized timestamp
literals to local-time-zone columns. Set query sessions to UTC as well when
reconciling source timestamps; other session time zones display the same
instants differently. This type is on Microsoft's
[Oracle Mirroring supported-type list](https://learn.microsoft.com/fabric/mirroring/oracle-limitations).
Static checks do not replace execution and Mirroring verification on the
qualified Oracle target.

The review-only [cloud integration proposal](../../docs/oracle-cloud-integration-proposal.md)
describes the current #3/#21 ownership boundary, the PR #25 network-module
contract, resource candidates, connectivity alternatives, and remaining
deployment gates. It is not an applied configuration or deployment approval.
