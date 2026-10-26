# SAP source paths

[Sources](../README.md) | [Repository map](../../docs/engineering/repository-layout.md)

Issue #6 owns explicitly synthetic SAP Plan B and its qualified native Fabric
processing route. #18 supplies logical synthetic fixtures, not SAP-native
schemas or proof of a connected ERP. Keep Plan B labels in manifests and evidence.

## Datasphere-like synthetic source package (#6)

The target is **synthetic Datasphere-like files -> ADLS Gen2 -> OneLake shortcut
-> SAP Mirroring -> separately qualified BPS processing -> canonical publication**.
Only the local file-generation and replay boundary is implemented here. The
former generic JSONL exporter has been removed: it was not this source path.

`python -m sources.sap.datasphere` converts the existing validated #18 fixture
into real Snappy-compressed Parquet with the directory and metadata conventions
observed in the pinned public writer below. It does not contact any service.
All eight SAP families are represented by explicitly custom `ZF1_*` source
objects, not by invented SAP standard CDS tables or a fictitious connected ERP.
The package also includes a `DD03ND`-shaped initial table derived from those
local transport schemas. It is a synthetic schema index, not SAP DDIC metadata,
and does **not** make the package BPS-ready.
Oracle, Salesforce, operational orders and the shared generator/contracts are
not modified or duplicated as new source-owned sales.

### Reproduce locally

Use Python 3.12 (the CI baseline) and the pinned package dependency. The optional
`generated` directory is ignored by Git. Use new destinations for a new run.

```powershell
python -m pip install -r sources\sap\requirements.txt
python -m scripts.volume_fixture generate --output-path generated\sap-plan-b\fixture --customer-count 30 --order-count 60 --catalog-profile multi-event-v2 --identity-profile natural-v1
python -m sources.sap.datasphere generate --fixture-path generated\sap-plan-b\fixture --output-path generated\sap-plan-b\package
python -m sources.sap.datasphere validate --fixture-path generated\sap-plan-b\fixture --output-path generated\sap-plan-b\package
python -m sources.sap.datasphere generate --fixture-path generated\sap-plan-b\fixture --output-path generated\sap-plan-b\package --if-exists verify-noop
python -m unittest discover -s tests -p "test_sap_datasphere.py" -v
```

This small run is a regression/demo source sample, not the established volume
fixture or proof of any remotely loaded manifest. A larger authorized demo can
consume an existing validated fixture without introducing a new #18 profile.
Source dataset digest, namespace, keys, schema and publication identity remain
those of the input fixture. Output bytes are reproducible with the pinned
PyArrow version, which is recorded in the output manifest. Existing destinations
are refused; `verify-noop` validates but never repairs or overwrites them.
Generation validates a temporary staging package before exclusively reserving
the destination; publication I/O failures report and retain incomplete output.

### Layout and source contract

```text
package/
  manifest.json
  fixture-manifest.json
  contract.json
  batches.json
  THIRD-PARTY-NOTICES.txt
  datasphere/F1_PLAN_B/ZF1_<FAMILY>/
    .sap.partfile.metadata
    initial/
      .sap.partfile.metadata
      part-<digest>.parquet
      _SUCCESS
    delta/
      .sap.partfile.metadata
      part-<timestamp>-<digest>-01.parquet  (only where changes exist)
  datasphere/F1_PLAN_B/DD03ND/
    .sap.partfile.metadata
    initial/
      .sap.partfile.metadata
      part-<digest>.parquet
      _SUCCESS
    delta/
      .sap.partfile.metadata
```

Each object has metadata version 3, `format=PARQUET`, `loadType=REPLICATE`,
`groupDeltaFilesBy=NONE`, and a deterministic synthetic replication task ID.
The composite source identity remains
`(sourceSystem, sourceTenant, sourceEntity, sourceKey)`. `contract.json` records
each custom column and its lossless local encoding: strings as NVARCHAR,
integers (including USD minor units) as DECIMAL(20,0), and nested crosswalks,
lists and booleans as explicitly encoded JSON strings. No business amount is
converted to float, relabeled as a major-currency amount or summed with orders.
Optional nulls are decoded using the local contract.

The synthetic `DD03ND`-shaped projection contains `STRUCOBJN`, `FIELDNAME`,
`DATATYPE`, `LENG` and `DECIMALS`, following Microsoft's documented field names.
It lists each custom object's three transport columns and payload fields. Its
types describe this package's transport representation (`NVARCHAR`, `DECIMAL`,
`TIMESTAMP`), not SAP ABAP Dictionary types or an activated SAP source contract.
The `TIMESTAMP` length/scale values describe the local Parquet physical width
and microsecond resolution only. It must not be presented as a replicated
`ZDD03ND_CDS` view or treated as proof that BPS can transform these objects.

| Technical column | Implemented semantics and evidence limit |
| --- | --- |
| `__operation_type` | `L` initial load, `U` full-row upsert. All `X`/delete operations are rejected, especially financial-document deletions. |
| `__sequence_number` | Nullable DECIMAL(20,0), deliberately null as in the pinned public writer. It is not an invented source CDC sequence or ordering guarantee. |
| `__timestamp` | UTC microsecond extraction timestamp: fixture `asOf` for initial and `publishedAt` for the credit delta. Original source/update/ingestion clocks remain separate columns. |

The deterministic local scenario has two checkpoints: initial contains all
masters and all documents/lines/links except customer credit memos; delta then
upserts those credit documents and their lines/typed links. These are **staged
synthetic checkpoints**, not a reconstruction of historical SAP CDC. Final
replay exactly reproduces the source fixture, including credit/order crosslinks,
supplier costs, allocations and financial reconciliation. No new canonical
publication is claimed for the intermediate checkpoint.

The validator anchors the complete file set, metadata and hashes to the
validated original fixture, checks actual Parquet schema/compression, replays
the batches and compares every restored source row/key to that fixture. It
then verifies document/line/BP/supplier relations and exact financial totals.
Rehashing a corrupted file or manifest cannot turn it into accepted source
data. Keep the original fixture alongside the package for validation.

### Qualification gap and next execution steps

Both `native_bps_ready=false` and `native_mirroring_ready=false` remain explicit.
The public writer is evidence for a **Datasphere-like transport**, not a
published SAP service-side acceptance contract. The eight custom F1 projections
are not the native Finance/AR/AP/Billing dataset input schemas. The colleague's
activated dataset contract and its observations cannot qualify this tenant,
our custom fields, hierarchies, transformations or credit-sign conventions.
Metadata acceptance, null sequence semantics and native consumption of these
custom objects must be observed in a real authorized pilot.

1. Generate and validate the local package above; inspect the pinned input
   digest and `batches.json`. Retain initial and delta as separate checkpoints.
2. After separate cloud approval, create or reuse the designated HNS-enabled
   ADLS Gen2 account/container and isolated prefix. Upload only initial data,
   required metadata and `_SUCCESS` first; do not upload the whole delta history
   at once and call it live ingestion.
3. Create an approved Lakehouse ADLS shortcut to the container, then a separate
   Mirrored SAP item selecting the replicated `datasphere` root. Verify metadata
   acceptance, replication state, row counts and financial reconciliation.
   Publish the credit delta only after recording the initial checkpoint.
4. Independently inspect the available BPS workload and activated datasets.
   Map/register the custom objects and qualify all required columns, joins,
   hierarchies and transformations. Stop visibly if unsupported; a standard
   Fabric processing alternative requires an explicit decision and is not a
   silent BPS fallback.
5. After native acceptance, implement a versioned canonical publication with
   explicit source/package lineage, source/ingestion/publication clocks and
   reconciliation. This local package alone does not deliver that cloud path
   or close #6's native-processing acceptance criterion. Plan A #15 and the
   operational ingestion prerequisite #9 remain separate.

Cloud provisioning and transfer are deliberately separate from this local
generator. Before each pilot, obtain scoped approval for the target
subscription/resource group, storage and Fabric items, identities and roles,
network/trusted-workspace access, exact writes, region, cost and rollback or
retention ownership. Recheck the live policy and resource state; never infer
cloud authorization from a local package or repository documentation. Do not
put credentials or tenant-specific bindings in this repository. The existing
**F2** is the compatibility-pilot ceiling; its lifecycle is organization-managed
and this code does not resize or resume capacity. Microsoft's BPS deployment and
FAQ capacity statements have differed (F2+ vs F16 minimum), so item/workload
eligibility must be verified rather than treating size as a throughput-only
difference. A successful local replay proves neither F2 BPS eligibility nor
native mirroring compatibility.

### Public evidence and licensing

Metadata/layout adapted from the MIT-licensed
[public writer at the pinned revision](https://github.com/fredgis/FabricHubDemo/blob/5ad08f4c3d6352408de84a96796b4bfdf393b23f/sources/sap/datasphere.py).
The required notice is included in
[`THIRD-PARTY-NOTICES.txt`](THIRD-PARTY-NOTICES.txt) and generated packages.
No third-party records, business terms or private presentations are used.
Microsoft's [Datasphere tutorial](https://learn.microsoft.com/fabric/mirroring/sap-datasphere-tutorial)
documents Parquet, Group Delta None, Initial/Delta, the container shortcut and
Mirrored SAP selection; it does not certify a synthetic generator.
See also [SAP Mirroring](https://learn.microsoft.com/fabric/mirroring/sap),
[BPS overview](https://learn.microsoft.com/azure/sap/business-process-solutions/about-business-process-solutions),
[BPS FAQ](https://learn.microsoft.com/azure/sap/business-process-solutions/faq)
and the [canonical contracts](../../docs/canonical-business-data-contracts.md).

Real SAP Plan A remains conditional under #15: access, usage rights, supported
interfaces and reconstruction must be qualified first. The Plan B generator here
is the local Datasphere-like source described above; any native Plan B
integration must use a separately qualified supported format and path. Never
seed real SAP by directly writing business tables or treat trial reconstruction
as a license renewal.
