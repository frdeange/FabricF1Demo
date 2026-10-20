# Canonical business and data contracts

This package defines the shared business boundary for the promoter Hub and Fan Experience. The machine-readable entity registry is `contracts/canonical-contracts.json`; this document defines behavior that must remain true across source adapters, operational commands, publications, and app projections.

All examples and the companion manifest are synthetic. Plan A means a future, separately authorized real SAP adapter. Plan B is a synthetic SAP-shaped scenario ledger processed with native Fabric capabilities. No SAP, Oracle, Salesforce, sports-data provider, live race, customer, or commercial relationship is connected or represented by these fixtures.

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

**Plan A** retains the same canonical contract but maps to an actually authorized SAP ERP through a supported interface; source document numbers and shapes remain source-specific. No Plan A source is enabled by this package. **Plan B** uses a deterministic synthetic source and native Fabric processing; its documents are visibly scenario documents and are not evidence of a connected SAP system. Oracle/Salesforce source mappings remain separate from the SAP choice. Adapters normalize both plans; do not force fictional tables to mimic a specific SAP release.

`SourcePublication` is immutable once published. A corrected/updated result creates a new publication with its own key and `asOf`; consumers select exactly one publication/run. Publication metadata distinguishes source time from ingestion/publication time. Do not silently combine an older SAP publication with a newer operational or sports publication.

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
