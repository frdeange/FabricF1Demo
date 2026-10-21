# Canonical business and data contracts

This package defines the shared business boundary for the promoter Hub and Fan Experience. The machine-readable entity registry is `contracts/canonical-contracts.json`; this document defines behavior that must remain true across source adapters, operational commands, publications, and app projections.

All examples and the companion manifest are synthetic. Plan A means a future, separately authorized real SAP adapter. Plan B is an illustrative synthetic SAP-shaped scenario ledger intended for a future native-Fabric processing pilot; that processing path has not been qualified or run. No SAP, Oracle, Salesforce, sports-data provider, live race, customer, or commercial relationship is connected or represented by these fixtures.

## Identity, ownership, and grain

Canonical keys are immutable, namespaced strings: `EventKey`, `SessionKey`, `DriverKey`, `ZoneKey`, `ProductKey`, `PriceKey`, `PartyKey`, `SponsorAccountKey`, `CampaignKey`, `OrderKey`, `OrderLineKey`, `ReservationKey`, `PaymentSimulationKey`, `EntitlementKey`, `CaseKey`, `ScenarioCreditKey`, `SponsorshipAgreementKey`, `SponsorshipCommitmentKey`, `ERPDocumentKey`, `ERPDocumentLineKey`, `DocumentLinkKey`, `SupplierCostKey`, `CostAllocationKey`, `RaceEventKey`, `ReplayRunKey`, and `PublicationKey`. The six cross-domain anchors are `EventKey`, `SessionKey`, `PartyKey`, `ProductKey`, `OrderKey`, and `CaseKey`. A merge or source-key change creates a cross-reference; it does not rewrite a canonical key.

Every entity's owner, grain, lifecycle states, unit, time fields, PII class, allowed operations, and Plan A/Plan B mapping are listed in the JSON registry. Business ownership is not the same as physical storage: source adapters own source master facts; the authorized Rayfin command boundary owns orders, reservations, simulated payment outcomes, entitlements, and support-command receipts; SAP or the isolated Plan B ledger owns ERP documents; and the publication pipeline owns immutable analytical versions. Apps call authorized commands and read authorized projections. They do not write operational state into Gold or write directly to SAP.

Preserve `(sourceSystem, sourceTenant, sourceEntity, sourceKey)` as a unique source cross-reference. Do not join identities using email, display name, browser-supplied buyer identity, or a source-local integer ID. Entra identity is mapped to `PartyKey` by a server-side, administrator-managed assignment. The actor's role and record ownership are checked on every command; a client-selected profile is never authority.

## State, operations, and lifecycle

The registry's per-entity state lists are closed values, not free-form labels. State changes are commands with actor, prior state, effective time, and audit receipt. Invalid transitions fail visibly and create no successful-looking receipt. Historical source events are append-only; corrections use a source revision, retraction, or reversal linked to the original record.

The operational order path creates one order and its lines, a persisted simulated outcome, entitlements, an idempotent receipt, and an outbox/reconciliation item in one local transaction or a recoverable state machine. An approved simulation can confirm the order and grant access; declined/voided outcomes cannot. ERP document creation is asynchronous and separate: pending/error remains visible, and a document is reported as created only after the source/Plan B ledger confirms it. A Gold refresh never grants or removes access.

Oracle (or its synthetic fixture) is the owner of base catalog capacity. The operational reservation is the allocation ledger. Competing reservations use atomic conditional allocation against available capacity; do not maintain a second mutable inventory without an explicit synchronization contract. Commercial orders and related ERP orders/documents are distinct linked records and must never be added as two sales.

### Idempotency and recovery

- Each mutating command requires a client idempotency key scoped by actor, command type, and environment. Persist its request hash and outcome receipt. A retry with the same key and same payload returns the original receipt and keys; reuse with a different payload returns a conflict.
- Enforce uniqueness for canonical keys and for each source cross-reference. Use atomic state transitions, inventory compare-and-set/locking, and a transactional outbox or equivalent durable recovery record.
- A deterministic seed plus `scenarioId`, `scenarioVersion`, and `datasetId` reproduces the same canonical fixture keys and values. A rerun in the same namespace is an upsert/no-op, not a new sale. A deliberately separate run has a separate dataset/publication namespace.
- Race-event analytical facts are unique by publication, session, and source sequence/event key. Delivery/replay attempts carry their own `ReplayRunKey`; retry or restart does not create a new order, payment, entitlement, or analytical source fact.
- Keep one isolated SAP plan, dataset, and publication per run. Never join or sum Plan A and Plan B records as though they were one source version.

## Currency, payment, credit, and financial measures

Amounts are non-negative integer minor units plus ISO 4217 currency (for example, `5000 USD` means USD 50.00). Never use floating-point values. Each price/order/document line records quantity, unit amount, net, tax, gross, and explicit `taxTreatment` (`exclusive`, `inclusive`, or `not_applicable`). Aggregate only within one currency. Do not infer tax, exchange rates, settlement, or accounting recognition. `null` plus an availability reason means unknown; it is not zero.

`PaymentSimulation` records a persisted simulated attempt only. It is not a payment gateway call, bank charge/refund, settlement, invoice, or revenue. `ScenarioCredit` is an approved compensation record, not money returned. This package adopts the bounded contract assumption that a full credit revokes the order's unconsumed entitlements; a partial credit does not revoke them. Consumed access is not undone. Any future change to this policy must version the contract and its test cases.

Keep these measures separate in every projection and reconciliation:

| Measure | Definition |
| --- | --- |
| Commercial order gross | Confirmed commercial order totals before scenario credits. |
| Simulated payment outcomes | Approved simulated attempts, grouped by result and currency; not bank settlement. |
| Posted customer invoices | Posted ERP/Plan B customer invoices only, with source and publication. |
| Scenario credits / credit documents | Approved operational credit and its separately linked ERP credit document; neither is a bank refund. |
| Sponsorship contracted / invoiced / fulfilled | Agreement amount, posted sponsor invoices, and evidenced deliverable value; never interchangeable. |
| Supplier cost / allocated cost | Source cost facts and their posted allocations, reported separately from sales. |
| Scenario order net | Commercial order gross less approved linked scenario credit; a demo metric, not certified accounting revenue. |

## Provenance and source plans

Every published record carries source system/key, source update time, ingestion time, schema version, dataset and plan, and `PublicationKey`; every financial/business projection can be traced to the source document or operational receipt. Identify simulated records and UI metrics with a visible synthetic/scenario provenance label. Keep freshness and unavailable-value status explicit.

**Plan A** retains the same canonical contract but maps to an actually authorized SAP ERP through a supported interface; source document numbers and shapes remain source-specific. No Plan A source is enabled by this package. **Plan B** is intended to use a deterministic synthetic source and a native Fabric processing path only after a separate support pilot; its documents are visibly scenario documents and are not evidence of a connected SAP system. Oracle/Salesforce source mappings remain separate from the SAP choice. Adapters normalize both plans; do not force fictional tables to mimic a specific SAP release.

`SourcePublication` is immutable once published. A corrected/updated result creates a new publication with its own key and `asOf`; consumers select exactly one publication/run. Publication metadata distinguishes source time from ingestion/publication time. Do not silently combine an older SAP publication with a newer operational or sports publication.

## Source-seed fixture for Oracle, Salesforce, and SAP Plan B

`scenarios/canonical-scenario-manifest.json` now includes a `sourceSeed` section that defines deterministic, synthetic source records for Oracle, Salesforce, and SAP Plan B across the same four journeys.

- This section is a data fixture and logical mapping, not a source adapter, provisioning package, or seeding workflow; no source has been connected or loaded.
- Every source record carries `sourceSystem`, `sourceTenant`, `sourceEntity`, `sourceKey`, `scenarioId`, `scenarioVersion`, `datasetId`, `schemaVersion`, and synthetic provenance.
- Oracle records are logical source contracts only, with illustrative schema labels (not executable DDL), and explicit links across event, zone, product, bundle component, and price records.
- Salesforce records use standard objects where applicable (`Account`, `Contact`, `Opportunity`, `Case`, `Campaign`) and clearly mark custom API names as illustrative/unqualified (for example `Sponsorship_Commitment__c`).
- SAP Plan B records are an illustrative synthetic SAP-shaped fixture intended for a future Fabric-native-path pilot; no processing or capability qualification has been performed, and the records do not claim SAP provisioning or connectivity. Business-partner, supplier, and cost-center rows are source-only references where P1 has no separate canonical master entity; they must not be mapped onto transactional `SupplierCost` or `CostAllocation` keys.
- Source-only SAP master references have no `canonicalEntity` or `canonicalKey`; their explicit mapping status prevents conflating them with canonical financial facts.
- Seeding identity is deterministic and idempotent for the same run version; run-version namespaces are explicit and isolated.
- Invalid or incomplete inputs are documented as negative scenarios and are intentionally excluded from successful seeded records.

### Small regression fixture vs. high-volume synthetic export

The canonical scenario manifest is intentionally small and stable for fast contract regression tests. The current fixture has **47 source-seed rows** and remains the semantic authority for:

- one fictional event and one synthetic replay session;
- the four approved journeys (fan purchase, hospitality B2B, complaint-credit, sponsorship);
- Plan B synthetic SAP semantics and explicit unsupported-live boundaries.

For larger demos and stress-style validation, use the deterministic local CLI:

```bash
python -m scripts.volume_fixture generate --output-path <your-output-folder>
python -m scripts.volume_fixture validate --output-path <your-output-folder>
```

Default generation exports **10,000 customer parties and 25,000 commercial orders** plus coherent source-separated Oracle/Salesforce/SAP Plan B and synthetic operational records in JSONL files. The CLI:

- never runs on import (explicit invocation only);
- refuses overwrite by default (`--if-exists error`) and supports deterministic no-op verification (`--if-exists verify-noop`);
- supports smaller test runs via `--customer-count`, `--order-count`, and namespace separation via `--run-version` and `--seed`;
- keeps synthetic-only provenance/disclosure and records unsupported boundaries in `manifest.json`.

The user-directed #18 catalogue enrichment uses **`multi-event-v2` by default**:

| Oracle-owned entity | Per event | Total |
| --- | ---: | ---: |
| Event | 1 | 12 |
| Zone / base capacity | 8 | 96 |
| Product / SKU | 24 | 288 |
| Effective-dated price | 96 (4 per product) | 1,152 |
| Bundle component | 12 | 144 |
| **Oracle records** | **141** | **1,692** |

Six tiers of replay passes, hospitality packages, weekend bundles and explicitly
unavailable live passes form the catalogue at each event. Six hospitality suites
have saleable capacity; two standby grandstands have base capacity but no sales.
Every bundle comprises its same-event/tier hospitality and digital replay passes.
These remain the existing five Oracle tables; no customer, order or competing
reservation ledger is added to Oracle.

The **10,000 customers and 25,000 orders are global totals**, not per-event
volumes. Every event has orders across the three saleable families, a synthetic
replay session, a Salesforce campaign and sponsorship agreement, and SAP Plan B
supplier costs/allocations. Customers, sponsor organizations and vendor masters
are shared across events. Event-scoped dependent records and typed links prevent
cross-event attribution. `financialTotalsByEventSourceCurrency` supplements the
existing global source/currency totals; orders and invoices are never added
together as revenue.

Use `--catalog-profile single-event-v1` to reproduce the original volume export
with **13 Oracle records**. That profile preserves the historical namespace,
manifest parameters and generated bytes; manifests without `catalogProfile`
are validated as `single-event-v1`. The new profile records `catalogProfile`
in manifest parameters and adds it to the namespace hash, isolating all keys
from old exports even with the same seed/run. Logical record schema `1.0.0`,
the 31 JSONL paths and the generate/validate commands are unchanged. New
event-scoped dependent records also expose `eventKey`; consumers must join by
keys and use manifest counts, not assume singleton events or fixed census.
The original small P1 scenario is unchanged and independent of both profiles.

### Demo identity presentation

For the next demo sample/export, **explicitly select `--identity-profile natural-v1`**:

```text
python -m scripts.volume_fixture generate --output-path <new-demo-output-folder> --catalog-profile multi-event-v2 --identity-profile natural-v1
python -m scripts.volume_fixture validate --output-path <new-demo-output-folder>
```

This user-directed #18 follow-up combines fixed, hand-authored name components
deterministically; it does not use real-person records, external directories or
customer data. Person Party/Contact rows have `firstName`, `lastName` and a
matching `displayName`; the fan Account uses that same display name without
creating another Party. Business and sponsor Parties/Accounts have plausible
fictional company display names, no invented person Contacts. SAP Customer
business partners use their Party's display name; Supplier partners and supplier
masters share a generated company name. Contacts retain the reserved
`example.test` email addresses; no phone numbers, postal addresses or actionable
contact details are introduced. Coincidental matches to real names or companies
are possible; these names are not identity evidence or globally unique identifiers.

Synthetic provenance stays explicit in metadata (`syntheticProvenance`,
`dataOrigin`, `identityProfile`) and the manifest, **not in a `Synthetic Customer`
prefix or trial marker in Name/FirstName/LastName**. Native Salesforce field
mapping/loading is separately owned by #20; this logical export does not create
fields or authorize source writes. A loader should map Contact FirstName/LastName
from their structured values and Account Name from `displayName`, keeping any
operational marker outside visible names.

`identityProfile` is recorded in parameters and therefore the dataset digest,
but deliberately **does not enter the namespace/key hash**: changing presentation
attributes preserves every source/canonical key, relationship, population and
financial total. All Oracle catalogue rows remain byte-identical, so this
identity-only change does not require Oracle reload. Use a new output folder;
`verify-noop` refuses a mismatch instead of overwriting an earlier profile.
The default `baseline-v1` omits the new parameter and preserves both historical
catalogue profiles byte-for-byte, including old manifests. Keeping that default
is for reproducibility, not permission to use placeholder names in the next demo.
The fixed small P1 scenario is not renamed.

`multi-event-v2` requires **at least 36 orders** to cover all 12 events and three
saleable families. Smaller regression runs can explicitly select
`single-event-v1`. These are local exports, not a live reseed approval. Before
source loading, hand off the profile, base revision, manifest digest, native
adapter checks and recovery scope to #19/#20/#6; preserve existing commissioning
test records and never silently overwrite a baseline export.

The 10,000 customers are **8,000 person fans plus 2,000 non-sponsor business
organizations**, not 10,000 fans with extra organizations added. The **8 sponsor
organizations are separate**, giving 10,008 total Parties. `populationCounts`
reports `customerParties`, `fanCustomerParties`, `businessCustomerParties`, and
`sponsorParties` independently. At smaller scales, business customers number
`max(1, customer_count // 5)` and the remaining customers are fans. At least
**2 customers** are required; `customer_count=1` fails before writing output
because one Party cannot represent both required customer types.

Replay/fan-purchase orders select only person fans; hospitality and weekend-bundle
orders select only non-sponsor organization customers. Sponsors cannot buy through
either commercial journey. Fans map to a Salesforce Contact and its Account;
business customers map directly to a Salesforce Account, distinct from sponsor
Accounts. Source-only SAP Customer BPs preserve these typed Party crosswalks.
Only fans receive synthetic person Contacts and explicit marketing consent rows.
Business support cases link to the customer Account and use a null Contact with
`organization-account-no-person-contact`; no fictional contact is inferred from
an organization. In the legacy profile, three or more orders exercise all three
saleable families; smaller order counts contain the corresponding prefix.

This local export supports the synthetic data work for **issue #18**. It does not
qualify source schemas, SAP/Fabric capabilities, or any application integration.
Paths and entity names are illustrative logical mappings, not executable Oracle
DDL, verified Salesforce API mappings, or release-specific SAP tables.

The volume profile follows these additional, testable rules:

- All rows carry scenario ID/version, dataset, run, seed, schema, namespace,
  publication, fixed `asOf`, and synthetic provenance. Every key includes a
  readable run label plus a SHA-256 suffix over the **complete**
  `(scenarioId, scenarioVersion, datasetId, runVersion, seed)` tuple, plus
  `catalogProfile` for `multi-event-v2`. Punctuation
  variants do not collapse into the same namespace. The output directory is not
  an input to deterministic content.
- Party remains **Salesforce-owned**. `operational/party.jsonl` is explicitly a
  canonical projection with its own source identity and a typed `sourceReference`
  to the single Salesforce fan Contact, business-customer Account, or sponsor
  Account row; it is not another CRM
  row or an operational Party master. Source-only customer Accounts, Contacts,
  Opportunities, and local simulated command receipts also have explicit null
  canonical mappings when P1 has no separate entity for them.
- Every customer and sponsor has a source-only SAP Plan B **Customer** business
  partner, with an explicit Party/Salesforce crosswalk, not a second canonical
  Party. Customer invoices and credit memos resolve that partner and Party.
  Supplier invoices resolve a **Supplier** business partner through the supplier
  master. BP, supplier, and cost-center records have null canonical entity/key
  plus a mapping reason; none is a financial fact.
- The rich profile has fictional events every 14 days from **2030-04-06 to
  2030-09-07, 13:00–19:00 UTC**, with synthetic replay starting one day later.
  The legacy event remains **2030-06-15, 13:00–19:00 UTC**, with replay starting
  **2030-06-16 19:00 UTC**. Hospitality and bundles sell only before their event;
  replay sells afterwards (up to 90 days in the rich profile, capped at
  December 1). Each entitlement carries component
  access windows. Digital replay consumes **no physical seats**. A weekend
  bundle allocates its hospitality component once, not a seat for digital access.
  Capacity is scaled for this volume profile, not a real circuit capacity.
- Each rich product has four non-overlapping, contiguous USD price versions
  starting January 1, April 1, July 1 and October 1, ending January 1, 2031.
  Prices vary by event, tier and effective period. Order lines reference the
  exact `priceKey` applicable at `createdAt`, using half-open
  `[effectiveFrom, effectiveTo)` intervals. Unsold live passes remain unavailable
  in every event/tier/version.
- The snapshot uses **2030-12-20 00:00 UTC** business `asOf` and a separate
  **2030-12-31 23:59 UTC** publication visibility cutoff, never the machine clock.
  Masters precede purchases; price/product windows are checked at order time.
  Payment approval precedes confirmation, invoicing precedes support credit,
  and campaign touches and explicit synthetic consent decisions retain their
  own times. Historical expired hospitality access is not marked active.
- Full credit revokes unconsumed access and releases its reservation; partial
  credit preserves access state, and consumed access is never reversed. The
  profile includes full/partial and consumed/unconsumed cases at default scale.
  Operational orders remain a **separate simulated future Rayfin boundary**;
  the export is not a working command service, transactional outbox, app, or
  source adapter.
- The validator requires the exact 31 JSONL paths plus `manifest.json`, checks
  bytes, row counts, per-file checksums and the aggregate dataset digest, and
  independently checks populations, source/canonical uniqueness, scope,
  references, contract states, chronology, pricing, component capacity, and
  per-document mathematics. The digest hashes canonical JSON of namespace,
  parameters, and sorted `(path, recordCount, sha256)` file entries. It is an
  integrity check, not an authenticity signature.
- `financialTotalsBySourceCurrency` separates operational commercial gross,
  simulated outcomes and credits; Salesforce contracted/invoiced/evidenced
  sponsorship; and SAP order invoices, sponsor invoices, credit memos, supplier
  invoices/costs and allocations. The overall posted-customer-invoice total
  includes both order and sponsor invoices; `postedOrderInvoiceMinor` does not.
  These are integer USD minor units with explicitly `not_applicable` tax, not
  accounting recognition, ROI, settlement, or bank refunds.

`verify-noop` **only compares every existing local export byte** with the same
parameters and refuses mismatches or extra files. It performs no real-source
write or upsert and does not establish idempotency of a future integration.
Tests use a fresh `TemporaryDirectory` under the checkout for each test and
automatically remove only that test's own files, even after failure. No existing
demo exports or earlier test artifacts are deleted. Adversarial semantic tests
refresh both file checksums and the aggregate digest before expecting rejection.

## Event time, ingestion time, replay, and as-of visibility

Store and expose distinct clocks:

1. **Event/effective time** is when the business or race event actually occurred in its source.
2. **Source update time** is when the source last changed the record.
3. **Ingestion time** is when this platform accepted the record.
4. **Publication time** is when an immutable analytical version became visible.
5. **Playback time** is the replay clock for a `ReplayRun`, not the event's original time or the wall clock.

For business as-of queries, include only facts effective by the requested business instant and present in the selected publication whose `publishedAt` is no later than the requested visibility cutoff. For replay, additionally expose only race events with `eventTime <= playbackTime`; never leak a later lap/result because it has already been ingested. A pause freezes playback time, step advances deterministically to the next sequence, restart resets only the selected run's playback cursor, and replay runs remain isolated by `ReplayRunKey`. The package fixture uses 1x playback. A query must accept a fixed `asOf`/playback instant; it must not substitute the current machine clock.

Replay and live use the same normalized race-event contract, but different source/run labels. This fixture is synthetic replay only. Live remains unavailable until a real authorized session, source rights, freshness/latency, and recovery behavior have been verified; the application must not silently fall back to hidden replay data.

## Valid and invalid examples

| Contract | Valid | Invalid |
| --- | --- | --- |
| Identity | `PartyKey=PTY-SYN-FAN-01` maps to an Entra assignment on the server. | Joining `PartyKey` by `fan@example.com`, or accepting a browser-selected buyer. |
| Money | `{ "amountMinor": 5000, "currency": "USD", "taxTreatment": "not_applicable" }`. | `50.00` as a floating point, omitting currency, or summing USD and EUR. |
| Purchase retry | Same actor/command/idempotency key and payload returns the same `OrderKey`, receipt, and entitlement. | A repeated click creates another order, simulated payment, or entitlement. |
| Full/partial credit | Full `5000 USD` scenario credit revokes an unconsumed entitlement; partial credit leaves it active. | Calling a scenario credit a card refund, revoking access for a partial credit, or reversing consumed access. |
| ERP relationship | One commercial order links to one or more source ERP documents/lines with their own keys. | Counting a commercial order and its linked ERP order as two independent sales. |
| Replay visibility | At playback `14:01:30Z`, expose only sequence events at or before that instant. | Showing sequence data at `14:02:10Z` before the playback clock reaches it. |
| Provenance | A Plan B document is labeled `synthetic-sap-scenario` and names its dataset/publication. | Claiming the fixture is a connected SAP invoice or mixing it into a Plan A publication. |

## Four acceptance journeys

The fixture in `scenarios/canonical-scenario-manifest.json` pins the input keys, command/idempotency keys, expected state transitions, documents, and reconciled counts for each journey. Expected amounts use integer USD minor units. Each journey is deterministic and testable without an external service.

1. **Fan purchase.** Inputs: synthetic Oracle-mapped `ProductKey`, `PriceKey`, `EventKey`, server-assigned `PartyKey`, and an idempotent purchase command. Expected: one confirmed `OrderKey`/line, one successful `PaymentSimulationKey`, one active `EntitlementKey`, and one separately keyed Plan B scenario invoice/document link. Repeating the command returns the same receipt and creates no additional records.
2. **Hospitality B2B.** Inputs: synthetic Salesforce-mapped buyer account/opportunity, hospitality `ProductKey`/price, `EventKey`, and requested capacity. Expected: one confirmed reservation and commercial order, one Plan B customer invoice, and separately traceable event/customer cost allocation; Hub result groups by event and buyer without duplicating the ERP document as sales.
3. **Complaint and credit.** Inputs: the fan's own `CaseKey`, linked order/entitlement, and support evidence. Expected: a linked open/resolved CRM case, an authorized full `ScenarioCredit`, a separate Plan B credit document, entitlement revocation while unconsumed, and a reconciliation receipt. Fan commands cannot approve the credit or read another party's case.
4. **Sponsorship.** Inputs: synthetic sponsor account, agreement, commitment, event, invoice, and supplier-cost references. Expected: separately visible contracted, invoiced, fulfilled, and allocated-cost amounts with source links and follow-up state. Exposure or fulfillment is not causal ROI or conversion.

## Change control

Changes to keys, grains, allowed operations, state transitions, monetary interpretation, credit/access policy, clocks, or publication isolation require a contract-version change plus updated manifest and tests. A source adapter may add source-specific fields but cannot change shared semantics.
