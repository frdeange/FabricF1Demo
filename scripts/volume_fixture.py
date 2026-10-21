from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_CUSTOMER_COUNT = 10_000
DEFAULT_ORDER_COUNT = 25_000
DEFAULT_SEED = "f1-volume-fixture-001"
DEFAULT_RUN_VERSION = "run-v1"
DEFAULT_SCHEMA_VERSION = "1.0.0"
DEFAULT_SCENARIO_ID = "synthetic-grand-prix-promoter-v1"
DEFAULT_SCENARIO_VERSION = "1.0.0"
DEFAULT_DATASET_ID = "synthetic-gp-dataset-volume-v1"
DEFAULT_PUBLICATION_KEY = "PUB-BULK-001"
LEGACY_PROFILE = "single-event-v1"
DEFAULT_CATALOG_PROFILE = "multi-event-v2"

# Logical source mappings, not qualified schemas or executable source adapters.
# path: (source system, logical source entity, canonical entity, row key)
FILE_SPECS = {
    "oracle/oracle_event.jsonl": ("oracle", "OracleEvent", "Event", "eventKey"),
    "oracle/oracle_circuit_zone.jsonl": ("oracle", "OracleCircuitZone", "CircuitZone", "zoneKey"),
    "oracle/oracle_catalog_product.jsonl": ("oracle", "OracleCatalogProduct", "Product", "productKey"),
    "oracle/oracle_price_list_entry.jsonl": ("oracle", "OraclePriceListEntry", "Price", "priceKey"),
    "oracle/oracle_bundle_component.jsonl": ("oracle", "OracleBundleComponent", "BundleComponent", "bundleComponentKey"),
    "operational/replay_session.jsonl": ("synthetic-scenario-generator", "RaceSession", "RaceSession", "sessionKey"),
    "operational/party.jsonl": ("canonical-projection", "SalesforcePartyProjection", "Party", "partyKey"),
    "operational/commercial_order.jsonl": ("synthetic-operational", "CommercialOrder", "CommercialOrder", "orderKey"),
    "operational/commercial_order_line.jsonl": ("synthetic-operational", "CommercialOrderLine", "CommercialOrderLine", "orderLineKey"),
    "operational/payment_simulation.jsonl": ("synthetic-operational", "PaymentSimulation", "PaymentSimulation", "paymentSimulationKey"),
    "operational/reservation.jsonl": ("synthetic-operational", "Reservation", "Reservation", "reservationKey"),
    "operational/entitlement.jsonl": ("synthetic-operational", "Entitlement", "Entitlement", "entitlementKey"),
    "operational/scenario_credit.jsonl": ("synthetic-operational", "ScenarioCredit", "ScenarioCredit", "scenarioCreditKey"),
    "operational/command_receipt.jsonl": ("synthetic-operational", "CommandReceipt", None, "commandReceiptKey"),
    "salesforce/account.jsonl": ("salesforce", "Account", None, "accountKey"),
    "salesforce/contact.jsonl": ("salesforce", "Contact", None, "contactKey"),
    "salesforce/consent.jsonl": ("salesforce", "Consent", "Consent", "consentKey"),
    "salesforce/campaign.jsonl": ("salesforce", "Campaign", "Campaign", "campaignKey"),
    "salesforce/campaign_touch.jsonl": ("salesforce", "CampaignTouch", "CampaignTouch", "campaignTouchKey"),
    "salesforce/opportunity.jsonl": ("salesforce", "Opportunity", None, "opportunityKey"),
    "salesforce/case.jsonl": ("salesforce", "Case", "CRMCase", "caseKey"),
    "salesforce/sponsorship_agreement.jsonl": ("salesforce", "SponsorshipAgreement", "SponsorshipAgreement", "agreementKey"),
    "salesforce/sponsorship_commitment.jsonl": ("salesforce", "SponsorshipCommitment", "SponsorshipCommitment", "commitmentKey"),
    "sap_plan_b/business_partner.jsonl": ("sap-plan-b-synthetic", "BusinessPartner", None, "sourceKey"),
    "sap_plan_b/supplier.jsonl": ("sap-plan-b-synthetic", "Supplier", None, "sourceKey"),
    "sap_plan_b/cost_center.jsonl": ("sap-plan-b-synthetic", "CostCenter", None, "sourceKey"),
    "sap_plan_b/sap_document.jsonl": ("sap-plan-b-synthetic", "SAPDocument", "ERPDocument", "erpDocumentKey"),
    "sap_plan_b/sap_document_line.jsonl": ("sap-plan-b-synthetic", "SAPDocumentLine", "ERPDocumentLine", "erpDocumentLineKey"),
    "sap_plan_b/document_link.jsonl": ("sap-plan-b-synthetic", "DocumentLink", "DocumentLink", "documentLinkKey"),
    "sap_plan_b/supplier_cost.jsonl": ("sap-plan-b-synthetic", "SupplierCost", "SupplierCost", "supplierCostKey"),
    "sap_plan_b/sap_cost_allocation.jsonl": ("sap-plan-b-synthetic", "SAPCostAllocation", "CostAllocation", "costAllocationKey"),
}
NULL_MAPPING_REASON = "source-reference-only-no-canonical-entity"


class ValidationError(RuntimeError):
    """Raised when a generated export fails validation."""


@dataclass(frozen=True)
class GenerationParameters:
    output_path: Path
    customer_count: int = DEFAULT_CUSTOMER_COUNT
    order_count: int = DEFAULT_ORDER_COUNT
    seed: str = DEFAULT_SEED
    run_version: str = DEFAULT_RUN_VERSION
    schema_version: str = DEFAULT_SCHEMA_VERSION
    scenario_id: str = DEFAULT_SCENARIO_ID
    scenario_version: str = DEFAULT_SCENARIO_VERSION
    dataset_id: str = DEFAULT_DATASET_ID
    if_exists: str = "error"
    catalog_profile: str = DEFAULT_CATALOG_PROFILE

    def as_dict(self) -> dict[str, Any]:
        result = {
            "customerCount": self.customer_count,
            "orderCount": self.order_count,
            "seed": self.seed,
            "runVersion": self.run_version,
            "schemaVersion": self.schema_version,
            "scenarioId": self.scenario_id,
            "scenarioVersion": self.scenario_version,
            "datasetId": self.dataset_id,
        }
        if self.catalog_profile != LEGACY_PROFILE:
            result["catalogProfile"] = self.catalog_profile
        return result

    @property
    def namespace(self) -> str:
        dimensions = [self.scenario_id, self.scenario_version, self.dataset_id, self.run_version, self.seed]
        if self.catalog_profile != LEGACY_PROFILE:
            dimensions.append(self.catalog_profile)
        return json.dumps(
            dimensions,
            separators=(",", ":"),
        )

    @property
    def key_token(self) -> str:
        return f"{_safe_token(self.run_version)[:24]}-{_sha256_bytes(self.namespace.encode('utf-8'))}"

    @property
    def source_tenant(self) -> str:
        return f"synthetic-{self.key_token}"

    @property
    def business_customer_count(self) -> int:
        return max(1, self.customer_count // 5)

    @property
    def fan_customer_count(self) -> int:
        return self.customer_count - self.business_customer_count

    def validate(self) -> None:
        for name, value in (("customer_count", self.customer_count), ("order_count", self.order_count)):
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer.")
        if self.customer_count < 2:
            raise ValueError("customer_count must be at least 2: both person fans and organization hospitality buyers are required.")
        for name in ("seed", "run_version", "scenario_id", "scenario_version", "dataset_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string.")
        if self.schema_version != DEFAULT_SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema_version: {self.schema_version!r}.")
        if self.if_exists not in {"error", "verify-noop"}:
            raise ValueError("if_exists must be error or verify-noop.")
        if self.catalog_profile not in {LEGACY_PROFILE, DEFAULT_CATALOG_PROFILE}:
            raise ValueError("Unsupported catalog_profile.")
        if self.catalog_profile == DEFAULT_CATALOG_PROFILE and self.order_count < 36:
            raise ValueError("multi-event-v2 requires at least 36 orders to cover all events and saleable families.")


def _safe_token(value: str) -> str:
    chars = []
    for char in value.upper():
        if char.isalnum():
            chars.append(char)
        else:
            chars.append("-")
    token = "".join(chars).strip("-")
    while "--" in token:
        token = token.replace("--", "-")
    return token or "RUN"


def _random_for(seed: str, namespace: str, scope: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}|{namespace}|{scope}".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_line(record: dict[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _build_common(
    *,
    canonical_key: str,
    source_system: str,
    source_tenant: str,
    source_entity: str,
    source_key: str,
    source_updated_at: str,
    ingested_at: str,
    schema_version: str,
    record_state: str,
    publication_key: str,
) -> dict[str, Any]:
    return {
        "canonicalKey": canonical_key,
        "sourceSystem": source_system,
        "sourceTenant": source_tenant,
        "sourceEntity": source_entity,
        "sourceKey": source_key,
        "sourceUpdatedAt": source_updated_at,
        "ingestedAt": ingested_at,
        "schemaVersion": schema_version,
        "recordState": record_state,
        "publicationKey": publication_key,
        "dataOrigin": "synthetic-only",
    }


def _append_record(
    registry: dict[str, list[dict[str, Any]]],
    relative_path: str,
    record: dict[str, Any],
) -> None:
    registry.setdefault(relative_path, []).append(record)


def _entity_counts(records: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter] = defaultdict(Counter)
    for rows in records.values():
        for row in rows:
            counts[row["sourceSystem"]][row["sourceEntity"]] += 1
    return {source: dict(entities) for source, entities in counts.items()}


def _financial_totals(records: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, dict[str, int]]]:
    totals: dict[str, Any] = {}

    def add(row: dict[str, Any], measure: str, amount: int) -> None:
        bucket = totals.setdefault(row["sourceSystem"], {}).setdefault(row["currency"], {})
        bucket[measure] = bucket.get(measure, 0) + amount

    measures = {
        "operational/commercial_order.jsonl": (("commercialOrderGrossMinor", "grossMinor"),),
        "operational/payment_simulation.jsonl": (("approvedSimulatedPaymentMinor", "amountMinor"),),
        "operational/scenario_credit.jsonl": (("scenarioCreditMinor", "amountMinor"),),
        "salesforce/sponsorship_agreement.jsonl": (("sponsorshipContractedMinor", "contractedMinor"),),
        "salesforce/sponsorship_commitment.jsonl": (
            ("sponsorshipInvoicedMinor", "invoicedMinor"), ("sponsorshipFulfilledMinor", "fulfilledMinor")),
        "sap_plan_b/supplier_cost.jsonl": (("supplierCostMinor", "amountMinor"),),
        "sap_plan_b/sap_cost_allocation.jsonl": (("allocatedCostMinor", "amountMinor"),),
    }
    for path, fields in measures.items():
        for row in records[path]:
            for measure, field in fields:
                add(row, measure, row[field])
    for doc in records["sap_plan_b/sap_document.jsonl"]:
        if doc["documentType"] == "customer_invoice":
            add(doc, "postedCustomerInvoiceMinor", doc["amountMinor"])
            add(doc, "postedSponsorshipInvoiceMinor" if "sponsorshipAgreementKey" in doc
                else "postedOrderInvoiceMinor", doc["amountMinor"])
        elif doc["documentType"] == "customer_credit_memo":
            add(doc, "postedCustomerCreditMemoMinor", doc["amountMinor"])
        else:
            add(doc, "postedSupplierInvoiceMinor", doc["amountMinor"])
    return totals


def _event_financial_totals(records: dict[str, list[dict[str, Any]]]) -> dict:
    grouped: dict[str, dict[str, list]] = {
        event["eventKey"]: {path: [] for path in FILE_SPECS}
        for event in records["oracle/oracle_event.jsonl"]
    }
    for path, rows in records.items():
        for row in rows:
            if "eventKey" in row:
                grouped[row["eventKey"]][path].append(row)
    return {key: _financial_totals(rows) for key, rows in grouped.items()}


def _dataset_digest(manifest: dict[str, Any]) -> str:
    digest_input = {
        "namespace": manifest["namespace"],
        "parameters": manifest["parameters"],
        "files": [{k: item[k] for k in ("path", "recordCount", "sha256")} for item in manifest["files"]],
    }
    return _sha256_bytes(_json_line(digest_input).encode("utf-8"))


def _catalog_contexts(records: dict[str, list[dict[str, Any]]],
                      params: GenerationParameters) -> list[dict[str, Any]]:
    """Expand the baseline catalogue before generating dependent business records."""
    event_path = "oracle/oracle_event.jsonl"
    zone_path = "oracle/oracle_circuit_zone.jsonl"
    product_path = "oracle/oracle_catalog_product.jsonl"
    price_path = "oracle/oracle_price_list_entry.jsonl"
    component_path = "oracle/oracle_bundle_component.jsonl"
    session_path = "operational/replay_session.jsonl"
    if params.catalog_profile == LEGACY_PROFILE:
        return [{
            "event": records[event_path][0], "session": records[session_path][0],
            "products": {r["productCode"]: [r] for r in records[product_path]},
            "prices": {r["productKey"]: [r] for r in records[price_path]},
        }]

    templates = {path: records[path] for path in
                 (event_path, zone_path, product_path, price_path, component_path, session_path)}
    for path in templates:
        records[path] = []
    contexts = []
    boundaries = ["2030-01-01T00:00:00Z", "2030-04-01T00:00:00Z",
                  "2030-07-01T00:00:00Z", "2030-10-01T00:00:00Z", "2031-01-01T00:00:00Z"]

    def clone(template: dict, key_field: str, suffix: str, **fields: Any) -> dict:
        row = copy.deepcopy(template)
        row[key_field] += suffix
        row["canonicalKey"] = row[key_field]
        row["sourceKey"] += suffix
        row.update(fields)
        return row

    for event_index in range(12):
        suffix = f"-E{event_index + 1:02}"
        start = datetime(2030, 4, 6, 13, tzinfo=timezone.utc) + timedelta(days=14 * event_index)
        end = start + timedelta(hours=6)
        replay = end + timedelta(days=1)
        event = clone(
            templates[event_path][0], "eventKey", suffix,
            displayName=f"Synthetic Grand Prix {event_index + 1:02}",
            eventStartAt=_iso(start), eventEndAt=_iso(end),
            sourceUpdatedAt=_iso(end), ingestedAt=_iso(end + timedelta(minutes=1)),
            bulkProfile=DEFAULT_CATALOG_PROFILE,
        )
        session = clone(
            templates[session_path][0], "sessionKey", suffix,
            eventKey=event["eventKey"], displayName=f"Synthetic Race Replay {event_index + 1:02}",
            sessionStartAt=_iso(start), sessionEndAt=_iso(end), availableFrom=_iso(replay),
            sourceUpdatedAt=_iso(replay), ingestedAt=_iso(replay + timedelta(minutes=1)),
        )
        records[event_path].append(event)
        records[session_path].append(session)
        zones = []
        for zone_index in range(8):
            zone = clone(
                templates[zone_path][1], "zoneKey", f"{suffix}-Z{zone_index + 1:02}",
                eventKey=event["eventKey"],
                displayName=(f"Hospitality Suite {zone_index + 1:02}" if zone_index < 6
                             else f"Standby Grandstand {zone_index - 5:02}"),
            )
            zones.append(zone)
            records[zone_path].append(zone)
        products_by_code: dict[str, list] = defaultdict(list)
        prices_by_product: dict[str, list] = {}
        for variant in range(6):
            variant_suffix = f"{suffix}-T{variant + 1:02}"
            for template in templates[product_path]:
                code = template["productCode"]
                replay_only = code == "PRD-REPLAY"
                product = clone(
                    template, "productKey", variant_suffix, eventKey=event["eventKey"],
                    displayName=f"{template['displayName']} / tier {variant + 1:02} / GP {event_index + 1:02}",
                    saleFrom=_iso(replay) if replay_only else template["saleFrom"],
                    saleTo=_iso(min(replay + timedelta(days=90), datetime(2030, 12, 1, tzinfo=timezone.utc)))
                    if replay_only else _iso(start),
                    accessFrom=_iso(replay if replay_only else start),
                    accessTo=session["availableTo"] if code in {"PRD-REPLAY", "PRD-WEEKEND"} else _iso(end),
                    capacityPerUnit={zones[variant]["zoneKey"]: 1} if code == "PRD-HOSP" else {},
                )
                products_by_code[code].append(product)
                records[product_path].append(product)
                template_price = next(p for p in templates[price_path] if p["productKey"] == template["productKey"])
                versions = []
                for version in range(4):
                    price = clone(
                        template_price, "priceKey", f"{variant_suffix}-V{version + 1:02}",
                        eventKey=event["eventKey"], productKey=product["productKey"],
                        amountMinor=template_price["amountMinor"] * (100 + 10 * variant + 2 * event_index + 5 * version) // 100,
                        effectiveFrom=boundaries[version], effectiveTo=boundaries[version + 1],
                        sourceUpdatedAt=boundaries[version],
                        ingestedAt=_iso(_timestamp(boundaries[version]) + timedelta(minutes=5)),
                    )
                    versions.append(price)
                    records[price_path].append(price)
                prices_by_product[product["productKey"]] = versions
            for component_index, template in enumerate(templates[component_path]):
                component_code = "PRD-REPLAY" if component_index == 0 else "PRD-HOSP"
                component = clone(
                    template, "bundleComponentKey", variant_suffix,
                    eventKey=event["eventKey"],
                    bundleProductKey=products_by_code["PRD-WEEKEND"][variant]["productKey"],
                    componentProductKey=products_by_code[component_code][variant]["productKey"],
                )
                records[component_path].append(component)
        contexts.append({"event": event, "session": session, "products": dict(products_by_code),
                         "prices": prices_by_product})
    return contexts


def build_export_records(params: GenerationParameters) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    params.validate()

    run_token = params.key_token
    rng = _random_for(params.seed, params.namespace, "dataset")
    records: dict[str, list[dict[str, Any]]] = {}

    event_start = datetime(2030, 6, 15, 13, 0, tzinfo=timezone.utc)
    event_end = datetime(2030, 6, 15, 19, 0, tzinfo=timezone.utc)
    campaign_start = datetime(2030, 2, 1, 9, 0, tzinfo=timezone.utc)
    campaign_end = datetime(2030, 12, 15, 18, 0, tzinfo=timezone.utc)
    price_start = datetime(2030, 1, 1, 0, 0, tzinfo=timezone.utc)
    price_end = datetime(2031, 1, 1, 0, 0, tzinfo=timezone.utc)
    source_published_at = datetime(2030, 12, 31, 23, 59, tzinfo=timezone.utc)
    as_of = datetime(2030, 12, 20, 0, 0, tzinfo=timezone.utc)
    replay_start = event_end + timedelta(days=1)
    master_at = price_start

    event_key = f"EVT-BULK-{run_token}-001"
    session_key = f"SES-BULK-{run_token}-001"
    campaign_key = f"CAMPAIGN-BULK-{run_token}-001"
    source_tenant = params.source_tenant
    publication_key = f"{DEFAULT_PUBLICATION_KEY}-{run_token}"

    product_defs = [
        ("PRD-REPLAY", "Replay Pass", "available", 5_000),
        ("PRD-LIVE", "Live Race Pass", "unavailable-no-qualified-live-source", 7_500),
        ("PRD-HOSP", "Hospitality Package", "available", 100_000),
        ("PRD-WEEKEND", "Weekend Bundle", "available", 105_000),
    ]
    zone_defs = [
        ("ZONE-NORTH", "Synthetic Grandstand North"),
        ("ZONE-PADDOCK", "Synthetic Paddock"),
    ]

    product_keys: dict[str, str] = {}
    price_keys: dict[str, str] = {}

    event_record = _build_common(
        canonical_key=event_key,
        source_system="oracle",
        source_tenant=source_tenant,
        source_entity="OracleEvent",
        source_key=f"ORA-EVT-{run_token}-001",
        source_updated_at=_iso(event_end),
        ingested_at=_iso(event_end + timedelta(minutes=1)),
        schema_version=params.schema_version,
        record_state="completed",
        publication_key=publication_key,
    )
    event_record.update(
        {
            "eventKey": event_key,
            "displayName": "Synthetic Grand Prix Demo Bulk Profile",
            "eventStartAt": _iso(event_start),
            "eventEndAt": _iso(event_end),
            "createdAt": _iso(master_at),
            "bulkProfile": "volume-10k-customers-25k-orders",
            "namespace": params.namespace,
        }
    )
    _append_record(records, "oracle/oracle_event.jsonl", event_record)

    session_record = _build_common(
        canonical_key=session_key,
        source_system="synthetic-scenario-generator",
        source_tenant=source_tenant,
        source_entity="RaceSession",
        source_key=f"SRC-SESSION-{run_token}-001",
        source_updated_at=_iso(replay_start),
        ingested_at=_iso(replay_start + timedelta(minutes=1)),
        schema_version=params.schema_version,
        record_state="available",
        publication_key=publication_key,
    )
    session_record.update(
        {
            "sessionKey": session_key,
            "eventKey": event_key,
            "displayName": "Synthetic Race Replay (Bulk)",
            "playbackMode": "synthetic-replay",
            "sessionStartAt": _iso(event_start),
            "sessionEndAt": _iso(event_end),
            "availableFrom": _iso(replay_start),
            "availableTo": _iso(price_end),
        }
    )
    _append_record(records, "operational/replay_session.jsonl", session_record)

    for index, (zone_code, display_name) in enumerate(zone_defs, start=1):
        zone_key = f"{zone_code}-{run_token}"
        zone_record = _build_common(
            canonical_key=zone_key,
            source_system="oracle",
            source_tenant=source_tenant,
            source_entity="OracleCircuitZone",
            source_key=f"ORA-ZONE-{run_token}-{index:03}",
            source_updated_at=_iso(master_at),
            ingested_at=_iso(master_at + timedelta(minutes=2)),
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        zone_record.update(
            {
                "zoneKey": zone_key,
                "eventKey": event_key,
                "displayName": display_name,
                "capacityUnit": "seats",
                "capacityProfile": "bulk-scaled",
                "capacity": 0,  # set after order generation
            }
        )
        _append_record(records, "oracle/oracle_circuit_zone.jsonl", zone_record)

    for index, (code, display_name, availability, amount_minor) in enumerate(product_defs, start=1):
        product_key = f"{code}-{run_token}"
        product_keys[code] = product_key
        product_record = _build_common(
            canonical_key=product_key,
            source_system="oracle",
            source_tenant=source_tenant,
            source_entity="OracleCatalogProduct",
            source_key=f"ORA-PRD-{run_token}-{index:03}",
            source_updated_at=_iso(master_at),
            ingested_at=_iso(master_at + timedelta(minutes=3)),
            schema_version=params.schema_version,
            record_state="published",
            publication_key=publication_key,
        )
        product_record.update(
            {
                "productKey": product_key,
                "eventKey": event_key,
                "displayName": display_name,
                "availability": availability,
                "productCode": code,
                "saleFrom": _iso(replay_start if code == "PRD-REPLAY" else campaign_start),
                "saleTo": _iso(datetime(2030, 12, 1, tzinfo=timezone.utc)
                               if code == "PRD-REPLAY" else event_start),
                "accessFrom": _iso(replay_start if code == "PRD-REPLAY" else event_start),
                "accessTo": _iso(price_end if code in {"PRD-REPLAY", "PRD-WEEKEND"} else event_end),
                "capacityPerUnit": {f"ZONE-PADDOCK-{run_token}": 1} if code == "PRD-HOSP" else {},
            }
        )
        _append_record(records, "oracle/oracle_catalog_product.jsonl", product_record)

        price_key = f"PRICE-{code}-{run_token}"
        price_keys[code] = price_key
        price_record = _build_common(
            canonical_key=price_key,
            source_system="oracle",
            source_tenant=source_tenant,
            source_entity="OraclePriceListEntry",
            source_key=f"ORA-PRICE-{run_token}-{index:03}",
            source_updated_at=_iso(price_start),
            ingested_at=_iso(price_start + timedelta(minutes=5)),
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        price_record.update(
            {
                "priceKey": price_key,
                "eventKey": event_key,
                "productKey": product_key,
                "amountMinor": amount_minor,
                "currency": "USD",
                "taxTreatment": "not_applicable",
                "effectiveFrom": _iso(price_start),
                "effectiveTo": _iso(price_end),
            }
        )
        _append_record(records, "oracle/oracle_price_list_entry.jsonl", price_record)

    bundle_component_defs = [
        ("REPLAY", 1),
        ("HOSP", 1),
    ]
    for index, (component_code, quantity) in enumerate(bundle_component_defs, start=1):
        component_key = f"BUNDLE-COMP-{run_token}-{index:03}"
        component_record = _build_common(
            canonical_key=component_key,
            source_system="oracle",
            source_tenant=source_tenant,
            source_entity="OracleBundleComponent",
            source_key=f"ORA-BUNDLE-COMP-{run_token}-{index:03}",
            source_updated_at=_iso(master_at),
            ingested_at=_iso(master_at + timedelta(minutes=4)),
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        component_record.update(
            {
                "bundleComponentKey": component_key,
                "bundleProductKey": product_keys["PRD-WEEKEND"],
                "componentProductKey": product_keys[f"PRD-{component_code}"],
                "quantity": quantity,
            }
        )
        _append_record(records, "oracle/oracle_bundle_component.jsonl", component_record)

    contexts = _catalog_contexts(records, params)
    rich = params.catalog_profile == DEFAULT_CATALOG_PROFILE
    products_by_key = {p["productKey"]: p for p in records["oracle/oracle_catalog_product.jsonl"]}
    bundles_by_key: dict[str, list] = defaultdict(list)
    for component in records["oracle/oracle_bundle_component.jsonl"]:
        bundles_by_key[component["bundleProductKey"]].append(component)

    campaign_record = _build_common(
        canonical_key=campaign_key,
        source_system="salesforce",
        source_tenant=source_tenant,
        source_entity="Campaign",
        source_key=f"SF-CAMP-{run_token}-001",
        source_updated_at=_iso(campaign_end),
        ingested_at=_iso(campaign_end + timedelta(minutes=3)),
        schema_version=params.schema_version,
        record_state="ended",
        publication_key=publication_key,
    )
    campaign_record.update(
        {
            "campaignKey": campaign_key,
            "displayName": "Synthetic Replay & Hospitality Growth",
            "startAt": _iso(campaign_start),
            "endAt": _iso(campaign_end),
            "createdAt": _iso(campaign_start),
        }
    )
    _append_record(records, "salesforce/campaign.jsonl", campaign_record)
    if rich:
        records["salesforce/campaign.jsonl"] = []
        for event_index, context in enumerate(contexts, 1):
            campaign = copy.deepcopy(campaign_record)
            scoped_key = f"{campaign_key}-E{event_index:02}"
            campaign.update(campaignKey=scoped_key, canonicalKey=scoped_key,
                            sourceKey=f"{campaign['sourceKey']}-E{event_index:02}",
                            eventKey=context["event"]["eventKey"],
                            displayName=f"Synthetic GP {event_index:02} Replay & Hospitality")
            records["salesforce/campaign.jsonl"].append(campaign)

    customer_party_keys: list[str] = []
    customer_account_keys: list[str] = []
    contact_keys: list[str | None] = []
    for index in range(1, params.customer_count + 1):
        is_business = index > params.fan_customer_count
        party_key = f"PTY-CUST-{run_token}-{index:05}"
        account_key = f"SF-ACCOUNT-{run_token}-{index:05}"
        contact_key = f"SF-CONTACT-{run_token}-{index:05}"
        customer_party_keys.append(party_key)
        customer_account_keys.append(account_key)
        contact_keys.append(None if is_business else contact_key)

        party_record = _build_common(
            canonical_key=party_key,
            source_system="salesforce",
            source_tenant=source_tenant,
            source_entity="Account" if is_business else "Contact",
            source_key=account_key if is_business else contact_key,
            source_updated_at=_iso(master_at),
            ingested_at=_iso(master_at + timedelta(minutes=4)),
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        party_record.update(
            {
                "partyKey": party_key,
                "partyType": "organization" if is_business else "person",
                "partyRole": "customer",
                "customerType": "business" if is_business else "fan",
                "displayName": f"Synthetic Business Customer {index:05}" if is_business else f"Synthetic Customer {index:05}",
                "email": None if is_business else f"customer.{index:05}@example.test",
                "accountSourceKey": account_key,
            }
        )
        _append_record(records, "operational/party.jsonl", party_record)

        account_record = _build_common(
            canonical_key=account_key,
            source_system="salesforce",
            source_tenant=source_tenant,
            source_entity="Account",
            source_key=account_key,
            source_updated_at=party_record["sourceUpdatedAt"],
            ingested_at=party_record["ingestedAt"],
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        account_record.update(
            {
                "accountKey": account_key,
                "partyKey": party_key,
                "displayName": party_record["displayName"],
                "segment": "hospitality-buyer" if is_business else ("fan", "family", "enthusiast", "vip")[index % 4],
                "channelPreference": ("digital", "reseller", "direct")[index % 3],
            }
        )
        _append_record(records, "salesforce/account.jsonl", account_record)
        if is_business:
            continue

        contact_record = _build_common(
            canonical_key=contact_key,
            source_system="salesforce",
            source_tenant=source_tenant,
            source_entity="Contact",
            source_key=contact_key,
            source_updated_at=party_record["sourceUpdatedAt"],
            ingested_at=party_record["ingestedAt"],
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        contact_record.update(
            {
                "contactKey": contact_key,
                "accountSourceKey": account_key,
                "partyKey": party_key,
                "displayName": party_record["displayName"],
                "email": party_record["email"],
            }
        )
        _append_record(records, "salesforce/contact.jsonl", contact_record)

        consent_state = "withdrawn" if index % 17 == 0 else "granted"
        consent_record = _build_common(
            canonical_key=f"CONSENT-{run_token}-{index:05}",
            source_system="salesforce",
            source_tenant=source_tenant,
            source_entity="Consent",
            source_key=f"SF-CONSENT-{run_token}-{index:05}",
            source_updated_at=party_record["sourceUpdatedAt"],
            ingested_at=party_record["ingestedAt"],
            schema_version=params.schema_version,
            record_state=consent_state,
            publication_key=publication_key,
        )
        consent_record.update(
            {
                "consentKey": consent_record["canonicalKey"],
                "partyKey": party_key,
                "purpose": "synthetic-demo-marketing",
                "channel": "email",
                "decisionBasis": "explicit-synthetic-fixture-not-inferred",
                "decidedAt": _iso(master_at),
                "effectiveAt": _iso(master_at),
                "state": consent_state,
            }
        )
        _append_record(records, "salesforce/consent.jsonl", consent_record)

    sponsor_party_count = max(8, params.customer_count // 2_000)
    sponsor_account_records: list[dict[str, Any]] = []
    for index in range(1, sponsor_party_count + 1):
        party_key = f"PTY-SPONSOR-{run_token}-{index:03}"
        account_key = f"SF-SPONSOR-ACCOUNT-{run_token}-{index:03}"
        sponsor_party = _build_common(
            canonical_key=party_key,
            source_system="salesforce",
            source_tenant=source_tenant,
            source_entity="Account",
            source_key=account_key,
            source_updated_at=_iso(master_at),
            ingested_at=_iso(master_at + timedelta(minutes=2)),
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        sponsor_party.update(
            {
                "partyKey": party_key,
                "partyType": "organization",
                "partyRole": "sponsor",
                "customerType": None,
                "displayName": f"Synthetic Sponsor {index:03}",
                "email": None,
            }
        )
        _append_record(records, "operational/party.jsonl", sponsor_party)

        sponsor_account = _build_common(
            canonical_key=account_key,
            source_system="salesforce",
            source_tenant=source_tenant,
            source_entity="Account",
            source_key=account_key,
            source_updated_at=sponsor_party["sourceUpdatedAt"],
            ingested_at=sponsor_party["ingestedAt"],
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        sponsor_account.update(
            {
                "accountKey": account_key,
                "partyKey": party_key,
                "displayName": sponsor_party["displayName"],
                "segment": "sponsor",
                "channelPreference": "direct",
            }
        )
        sponsor_account_records.append(sponsor_account)
        _append_record(records, "salesforce/account.jsonl", sponsor_account)

    vendor_master_count = max(6, params.order_count // 5_000)
    for index in range(1, vendor_master_count + 1):
        bp_key = f"SAP-BP-{run_token}-{index:03}"
        supplier_key = f"SAP-SUPPLIER-{run_token}-{index:03}"
        cost_center_key = f"SAP-COSTCENTER-{run_token}-{index:03}"
        source_updated_at = _iso(master_at)
        ingested_at = _iso(master_at + timedelta(minutes=2))

        bp_record = _build_common(
            canonical_key=f"SAP-MASTER-{run_token}-BP-{index:03}",
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="BusinessPartner",
            source_key=bp_key,
            source_updated_at=source_updated_at,
            ingested_at=ingested_at,
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        bp_record.update(
            {
                "canonicalEntity": None,
                "canonicalKey": None,
                "canonicalNullReason": "source-reference-only-no-canonical-entity",
                "mappingStatus": "source-reference-only-no-canonical-entity",
                "displayName": f"Synthetic Vendor BP {index:03}",
                "bpRole": "Supplier",
            }
        )
        _append_record(records, "sap_plan_b/business_partner.jsonl", bp_record)

        supplier_record = _build_common(
            canonical_key=f"SAP-MASTER-{run_token}-SUP-{index:03}",
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="Supplier",
            source_key=supplier_key,
            source_updated_at=source_updated_at,
            ingested_at=ingested_at,
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        supplier_record.update(
            {
                "canonicalEntity": None,
                "canonicalKey": None,
                "canonicalNullReason": "source-reference-only-no-canonical-entity",
                "mappingStatus": "source-reference-only-no-canonical-entity",
                "bpSourceKey": bp_key,
                "displayName": f"Synthetic Supplier {index:03}",
            }
        )
        _append_record(records, "sap_plan_b/supplier.jsonl", supplier_record)

        cost_center_record = _build_common(
            canonical_key=f"SAP-MASTER-{run_token}-CC-{index:03}",
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="CostCenter",
            source_key=cost_center_key,
            source_updated_at=source_updated_at,
            ingested_at=ingested_at,
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        cost_center_record.update(
            {
                "canonicalEntity": None,
                "canonicalKey": None,
                "canonicalNullReason": "source-reference-only-no-canonical-entity",
                "mappingStatus": "source-reference-only-no-canonical-entity",
                "displayName": f"Synthetic Cost Center {index:03}",
            }
        )
        _append_record(records, "sap_plan_b/cost_center.jsonl", cost_center_record)

    order_totals = Counter()
    zone_demands = Counter()
    order_keys: list[str] = []
    order_to_line: dict[str, dict[str, Any]] = {}
    order_to_entitlement: dict[str, dict[str, Any]] = {}
    order_by_key: dict[str, dict[str, Any]] = {}
    party_index_by_key = {party_key: idx for idx, party_key in enumerate(customer_party_keys)}

    product_mix = [
        ("PRD-REPLAY", 70),
        ("PRD-WEEKEND", 20),
        ("PRD-HOSP", 10),
    ]
    weighted_products = []
    for code, weight in product_mix:
        weighted_products.extend([code] * weight)

    order_start = campaign_start + timedelta(days=1)
    for index in range(1, params.order_count + 1):
        order_key = f"ORD-{run_token}-{index:06}"
        line_key = f"ORDLINE-{run_token}-{index:06}"
        payment_key = f"PAY-{run_token}-{index:06}"
        entitlement_key = f"ENT-{run_token}-{index:06}"
        reservation_key = f"RSV-{run_token}-{index:06}"
        command_receipt_key = f"CMD-RCPT-{run_token}-{index:06}"
        order_keys.append(order_key)

        product_code = (["PRD-REPLAY", "PRD-HOSP", "PRD-WEEKEND"][index - 1]
                        if index <= 3 else rng.choice(weighted_products))
        context = contexts[(index - 1) % len(contexts)]
        if rich:
            product_code = (["PRD-REPLAY", "PRD-HOSP", "PRD-WEEKEND"][(index - 1) // 12]
                            if index <= 36 else product_code)
        event_key = context["event"]["eventKey"]
        event_start = _timestamp(context["event"]["eventStartAt"])
        event_end = _timestamp(context["event"]["eventEndAt"])
        replay_start = _timestamp(context["session"]["availableFrom"])
        campaign_key = records["salesforce/campaign.jsonl"][(index - 1) % len(contexts)]["campaignKey"]
        product = rng.choice(context["products"][product_code]) if rich else context["products"][product_code][0]
        product_key = product["productKey"]
        party_idx = (rng.randint(1, params.fan_customer_count) if product_code == "PRD-REPLAY"
                     else rng.randint(params.fan_customer_count + 1, params.customer_count))
        party_key = customer_party_keys[party_idx - 1]
        account_key = customer_account_keys[party_idx - 1]
        if product_code == "PRD-HOSP":
            quantity = 1
        elif product_code == "PRD-WEEKEND":
            quantity = 1 + rng.randint(0, 1)
        else:
            quantity = 1 + rng.randint(0, 3)
        sale_start = replay_start if product_code == "PRD-REPLAY" else order_start
        sale_days = 165 if product_code == "PRD-REPLAY" else 125
        if rich:
            sale_start = _timestamp(product["saleFrom"]) + timedelta(days=1)
            sale_seconds = int((_timestamp(product["saleTo"]) - sale_start).total_seconds()) - 3600
            created_at = sale_start + timedelta(seconds=rng.randint(0, sale_seconds))
        else:
            created_at = sale_start + timedelta(days=rng.randint(0, sale_days), minutes=rng.randint(0, 600))
        price = next(p for p in context["prices"][product_key]
                     if p["effectiveFrom"] <= _iso(created_at) < p["effectiveTo"])
        price_key, unit_price = price["priceKey"], price["amountMinor"]
        line_net = quantity * unit_price
        line_tax = 0
        line_gross = line_net + line_tax
        confirmed_at = created_at + timedelta(minutes=5 + rng.randint(0, 15))
        payment_resolved_at = confirmed_at - timedelta(minutes=1)

        order_record = _build_common(
            canonical_key=order_key,
            source_system="synthetic-operational",
            source_tenant=source_tenant,
            source_entity="CommercialOrder",
            source_key=f"SYN-ORDER-{run_token}-{index:06}",
            source_updated_at=_iso(confirmed_at),
            ingested_at=_iso(confirmed_at + timedelta(seconds=30)),
            schema_version=params.schema_version,
            record_state="confirmed",
            publication_key=publication_key,
        )
        order_record.update(
            {
                "orderKey": order_key,
                "eventKey": event_key,
                "partyKey": party_key,
                "customerAccountSourceKey": account_key,
                "orderState": "confirmed",
                "journey": "fan-purchase" if product_code == "PRD-REPLAY" else "hospitality-b2b",
                "currency": "USD",
                "lineCount": 1,
                "grossMinor": line_gross,
                "taxMinor": line_tax,
                "createdAt": _iso(created_at),
                "confirmedAt": _iso(confirmed_at),
                "idempotencyKey": f"buy-{run_token}-{index:06}",
                "channel": ("mobile", "web", "partner")[index % 3],
                "segment": ("fan", "family", "enthusiast", "vip")[party_idx % 4]
                if product_code == "PRD-REPLAY" else "hospitality-buyer",
            }
        )
        _append_record(records, "operational/commercial_order.jsonl", order_record)
        order_by_key[order_key] = order_record
        order_totals["commercialOrderGrossMinor"] += line_gross

        line_record = _build_common(
            canonical_key=line_key,
            source_system="synthetic-operational",
            source_tenant=source_tenant,
            source_entity="CommercialOrderLine",
            source_key=f"SYN-ORDERLINE-{run_token}-{index:06}",
            source_updated_at=_iso(confirmed_at),
            ingested_at=_iso(confirmed_at + timedelta(seconds=30)),
            schema_version=params.schema_version,
            record_state="open",
            publication_key=publication_key,
        )
        line_record.update(
            {
                "orderLineKey": line_key,
                "orderKey": order_key,
                "productKey": product_key,
                "priceKey": price_key,
                "quantity": quantity,
                "unitPriceMinor": unit_price,
                "netMinor": line_net,
                "taxMinor": line_tax,
                "grossMinor": line_gross,
                "currency": "USD",
                "taxTreatment": "not_applicable",
                "createdAt": _iso(created_at),
            }
        )
        _append_record(records, "operational/commercial_order_line.jsonl", line_record)
        order_to_line[order_key] = line_record

        payment_record = _build_common(
            canonical_key=payment_key,
            source_system="synthetic-operational",
            source_tenant=source_tenant,
            source_entity="PaymentSimulation",
            source_key=f"SYN-PAY-{run_token}-{index:06}",
            source_updated_at=_iso(payment_resolved_at),
            ingested_at=_iso(payment_resolved_at + timedelta(seconds=20)),
            schema_version=params.schema_version,
            record_state="approved",
            publication_key=publication_key,
        )
        payment_record.update(
            {
                "paymentSimulationKey": payment_key,
                "orderKey": order_key,
                "state": "approved",
                "amountMinor": line_gross,
                "currency": "USD",
                "requestedAt": _iso(created_at + timedelta(minutes=1)),
                "resolvedAt": _iso(payment_resolved_at),
                "simulatedOnly": True,
            }
        )
        _append_record(records, "operational/payment_simulation.jsonl", payment_record)
        order_totals["approvedSimulatedPaymentMinor"] += line_gross

        consumed = index % 11 == 0
        access_from = _timestamp(product["accessFrom"])
        access_to = _timestamp(product["accessTo"])
        consumed_at = max(replay_start if product_code == "PRD-WEEKEND" else access_from, confirmed_at) + timedelta(hours=1)
        entitlement_state = "consumed" if consumed else ("expired" if access_to <= as_of else "active")
        entitlement_record = _build_common(
            canonical_key=entitlement_key,
            source_system="synthetic-operational",
            source_tenant=source_tenant,
            source_entity="Entitlement",
            source_key=f"SYN-ENT-{run_token}-{index:06}",
            source_updated_at=_iso(payment_resolved_at),
            ingested_at=_iso(payment_resolved_at + timedelta(seconds=40)),
            schema_version=params.schema_version,
            record_state=entitlement_state,
            publication_key=publication_key,
        )
        entitlement_record.update(
            {
                "entitlementKey": entitlement_key,
                "orderKey": order_key,
                "partyKey": party_key,
                "productKey": product_key,
                "state": entitlement_state,
                "grantedAt": _iso(confirmed_at),
                "validFrom": _iso(access_from),
                "validTo": _iso(access_to),
                "quantityGranted": quantity,
                "consumed": consumed,
                "consumedAt": _iso(consumed_at) if consumed else None,
                "accessScopes": [
                    {"productKey": p["productKey"], "validFrom": p["accessFrom"], "validTo": p["accessTo"]}
                    for p in ([products_by_key[c["componentProductKey"]] for c in bundles_by_key[product_key]]
                              if product_key in bundles_by_key else [product])
                ],
            }
        )
        _append_record(records, "operational/entitlement.jsonl", entitlement_record)
        order_to_entitlement[order_key] = entitlement_record

        zone_demands_for_order = dict(_physical_demand(product_key, products_by_key, bundles_by_key, quantity))
        zone_demands.update(zone_demands_for_order)
        reservation_record = _build_common(
            canonical_key=reservation_key,
            source_system="synthetic-operational",
            source_tenant=source_tenant,
            source_entity="Reservation",
            source_key=f"SYN-RSV-{run_token}-{index:06}",
            source_updated_at=_iso(confirmed_at),
            ingested_at=_iso(confirmed_at + timedelta(seconds=10)),
            schema_version=params.schema_version,
            record_state="confirmed",
            publication_key=publication_key,
        )
        reservation_record.update(
            {
                "reservationKey": reservation_key,
                "eventKey": event_key,
                "orderKey": order_key,
                "orderLineKey": line_key,
                "partyKey": party_key,
                "state": "confirmed",
                "heldAt": _iso(created_at),
                "confirmedAt": _iso(confirmed_at),
                "expiresAt": _iso(created_at + timedelta(hours=1)),
                "capacityScope": "physical" if zone_demands_for_order else "digital-no-physical-allocation",
                "zoneDemands": zone_demands_for_order,
            }
        )
        _append_record(records, "operational/reservation.jsonl", reservation_record)

        command_receipt = _build_common(
            canonical_key=command_receipt_key,
            source_system="synthetic-operational",
            source_tenant=source_tenant,
            source_entity="CommandReceipt",
            source_key=f"SYN-CMD-RCPT-{run_token}-{index:06}",
            source_updated_at=_iso(confirmed_at),
            ingested_at=_iso(confirmed_at + timedelta(seconds=5)),
            schema_version=params.schema_version,
            record_state="succeeded",
            publication_key=publication_key,
        )
        command_receipt.update(
            {
                "commandReceiptKey": command_receipt_key,
                "commandType": "purchase",
                "idempotencyKey": order_record["idempotencyKey"],
                "orderKey": order_key,
                "paymentSimulationKey": payment_key,
                "entitlementKey": entitlement_key,
            }
        )
        _append_record(records, "operational/command_receipt.jsonl", command_receipt)

        touch_record = _build_common(
            canonical_key=f"TOUCH-{run_token}-{index:06}",
            source_system="salesforce",
            source_tenant=source_tenant,
            source_entity="CampaignTouch",
            source_key=f"SF-TOUCH-{run_token}-{index:06}",
            source_updated_at=_iso(created_at),
            ingested_at=_iso(created_at + timedelta(minutes=1)),
            schema_version=params.schema_version,
            record_state="recorded",
            publication_key=publication_key,
        )
        touch_record.update(
            {
                "campaignTouchKey": touch_record["canonicalKey"],
                "campaignKey": campaign_key,
                "partyKey": party_key,
                "orderKey": order_key,
                "state": "recorded",
                "occurredAt": _iso(created_at - timedelta(minutes=1)),
            }
        )
        _append_record(records, "salesforce/campaign_touch.jsonl", touch_record)

        if product_code in {"PRD-HOSP", "PRD-WEEKEND"}:
            opportunity_record = _build_common(
                canonical_key=f"SF-OPP-{run_token}-{index:06}",
                source_system="salesforce",
                source_tenant=source_tenant,
                source_entity="Opportunity",
                source_key=f"SF-OPP-{run_token}-{index:06}",
                source_updated_at=_iso(confirmed_at),
                ingested_at=_iso(confirmed_at + timedelta(minutes=1)),
                schema_version=params.schema_version,
                record_state="closed_won",
                publication_key=publication_key,
            )
            opportunity_record.update(
                {
                    "opportunityKey": opportunity_record["sourceKey"],
                    "accountSourceKey": account_key,
                    "orderKey": order_key,
                    "stageName": "Closed Won",
                    "amountMinor": line_gross,
                    "currency": "USD",
                }
            )
            _append_record(records, "salesforce/opportunity.jsonl", opportunity_record)

    credit_count = max(1, params.order_count // 50)
    pinned_credit_orders = [1, 2, 11, 22] if credit_count >= 4 else [1]
    candidates = [i for i in range(max(pinned_credit_orders) + 1, params.order_count + 1)]
    credit_order_indexes = sorted(pinned_credit_orders + rng.sample(candidates, credit_count - len(pinned_credit_orders)))
    for credit_idx, order_index in enumerate(credit_order_indexes, start=1):
        order_key = f"ORD-{run_token}-{order_index:06}"
        line_record = order_to_line[order_key]
        entitlement_record = order_to_entitlement[order_key]
        case_key = f"CASE-{run_token}-{credit_idx:05}"
        credit_key = f"CREDIT-{run_token}-{credit_idx:05}"
        support_receipt_key = f"CMD-SUPPORT-{run_token}-{credit_idx:05}"
        line_gross = line_record["grossMinor"]
        created_at = datetime.fromisoformat(line_record["sourceUpdatedAt"].replace("Z", "+00:00")) + timedelta(days=1)
        if entitlement_record["consumed"]:
            created_at = max(created_at, datetime.fromisoformat(
                entitlement_record["consumedAt"].replace("Z", "+00:00")) + timedelta(hours=1))
        resolved_at = created_at + timedelta(hours=4)
        full_credit = credit_idx % 2 == 1
        credit_amount = line_gross if full_credit else line_gross // 2
        party_key = entitlement_record["partyKey"]
        party_index = party_index_by_key[party_key]
        contact_key = contact_keys[party_index]

        case_record = _build_common(
            canonical_key=case_key,
            source_system="salesforce",
            source_tenant=source_tenant,
            source_entity="Case",
            source_key=f"SF-CASE-{run_token}-{credit_idx:05}",
            source_updated_at=_iso(resolved_at),
            ingested_at=_iso(resolved_at + timedelta(minutes=5)),
            schema_version=params.schema_version,
            record_state="resolved",
            publication_key=publication_key,
        )
        case_record.update(
            {
                "caseKey": case_key,
                "contactSourceKey": contact_key,
                "contactNullReason": "organization-account-no-person-contact" if contact_key is None else None,
                "accountSourceKey": customer_account_keys[party_index],
                "partyKey": party_key,
                "orderKey": order_key,
                "state": "resolved",
                "reason": "synthetic-support-credit",
                "openedAt": _iso(created_at),
                "resolvedAt": _iso(resolved_at),
                "journey": "complaint-credit",
            }
        )
        _append_record(records, "salesforce/case.jsonl", case_record)

        credit_record = _build_common(
            canonical_key=credit_key,
            source_system="synthetic-operational",
            source_tenant=source_tenant,
            source_entity="ScenarioCredit",
            source_key=f"SYN-CREDIT-{run_token}-{credit_idx:05}",
            source_updated_at=_iso(resolved_at),
            ingested_at=_iso(resolved_at + timedelta(minutes=2)),
            schema_version=params.schema_version,
            record_state="issued",
            publication_key=publication_key,
        )
        credit_record.update(
            {
                "scenarioCreditKey": credit_key,
                "caseKey": case_key,
                "orderKey": order_key,
                "entitlementKey": entitlement_record["entitlementKey"],
                "creditType": ("full" if full_credit else "partial") + "-scenario-credit-not-money-refund",
                "amountMinor": credit_amount,
                "currency": "USD",
                "state": "issued",
                "requestedAt": _iso(created_at),
                "decidedAt": _iso(resolved_at - timedelta(minutes=1)),
                "issuedAt": _iso(resolved_at),
            }
        )
        _append_record(records, "operational/scenario_credit.jsonl", credit_record)
        order_totals["scenarioCreditMinor"] += credit_amount

        if full_credit and not entitlement_record["consumed"]:
            entitlement_record["state"] = "revoked"
            entitlement_record["recordState"] = "revoked"
            entitlement_record["revokedAt"] = _iso(resolved_at)
            entitlement_record["revocationReason"] = "full-credit-unconsumed-access"
            reservation = records["operational/reservation.jsonl"][order_index - 1]
            reservation.update(state="released", recordState="released", releasedAt=_iso(resolved_at))

        support_receipt = _build_common(
            canonical_key=support_receipt_key,
            source_system="synthetic-operational",
            source_tenant=source_tenant,
            source_entity="CommandReceipt",
            source_key=f"SYN-SUPPORT-RCPT-{run_token}-{credit_idx:05}",
            source_updated_at=_iso(resolved_at),
            ingested_at=_iso(resolved_at + timedelta(minutes=1)),
            schema_version=params.schema_version,
            record_state="succeeded",
            publication_key=publication_key,
        )
        support_receipt.update(
            {
                "commandReceiptKey": support_receipt_key,
                "commandType": "support-credit",
                "idempotencyKey": f"support-{run_token}-{credit_idx:05}",
                "caseKey": case_key,
                "scenarioCreditKey": credit_key,
                "orderKey": order_key,
            }
        )
        _append_record(records, "operational/command_receipt.jsonl", support_receipt)

    customer_invoice_total = 0
    customer_credit_total = 0
    supplier_cost_total = 0
    sponsorship_contracted_total = 0
    sponsorship_invoiced_total = 0
    sponsorship_fulfilled_total = 0

    doc_counter = 0
    line_counter = 0

    for order_key in order_keys:
        line_record = order_to_line[order_key]
        order_record = order_by_key[order_key]
        doc_counter += 1
        line_counter += 1
        doc_key = f"ERP-INV-{run_token}-{doc_counter:06}"
        doc_line_key = f"ERPL-{run_token}-{line_counter:06}"
        link_key = f"LINK-{run_token}-ORDER-{doc_counter:06}"
        posted_at = datetime.fromisoformat(order_record["confirmedAt"].replace("Z", "+00:00")) + timedelta(
            hours=6
        )

        doc_record = _build_common(
            canonical_key=doc_key,
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="SAPDocument",
            source_key=f"SAP-DOC-{run_token}-{doc_counter:06}",
            source_updated_at=_iso(posted_at),
            ingested_at=_iso(posted_at + timedelta(minutes=5)),
            schema_version=params.schema_version,
            record_state="posted",
            publication_key=publication_key,
        )
        doc_record.update(
            {
                "erpDocumentKey": doc_key,
                "documentType": "customer_invoice",
                "documentState": "posted",
                "orderKey": order_key,
                "partyKey": order_record["partyKey"],
                "amountMinor": line_record["grossMinor"],
                "currency": "USD",
                "taxTreatment": "not_applicable",
                "erpDocumentLineKey": doc_line_key,
                "documentLinkKey": link_key,
            }
        )
        _append_record(records, "sap_plan_b/sap_document.jsonl", doc_record)

        line_record_sap = _build_common(
            canonical_key=doc_line_key,
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="SAPDocumentLine",
            source_key=f"SAP-LINE-{run_token}-{line_counter:06}",
            source_updated_at=_iso(posted_at),
            ingested_at=_iso(posted_at + timedelta(minutes=5)),
            schema_version=params.schema_version,
            record_state="posted",
            publication_key=publication_key,
        )
        line_record_sap.update(
            {
                "erpDocumentLineKey": doc_line_key,
                "documentSourceKey": doc_record["sourceKey"],
                "erpDocumentKey": doc_key,
                "orderLineKey": line_record["orderLineKey"],
                "lineQuantity": line_record["quantity"],
                "lineNetMinor": line_record["netMinor"],
                "lineTaxMinor": line_record["taxMinor"],
                "lineGrossMinor": line_record["grossMinor"],
                "currency": "USD",
                "taxTreatment": "not_applicable",
            }
        )
        _append_record(records, "sap_plan_b/sap_document_line.jsonl", line_record_sap)
        customer_invoice_total += line_record["grossMinor"]

        doc_link = _build_common(
            canonical_key=link_key,
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="DocumentLink",
            source_key=f"SAP-LINK-{run_token}-{doc_counter:06}",
            source_updated_at=_iso(posted_at),
            ingested_at=_iso(posted_at + timedelta(minutes=5)),
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        doc_link.update(
            {
                "documentLinkKey": link_key,
                "orderKey": order_key,
                "erpDocumentKey": doc_key,
                "erpDocumentLineKey": doc_line_key,
                "linkType": "order-to-document",
            }
        )
        _append_record(records, "sap_plan_b/document_link.jsonl", doc_link)

    for index, credit_record in enumerate(records["operational/scenario_credit.jsonl"], start=1):
        doc_counter += 1
        line_counter += 1
        doc_key = f"ERP-CM-{run_token}-{index:05}"
        doc_line_key = f"ERPL-CM-{run_token}-{index:05}"
        link_key = f"LINK-{run_token}-CREDIT-{index:05}"
        posted_at = datetime.fromisoformat(credit_record["sourceUpdatedAt"].replace("Z", "+00:00")) + timedelta(
            hours=3
        )
        doc_record = _build_common(
            canonical_key=doc_key,
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="SAPDocument",
            source_key=f"SAP-CM-{run_token}-{index:05}",
            source_updated_at=_iso(posted_at),
            ingested_at=_iso(posted_at + timedelta(minutes=4)),
            schema_version=params.schema_version,
            record_state="posted",
            publication_key=publication_key,
        )
        doc_record.update(
            {
                "erpDocumentKey": doc_key,
                "documentType": "customer_credit_memo",
                "documentState": "posted",
                "orderKey": credit_record["orderKey"],
                "partyKey": order_by_key[credit_record["orderKey"]]["partyKey"],
                "amountMinor": credit_record["amountMinor"],
                "currency": "USD",
                "taxTreatment": "not_applicable",
                "erpDocumentLineKey": doc_line_key,
                "documentLinkKey": link_key,
                "scenarioCreditKey": credit_record["scenarioCreditKey"],
            }
        )
        _append_record(records, "sap_plan_b/sap_document.jsonl", doc_record)

        line_record_sap = _build_common(
            canonical_key=doc_line_key,
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="SAPDocumentLine",
            source_key=f"SAP-CM-LINE-{run_token}-{index:05}",
            source_updated_at=_iso(posted_at),
            ingested_at=_iso(posted_at + timedelta(minutes=4)),
            schema_version=params.schema_version,
            record_state="posted",
            publication_key=publication_key,
        )
        line_record_sap.update(
            {
                "erpDocumentLineKey": doc_line_key,
                "documentSourceKey": doc_record["sourceKey"],
                "erpDocumentKey": doc_key,
                "lineQuantity": 1,
                "lineNetMinor": credit_record["amountMinor"],
                "lineTaxMinor": 0,
                "lineGrossMinor": credit_record["amountMinor"],
                "currency": "USD",
                "taxTreatment": "not_applicable",
            }
        )
        _append_record(records, "sap_plan_b/sap_document_line.jsonl", line_record_sap)
        customer_credit_total += credit_record["amountMinor"]

        doc_link = _build_common(
            canonical_key=link_key,
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="DocumentLink",
            source_key=f"SAP-CM-LINK-{run_token}-{index:05}",
            source_updated_at=_iso(posted_at),
            ingested_at=_iso(posted_at + timedelta(minutes=4)),
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        doc_link.update(
            {
                "documentLinkKey": link_key,
                "orderKey": credit_record["orderKey"],
                "scenarioCreditKey": credit_record["scenarioCreditKey"],
                "erpDocumentKey": doc_key,
                "erpDocumentLineKey": doc_line_key,
                "linkType": "credit-to-document",
            }
        )
        _append_record(records, "sap_plan_b/document_link.jsonl", doc_link)

    sponsorship_invoice_docs = max(len(contexts), 3, sponsor_party_count // 2)
    for index in range(1, sponsorship_invoice_docs + 1):
        context = contexts[(index - 1) % len(contexts)]
        event_key = context["event"]["eventKey"]
        event_end = _timestamp(context["event"]["eventEndAt"])
        sponsor_account = sponsor_account_records[(index - 1) % len(sponsor_account_records)]
        agreement_key = f"AGREEMENT-{run_token}-{index:03}"
        commitment_key = f"COMMIT-{run_token}-{index:03}"
        contracted_minor = 250_000 + (index * 25_000)
        invoiced_minor = contracted_minor // 2
        fulfilled_minor = contracted_minor * 7 // 10
        sponsorship_contracted_total += contracted_minor
        sponsorship_invoiced_total += invoiced_minor
        sponsorship_fulfilled_total += fulfilled_minor

        agreement_record = _build_common(
            canonical_key=agreement_key,
            source_system="salesforce",
            source_tenant=source_tenant,
            source_entity="SponsorshipAgreement",
            source_key=f"SF-AGREEMENT-{run_token}-{index:03}",
            source_updated_at=_iso(campaign_start + timedelta(days=40 + index)),
            ingested_at=_iso(campaign_start + timedelta(days=40 + index, minutes=2)),
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        agreement_record.update(
            {
                "agreementKey": agreement_key,
                "sponsorAccountKey": sponsor_account["accountKey"],
                "eventKey": event_key,
                "contractedMinor": contracted_minor,
                "currency": "USD",
                "state": "active",
            }
        )
        _append_record(records, "salesforce/sponsorship_agreement.jsonl", agreement_record)

        commitment_record = _build_common(
            canonical_key=commitment_key,
            source_system="salesforce",
            source_tenant=source_tenant,
            source_entity="SponsorshipCommitment",
            source_key=f"SF-COMMIT-{run_token}-{index:03}",
            source_updated_at=_iso(event_end),
            ingested_at=_iso(event_end + timedelta(minutes=2)),
            schema_version=params.schema_version,
            record_state="in_progress",
            publication_key=publication_key,
        )
        commitment_record.update(
            {
                "commitmentKey": commitment_key,
                "agreementKey": agreement_key,
                "sponsorAccountKey": sponsor_account["accountKey"],
                "invoicedMinor": invoiced_minor,
                "fulfilledMinor": fulfilled_minor,
                "currency": "USD",
                "evidenceReference": f"synthetic://{params.scenario_id}/evidence/{commitment_key}",
                "roiClaimed": False,
                "dueAt": _iso(event_end),
                "evidencedAt": _iso(event_end),
            }
        )
        _append_record(records, "salesforce/sponsorship_commitment.jsonl", commitment_record)

        doc_key = f"ERP-SPONSOR-INV-{run_token}-{index:03}"
        doc_line_key = f"ERPL-SPONSOR-INV-{run_token}-{index:03}"
        link_key = f"LINK-SPONSOR-INV-{run_token}-{index:03}"
        posted_at = campaign_start + timedelta(days=70 + index)
        doc_record = _build_common(
            canonical_key=doc_key,
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="SAPDocument",
            source_key=f"SAP-SPONSOR-INV-{run_token}-{index:03}",
            source_updated_at=_iso(posted_at),
            ingested_at=_iso(posted_at + timedelta(minutes=4)),
            schema_version=params.schema_version,
            record_state="posted",
            publication_key=publication_key,
        )
        doc_record.update(
            {
                "erpDocumentKey": doc_key,
                "documentType": "customer_invoice",
                "documentState": "posted",
                "amountMinor": invoiced_minor,
                "currency": "USD",
                "taxTreatment": "not_applicable",
                "erpDocumentLineKey": doc_line_key,
                "documentLinkKey": link_key,
                "sponsorshipAgreementKey": agreement_key,
                "partyKey": sponsor_account["partyKey"],
            }
        )
        _append_record(records, "sap_plan_b/sap_document.jsonl", doc_record)
        customer_invoice_total += invoiced_minor

        doc_line_record = _build_common(
            canonical_key=doc_line_key,
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="SAPDocumentLine",
            source_key=f"SAP-SPONSOR-LINE-{run_token}-{index:03}",
            source_updated_at=_iso(posted_at),
            ingested_at=_iso(posted_at + timedelta(minutes=4)),
            schema_version=params.schema_version,
            record_state="posted",
            publication_key=publication_key,
        )
        doc_line_record.update(
            {
                "erpDocumentLineKey": doc_line_key,
                "documentSourceKey": doc_record["sourceKey"],
                "erpDocumentKey": doc_key,
                "lineQuantity": 1,
                "lineNetMinor": invoiced_minor,
                "lineTaxMinor": 0,
                "lineGrossMinor": invoiced_minor,
                "currency": "USD",
                "taxTreatment": "not_applicable",
            }
        )
        _append_record(records, "sap_plan_b/sap_document_line.jsonl", doc_line_record)

        link_record = _build_common(
            canonical_key=link_key,
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="DocumentLink",
            source_key=f"SAP-SPONSOR-LINK-{run_token}-{index:03}",
            source_updated_at=_iso(posted_at),
            ingested_at=_iso(posted_at + timedelta(minutes=4)),
            schema_version=params.schema_version,
            record_state="linked",
            publication_key=publication_key,
        )
        link_record.update(
            {
                "documentLinkKey": link_key,
                "sponsorshipAgreementKey": agreement_key,
                "erpDocumentKey": doc_key,
                "erpDocumentLineKey": doc_line_key,
                "linkType": "sponsorship-invoice",
            }
        )
        _append_record(records, "sap_plan_b/document_link.jsonl", link_record)

    supplier_sources = [record["sourceKey"] for record in records["sap_plan_b/supplier.jsonl"]]
    cost_center_sources = [record["sourceKey"] for record in records["sap_plan_b/cost_center.jsonl"]]
    supplier_cost_doc_count = max(len(contexts), 6, params.order_count // 4_000)
    for index in range(1, supplier_cost_doc_count + 1):
        supplier_source = supplier_sources[(index - 1) % len(supplier_sources)]
        cost_center_source = cost_center_sources[(index - 1) % len(cost_center_sources)]
        supplier_cost_key = f"COST-{run_token}-{index:05}"
        allocation_key = f"ALLOC-{run_token}-{index:05}"
        amount_minor = 8_000 + (index * 700)
        supplier_cost_total += amount_minor
        posted_at = campaign_start + timedelta(days=120 + index)
        doc_key = f"ERP-SUPPLIER-{run_token}-{index:05}"
        doc_line_key = f"ERPL-SUPPLIER-{run_token}-{index:05}"
        link_key = f"LINK-SUPPLIER-{run_token}-{index:05}"

        doc_record = _build_common(
            canonical_key=doc_key,
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="SAPDocument",
            source_key=f"SAP-SUPPLIER-DOC-{run_token}-{index:05}",
            source_updated_at=_iso(posted_at),
            ingested_at=_iso(posted_at + timedelta(minutes=2)),
            schema_version=params.schema_version,
            record_state="posted",
            publication_key=publication_key,
        )
        doc_record.update(
            {
                "erpDocumentKey": doc_key,
                "documentType": "supplier_invoice",
                "documentState": "posted",
                "amountMinor": amount_minor,
                "currency": "USD",
                "taxTreatment": "not_applicable",
                "erpDocumentLineKey": doc_line_key,
                "documentLinkKey": link_key,
            }
        )
        _append_record(records, "sap_plan_b/sap_document.jsonl", doc_record)

        doc_line_record = _build_common(
            canonical_key=doc_line_key,
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="SAPDocumentLine",
            source_key=f"SAP-SUPPLIER-LINE-{run_token}-{index:05}",
            source_updated_at=_iso(posted_at),
            ingested_at=_iso(posted_at + timedelta(minutes=2)),
            schema_version=params.schema_version,
            record_state="posted",
            publication_key=publication_key,
        )
        doc_line_record.update(
            {
                "erpDocumentLineKey": doc_line_key,
                "documentSourceKey": doc_record["sourceKey"],
                "erpDocumentKey": doc_key,
                "lineQuantity": 1,
                "lineNetMinor": amount_minor,
                "lineTaxMinor": 0,
                "lineGrossMinor": amount_minor,
                "currency": "USD",
                "taxTreatment": "not_applicable",
            }
        )
        _append_record(records, "sap_plan_b/sap_document_line.jsonl", doc_line_record)

        supplier_cost_record = _build_common(
            canonical_key=supplier_cost_key,
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="SupplierCost",
            source_key=f"SAP-SUPPLIER-COST-{run_token}-{index:05}",
            source_updated_at=_iso(posted_at),
            ingested_at=_iso(posted_at + timedelta(minutes=2)),
            schema_version=params.schema_version,
            record_state="allocated",
            publication_key=publication_key,
        )
        supplier_cost_record.update(
            {
                "supplierCostKey": supplier_cost_key,
                "supplierSourceKey": supplier_source,
                "costCenterSourceKey": cost_center_source,
                "documentSourceKey": doc_record["sourceKey"],
                "documentLineSourceKey": doc_line_record["sourceKey"],
                "amountMinor": amount_minor,
                "currency": "USD",
            }
        )
        _append_record(records, "sap_plan_b/supplier_cost.jsonl", supplier_cost_record)

        allocation_record = _build_common(
            canonical_key=allocation_key,
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="SAPCostAllocation",
            source_key=f"SAP-ALLOC-{run_token}-{index:05}",
            source_updated_at=_iso(posted_at),
            ingested_at=_iso(posted_at + timedelta(minutes=2)),
            schema_version=params.schema_version,
            record_state="posted",
            publication_key=publication_key,
        )
        allocation_record.update(
            {
                "costAllocationKey": allocation_key,
                "supplierCostSourceKey": supplier_cost_record["sourceKey"],
                "supplierCostKey": supplier_cost_key,
                "supplierSourceKey": supplier_source,
                "costCenterSourceKey": cost_center_source,
                "amountMinor": amount_minor,
                "currency": "USD",
                "allocationTarget": "event-operation"
                if index % 2 == 0
                else "sponsorship-delivery",
            }
        )
        _append_record(records, "sap_plan_b/sap_cost_allocation.jsonl", allocation_record)

        link_record = _build_common(
            canonical_key=link_key,
            source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant,
            source_entity="DocumentLink",
            source_key=f"SAP-SUPPLIER-LINK-{run_token}-{index:05}",
            source_updated_at=_iso(posted_at),
            ingested_at=_iso(posted_at + timedelta(minutes=2)),
            schema_version=params.schema_version,
            record_state="active",
            publication_key=publication_key,
        )
        link_record.update(
            {
                "documentLinkKey": link_key,
                "supplierCostKey": supplier_cost_key,
                "erpDocumentKey": doc_key,
                "erpDocumentLineKey": doc_line_key,
                "linkType": "supplier-cost-document",
            }
        )
        _append_record(records, "sap_plan_b/document_link.jsonl", link_record)

    # Now that demands are known, set scaled zone capacities.
    zone_capacity_map = {
        z["zoneKey"]: zone_demands[z["zoneKey"]] + (
            max(1_000, params.order_count // 10) if z["zoneKey"].startswith("ZONE-NORTH-")
            else max(500, params.order_count // (20 * len(contexts))))
        for z in records["oracle/oracle_circuit_zone.jsonl"]
    }
    for zone_record in records["oracle/oracle_circuit_zone.jsonl"]:
        zone_record["capacity"] = zone_capacity_map[zone_record["zoneKey"]]

    parties = records["operational/party.jsonl"]
    billing_partners = {}
    for index, party in enumerate(parties, start=1):
        original_entity, original_key = party["sourceEntity"], party["sourceKey"]
        party.update(
            sourceSystem="canonical-projection",
            sourceEntity="SalesforcePartyProjection",
            sourceKey=f"PROJECTION-PARTY-{run_token}-{index:05}",
            projectionKind="canonical-party-crosswalk",
            businessOwner="Salesforce",
            sourceReference={
                "sourceSystem": "salesforce", "sourceTenant": source_tenant,
                "sourceEntity": original_entity, "sourceKey": original_key,
            },
        )
        bp_key = f"SAP-BP-CUSTOMER-{run_token}-{index:05}"
        billing_partners[party["partyKey"]] = bp_key
        bp = _build_common(
            canonical_key=bp_key, source_system="sap-plan-b-synthetic",
            source_tenant=source_tenant, source_entity="BusinessPartner", source_key=bp_key,
            source_updated_at=_iso(master_at), ingested_at=_iso(master_at + timedelta(minutes=6)),
            schema_version=params.schema_version, record_state="active", publication_key=publication_key,
        )
        bp.update(bpRole="Customer", partyKey=party["partyKey"], partyCrosswalk={
            "canonicalEntity": "Party", "canonicalKey": party["partyKey"],
            "sourceReference": copy.deepcopy(party["sourceReference"]),
        })
        _append_record(records, "sap_plan_b/business_partner.jsonl", bp)

    suppliers_by_key = {r["sourceKey"]: r for r in records["sap_plan_b/supplier.jsonl"]}
    costs_by_document = {r["documentSourceKey"]: r for r in records["sap_plan_b/supplier_cost.jsonl"]}
    for doc in records["sap_plan_b/sap_document.jsonl"]:
        doc["postedAt"] = doc["sourceUpdatedAt"]
        doc["documentDate"] = doc["postedAt"]
        if doc["documentType"] == "supplier_invoice":
            supplier = suppliers_by_key[costs_by_document[doc["sourceKey"]]["supplierSourceKey"]]
            doc.update(partnerSourceKey=supplier["bpSourceKey"], supplierSourceKey=supplier["sourceKey"])
        else:
            doc["partnerSourceKey"] = billing_partners[doc["partyKey"]]
    for line in records["sap_plan_b/sap_document_line.jsonl"]:
        line.update(postedAt=line["sourceUpdatedAt"], unitPriceMinor=line["lineNetMinor"] // line["lineQuantity"])
    for link in records["sap_plan_b/document_link.jsonl"]:
        link.update(recordState="linked", linkedAt=link["sourceUpdatedAt"])
    for entitlement in records["operational/entitlement.jsonl"]:
        last_change = (entitlement.get("revokedAt") or entitlement.get("consumedAt")
                       or (entitlement["validTo"] if entitlement["state"] == "expired" else entitlement["grantedAt"]))
        entitlement.update(sourceUpdatedAt=last_change,
                           ingestedAt=_iso(datetime.fromisoformat(last_change.replace("Z", "+00:00"))
                                           + timedelta(minutes=1)))
    for reservation in records["operational/reservation.jsonl"]:
        if reservation["state"] == "released":
            reservation.update(sourceUpdatedAt=reservation["releasedAt"], ingestedAt=reservation["releasedAt"])
    for agreement in records["salesforce/sponsorship_agreement.jsonl"]:
        agreement.update(signedAt=agreement["sourceUpdatedAt"], validFrom=agreement["sourceUpdatedAt"],
                         validTo=_iso(price_end), journey="sponsorship")
    physical_orders = [o for o in records["operational/commercial_order.jsonl"] if o["journey"] == "hospitality-b2b"]
    agreements = records["salesforce/sponsorship_agreement.jsonl"]
    costs = records["sap_plan_b/supplier_cost.jsonl"]
    for index, allocation in enumerate(records["sap_plan_b/sap_cost_allocation.jsonl"]):
        event_key = contexts[index % len(contexts)]["event"]["eventKey"]
        allocation.update(eventKey=event_key, allocatedAt=allocation["sourceUpdatedAt"], postedAt=allocation["sourceUpdatedAt"])
        if allocation["allocationTarget"] == "sponsorship-delivery":
            matching_agreements = [a for a in agreements if a["eventKey"] == event_key]
            allocation["sponsorshipAgreementKey"] = matching_agreements[index % len(matching_agreements)]["agreementKey"]
        elif physical_orders:
            matching = [o for o in physical_orders if o["eventKey"] == event_key]
            allocation["partyKey"] = matching[index % len(matching)]["partyKey"]
        costs[index].update(eventKey=event_key, incurredAt=costs[index]["sourceUpdatedAt"])

    if rich:
        agreements_by_key = {r["agreementKey"]: r for r in agreements}
        for path in (
            "operational/commercial_order_line.jsonl", "operational/payment_simulation.jsonl",
            "operational/reservation.jsonl", "operational/entitlement.jsonl",
            "operational/scenario_credit.jsonl", "operational/command_receipt.jsonl",
            "salesforce/campaign_touch.jsonl", "salesforce/opportunity.jsonl", "salesforce/case.jsonl",
        ):
            for row in records[path]:
                row["eventKey"] = order_by_key[row["orderKey"]]["eventKey"]
        for row in records["salesforce/sponsorship_commitment.jsonl"]:
            row["eventKey"] = agreements_by_key[row["agreementKey"]]["eventKey"]
        for row in records["sap_plan_b/sap_document.jsonl"]:
            if "orderKey" in row:
                row["eventKey"] = order_by_key[row["orderKey"]]["eventKey"]
            elif "sponsorshipAgreementKey" in row:
                row["eventKey"] = agreements_by_key[row["sponsorshipAgreementKey"]]["eventKey"]
            else:
                row["eventKey"] = costs_by_document[row["sourceKey"]]["eventKey"]
        docs_by_key = {r["erpDocumentKey"]: r for r in records["sap_plan_b/sap_document.jsonl"]}
        for path in ("sap_plan_b/sap_document_line.jsonl", "sap_plan_b/document_link.jsonl"):
            for row in records[path]:
                row["eventKey"] = docs_by_key[row["erpDocumentKey"]]["eventKey"]

    for path, (system, entity, canonical_entity, key_field) in FILE_SPECS.items():
        for row in records.setdefault(path, []):
            mapped_entity = ("SponsorAccount" if path == "salesforce/account.jsonl" and row["segment"] == "sponsor"
                             else canonical_entity)
            row.update(
                scenarioId=params.scenario_id, scenarioVersion=params.scenario_version,
                datasetId=params.dataset_id, runVersion=params.run_version, seed=params.seed,
                namespace=params.namespace, schemaVersion=params.schema_version,
                sapPlan="B", asOf=_iso(as_of), publishedAt=_iso(source_published_at),
                syntheticProvenance="synthetic-only", sourceMappingQualification="illustrative-logical-unqualified",
                canonicalEntity=mapped_entity,
            )
            if mapped_entity is None:
                row.update(canonicalKey=None, canonicalNullReason=NULL_MAPPING_REASON, mappingStatus=NULL_MAPPING_REASON)
            else:
                row["canonicalKey"] = row[key_field]

    counts_by_source_entity = _entity_counts(records)

    reconciliation = {
        "currency": "USD",
        "commercialOrderGrossMinor": order_totals["commercialOrderGrossMinor"],
        "approvedSimulatedPaymentMinor": order_totals["approvedSimulatedPaymentMinor"],
        "scenarioCreditMinor": order_totals["scenarioCreditMinor"],
        "commercialOrderNetAfterCreditMinor": order_totals["commercialOrderGrossMinor"]
        - order_totals["scenarioCreditMinor"],
        "postedCustomerInvoiceMinor": customer_invoice_total,
        "postedCustomerCreditMemoMinor": customer_credit_total,
        "supplierCostMinor": supplier_cost_total,
        "allocatedCostMinor": supplier_cost_total,
        "postedOrderInvoiceMinor": order_totals["commercialOrderGrossMinor"],
        "sponsorshipContractedMinor": sponsorship_contracted_total,
        "sponsorshipInvoicedMinor": sponsorship_invoiced_total,
        "sponsorshipFulfilledMinor": sponsorship_fulfilled_total,
    }

    report = {
        "manifestVersion": "1.0.0",
        "generator": "scripts.volume_fixture",
        "schemaVersion": params.schema_version,
        "scenarioId": params.scenario_id,
        "scenarioVersion": params.scenario_version,
        "datasetId": params.dataset_id,
        "runVersion": params.run_version,
        "namespace": params.namespace,
        "seed": params.seed,
        "publicationKey": publication_key,
        "dataOrigin": "synthetic-only",
        "provenanceLabel": "SYNTHETIC SCENARIO - NOT CONNECTED SOURCE DATA",
        "sapPlan": "B",
        "asOf": _iso(as_of),
        "publishedAt": _iso(source_published_at),
        "sourceTenant": source_tenant,
        "keyToken": run_token,
        "sourceMappingQualification": "illustrative-logical-unqualified",
        "parameters": params.as_dict(),
        "populationCounts": {
            "customerParties": params.customer_count,
            "fanCustomerParties": params.fan_customer_count,
            "businessCustomerParties": params.business_customer_count,
            "sponsorParties": sponsor_party_count,
            "vendorMasters": vendor_master_count,
            "totalParties": len(records["operational/party.jsonl"]),
        },
        "countsBySourceEntity": dict(counts_by_source_entity),
        "reconciliation": reconciliation,
        "financialTotalsBySourceCurrency": _financial_totals(records),
        "capacity": {
            "zoneDemands": {key: zone_demands[key] for key in zone_capacity_map},
            "zoneCapacities": zone_capacity_map,
            "bundleComponentRule": {
                key: [{"componentProductKey": c["componentProductKey"], "quantity": c["quantity"]} for c in components]
                for key, components in bundles_by_key.items()
            },
        },
        "boundaries": {
            "supported": [
                "Synthetic Oracle/Salesforce/SAP Plan B source-shaped records with provenance.",
                "Separate synthetic operational command boundary for orders, payments, reservations, entitlements, and support credits.",
                "Twelve fictional events with synthetic replay sessions." if rich
                else "One fictional event and one synthetic replay session.",
            ],
            "unsupported": [
                "No live product sales, no qualified live race source, and no real customer data.",
                "No inferred consent, ROI, settlement, refund, or accounting revenue recognition.",
                "No claim of connected Oracle/Salesforce/SAP systems; SAP Plan B remains synthetic.",
            ],
        },
        "sourceOnlyMasterMappingRule": "Records with no canonical equivalent use canonicalEntity=null, canonicalKey=null, and canonicalNullReason='source-reference-only-no-canonical-entity'.",
        "generatedAt": "deterministic-not-wallclock",
        "files": [],
    }

    if rich:
        report["financialTotalsByEventSourceCurrency"] = _event_financial_totals(records)
    return records, report


def _materialize_files(
    records: dict[str, list[dict[str, Any]]], report: dict[str, Any]
) -> tuple[dict[str, bytes], dict[str, Any]]:
    file_bytes: dict[str, bytes] = {}
    files_report = []
    for relative_path in sorted(records):
        lines = [_json_line(record) for record in records[relative_path]]
        payload = ("\n".join(lines) + "\n").encode("utf-8")
        file_bytes[relative_path] = payload
        files_report.append(
            {
                "path": relative_path,
                "recordCount": len(lines),
                "sha256": _sha256_bytes(payload),
                "sizeBytes": len(payload),
            }
        )
    report_copy = copy.deepcopy(report)
    report_copy["files"] = files_report
    report_copy["datasetDigestSha256"] = _dataset_digest(report_copy)
    report_bytes = json.dumps(report_copy, indent=2, sort_keys=True).encode("utf-8")
    file_bytes["manifest.json"] = report_bytes + b"\n"
    return file_bytes, report_copy


def _write_export(output_path: Path, files: dict[str, bytes]) -> None:
    output_path.mkdir(parents=True, exist_ok=True)
    for relative_path, payload in files.items():
        destination = output_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)


def _verify_existing_noop(output_path: Path, expected_files: dict[str, bytes]) -> None:
    missing = []
    mismatched = []
    for relative_path, payload in expected_files.items():
        candidate = output_path / relative_path
        if not candidate.exists():
            missing.append(relative_path)
            continue
        current = candidate.read_bytes()
        if current != payload:
            mismatched.append(relative_path)
    unexpected = []
    for candidate in output_path.rglob("*"):
        if candidate.is_dir():
            continue
        relative = candidate.relative_to(output_path).as_posix()
        if relative not in expected_files:
            unexpected.append(relative)
    if missing or mismatched or unexpected:
        raise FileExistsError(
            "Existing output does not match deterministic no-op verification. "
            f"missing={missing}, mismatched={mismatched}, unexpected={unexpected}"
        )


def generate_dataset(params: GenerationParameters) -> dict[str, Any]:
    records, report = build_export_records(params)
    files, hydrated_report = _materialize_files(records, report)

    output_path = params.output_path
    if output_path.exists():
        has_files = any(output_path.iterdir())
        if has_files:
            if params.if_exists == "verify-noop":
                _verify_existing_noop(output_path, files)
                return {"status": "no-op-verified", "manifestPath": str(output_path / "manifest.json")}
            raise FileExistsError(
                f"Output path already exists and is not empty: {output_path}. "
                "Refusing to overwrite existing artifacts."
            )
    _write_export(output_path, files)
    return {"status": "generated", "manifestPath": str(output_path / "manifest.json"), "report": hydrated_report}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid JSONL at {path} line {line_number}: {exc}") from exc
    return records


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _load_export(output_path: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    manifest_path = output_path / "manifest.json"
    if not manifest_path.exists():
        raise ValidationError(f"manifest.json not found at {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _expect(isinstance(manifest, dict), "Manifest must be an object.")
    paths = [item["path"] for item in manifest["files"]]
    _expect(paths == sorted(FILE_SPECS), "Manifest must list the exact supported file set once, in sorted order.")
    actual_files = set()
    for path in output_path.rglob("*"):
        _expect(not path.is_symlink(), "Export must not contain symlinks.")
        if path.is_file():
            actual_files.add(path.relative_to(output_path).as_posix())
    _expect(actual_files == set(FILE_SPECS) | {"manifest.json"}, "Missing or unlisted export files.")
    loaded: dict[str, list[dict[str, Any]]] = {}
    for item in manifest["files"]:
        file_path = output_path / item["path"]
        _expect(file_path.exists(), f"Expected file missing: {item['path']}")
        content = file_path.read_bytes()
        _expect(type(item["sizeBytes"]) is int and len(content) == item["sizeBytes"],
                f"Byte size mismatch for {item['path']}")
        _expect(
            _sha256_bytes(content) == item["sha256"],
            f"Digest mismatch for {item['path']}",
        )
        loaded[item["path"]] = _load_jsonl(file_path)
        _expect(type(item["recordCount"]) is int and len(loaded[item["path"]]) == item["recordCount"],
                f"Count mismatch for {item['path']}")
    _expect(_dataset_digest(manifest) == manifest["datasetDigestSha256"], "Aggregate dataset digest mismatch.")
    return manifest, loaded


def _timestamp(value: Any) -> datetime:
    _expect(isinstance(value, str) and value.endswith("Z"), f"Expected UTC RFC 3339 timestamp: {value!r}")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _physical_demand(product_key: str, products: dict, bundles: dict, quantity: int,
                     ancestors: frozenset = frozenset()) -> Counter:
    _expect(product_key in products and product_key not in ancestors, "Unknown or cyclic bundle product.")
    if product_key in bundles:
        _expect(not products[product_key]["capacityPerUnit"], "Bundle cannot also allocate its components' seats.")
        demand = Counter()
        for component in bundles[product_key]:
            demand.update(_physical_demand(component["componentProductKey"], products, bundles,
                                           quantity * component["quantity"], ancestors | {product_key}))
        return demand
    return Counter({zone: quantity * units for zone, units in products[product_key]["capacityPerUnit"].items()})


def _validate_event_links(data: dict, event_keys: set[str]) -> None:
    shared_paths = {
        "operational/party.jsonl", "salesforce/account.jsonl", "salesforce/contact.jsonl",
        "salesforce/consent.jsonl", "sap_plan_b/business_partner.jsonl",
        "sap_plan_b/supplier.jsonl", "sap_plan_b/cost_center.jsonl",
    }
    indexes = {
        key_field: {r[key_field]: r["eventKey"] for r in data[path]}
        for path, (_, _, _, key_field) in FILE_SPECS.items() if path not in shared_paths
    }
    indexes["sponsorshipAgreementKey"] = indexes["agreementKey"]
    indexes["bundleProductKey"] = indexes["productKey"]
    indexes["componentProductKey"] = indexes["productKey"]
    for path, rows in data.items():
        if path in shared_paths:
            continue
        for row in rows:
            _expect(row.get("eventKey") in event_keys, f"{path}: missing event scope.")
            for field, targets in indexes.items():
                if field in row:
                    _expect(row[field] in targets and targets[row[field]] == row["eventKey"],
                            f"{path}: {field} crosses event or is missing.")
    for path in (
        "operational/commercial_order.jsonl", "salesforce/campaign.jsonl",
        "salesforce/sponsorship_agreement.jsonl", "sap_plan_b/supplier_cost.jsonl",
    ):
        _expect({r["eventKey"] for r in data[path]} == event_keys, f"{path}: incomplete event coverage.")


def _validate_semantics(manifest: dict, data: dict, output_path: Path) -> None:
    p = manifest["parameters"]
    params = GenerationParameters(
        output_path=output_path, customer_count=p["customerCount"], order_count=p["orderCount"],
        seed=p["seed"], run_version=p["runVersion"], schema_version=p["schemaVersion"],
        scenario_id=p["scenarioId"], scenario_version=p["scenarioVersion"], dataset_id=p["datasetId"],
        catalog_profile=p.get("catalogProfile", LEGACY_PROFILE),
    )
    params.validate()
    _expect(p == params.as_dict(), "Unsupported or missing generation parameters.")
    scope = {
        "scenarioId": params.scenario_id, "scenarioVersion": params.scenario_version,
        "datasetId": params.dataset_id, "runVersion": params.run_version, "seed": params.seed,
        "schemaVersion": params.schema_version, "namespace": params.namespace,
        "sourceTenant": params.source_tenant, "sapPlan": "B", "dataOrigin": "synthetic-only",
        "publicationKey": f"{DEFAULT_PUBLICATION_KEY}-{params.key_token}",
        "asOf": "2030-12-20T00:00:00Z", "publishedAt": "2030-12-31T23:59:00Z",
        "sourceMappingQualification": "illustrative-logical-unqualified",
    }
    for field, value in scope.items():
        _expect(manifest.get(field) == value, f"Manifest scope mismatch: {field}")
    _expect(manifest["keyToken"] == params.key_token, "Manifest key namespace mismatch.")
    _expect(manifest["manifestVersion"] == "1.0.0" and manifest["generator"] == "scripts.volume_fixture",
            "Unsupported manifest format.")
    _expect(manifest["provenanceLabel"] == "SYNTHETIC SCENARIO - NOT CONNECTED SOURCE DATA", "Missing synthetic disclosure.")
    _expect(manifest["countsBySourceEntity"] == _entity_counts(data), "Source entity counts mismatch.")
    contracts = json.loads((Path(__file__).resolve().parents[1] / "contracts" / "canonical-contracts.json").read_text(encoding="utf-8"))
    states = {item["name"]: set(item["states"]) for item in contracts["entities"]}
    canonical_keys, source_identities = set(), set()
    sources = {}

    def check_keys(value: Any) -> None:
        if isinstance(value, dict):
            for field, item in value.items():
                if (field.endswith("Key") or field == "idempotencyKey") and item is not None:
                    _expect(isinstance(item, str) and params.key_token in item, f"Key outside namespace: {field}")
                if field.endswith("Minor"):
                    _expect(type(item) is int and item >= 0, f"Money must be nonnegative integer minor units: {field}")
                if field in {"quantity", "lineQuantity", "quantityGranted", "lineCount"}:
                    _expect(type(item) is int and item > 0, f"Quantity must be a positive integer: {field}")
                check_keys(item)
        elif isinstance(value, list):
            for item in value:
                check_keys(item)

    for path, rows in data.items():
        system, entity, canonical_entity, key_field = FILE_SPECS[path]
        row_keys = set()
        for row in rows:
            _expect(isinstance(row, dict), f"{path}: record must be an object.")
            for field, value in scope.items():
                _expect(row.get(field) == value, f"{path}: scope mismatch: {field}")
            _expect(row.get("syntheticProvenance") == "synthetic-only", "Missing synthetic provenance.")
            _expect(row["sourceSystem"] == system and row["sourceEntity"] == entity, f"{path}: wrong source scope/entity.")
            identity = tuple(row[k] for k in ("sourceSystem", "sourceTenant", "sourceEntity", "sourceKey"))
            _expect(identity not in source_identities, f"Duplicate source identity: {identity}")
            source_identities.add(identity)
            sources[identity] = row
            _expect(row[key_field] not in row_keys, f"Duplicate row key in {path}")
            row_keys.add(row[key_field])
            mapped_entity = ("SponsorAccount" if path == "salesforce/account.jsonl" and row["segment"] == "sponsor"
                             else canonical_entity)
            _expect(row.get("canonicalEntity") == mapped_entity, f"{path}: wrong canonical entity.")
            if mapped_entity is None:
                _expect(row["canonicalKey"] is None and row.get("canonicalNullReason") == NULL_MAPPING_REASON
                        and row.get("mappingStatus") == NULL_MAPPING_REASON, "Source-only master/reference must have explicit null mapping.")
                allowed = {"succeeded"} if entity == "CommandReceipt" else ({"closed_won"} if entity == "Opportunity" else {"active"})
            else:
                _expect(row["canonicalKey"] == row[key_field], f"{path}: inconsistent canonical key.")
                _expect(row["canonicalKey"] not in canonical_keys, "Duplicate canonical key.")
                canonical_keys.add(row["canonicalKey"])
                allowed = states[mapped_entity]
            _expect(row["recordState"] in allowed, f"{path}: invalid contract state.")
            if "state" in row:
                _expect(row["state"] == row["recordState"], f"{path}: inconsistent state fields.")
            _expect(_timestamp(row["sourceUpdatedAt"]) <= _timestamp(row["ingestedAt"])
                    <= _timestamp(row["publishedAt"]), f"{path}: incoherent source/ingestion/publication time.")
            _expect(_timestamp(row["sourceUpdatedAt"]) <= _timestamp(row["asOf"]), "Source fact beyond asOf.")
            check_keys(row)
            for field, value in row.items():
                if (field.endswith("At") or field.endswith("From") or field.endswith("To")) and value is not None:
                    instant = _timestamp(value)
                    if field.endswith("At") and field != "publishedAt":
                        _expect(instant <= _timestamp(row["asOf"]), f"Future visible fact: {field}")
                    if field in {"createdAt", "requestedAt", "resolvedAt", "confirmedAt", "grantedAt", "consumedAt",
                                 "revokedAt", "releasedAt", "openedAt", "decidedAt", "issuedAt", "occurredAt",
                                 "signedAt", "evidencedAt", "linkedAt", "postedAt", "allocatedAt", "incurredAt"}:
                        _expect(instant <= _timestamp(row["sourceUpdatedAt"]), f"Fact after source update: {field}")
            if row.get("email") is not None:
                _expect(isinstance(row["email"], str) and row["email"].endswith("@example.test"),
                        "Only synthetic example.test emails are permitted.")
            if "currency" in row:
                _expect(row["currency"] == "USD", "Unsupported currency; no implicit conversion.")
            if "taxTreatment" in row:
                _expect(row["taxTreatment"] == "not_applicable", "This fixture models explicit not_applicable tax only.")

    def index(path: str, field: str) -> dict:
        return {r[field]: r for r in data[path]}

    def reference(ref: dict, entity: str | None = None) -> dict:
        _expect(set(ref) == {"sourceSystem", "sourceTenant", "sourceEntity", "sourceKey"}, "Malformed typed source reference.")
        identity = tuple(ref[k] for k in ("sourceSystem", "sourceTenant", "sourceEntity", "sourceKey"))
        _expect(identity in sources, "Missing typed source reference.")
        if entity:
            _expect(ref["sourceEntity"] == entity, "Wrong source reference entity.")
        return sources[identity]

    parties = index("operational/party.jsonl", "partyKey")
    accounts = index("salesforce/account.jsonl", "sourceKey")
    contacts = index("salesforce/contact.jsonl", "sourceKey")
    orders = index("operational/commercial_order.jsonl", "orderKey")
    lines = index("operational/commercial_order_line.jsonl", "orderLineKey")
    products = index("oracle/oracle_catalog_product.jsonl", "productKey")
    prices = index("oracle/oracle_price_list_entry.jsonl", "priceKey")
    zones = index("oracle/oracle_circuit_zone.jsonl", "zoneKey")
    events = data["oracle/oracle_event.jsonl"]
    sessions = data["operational/replay_session.jsonl"]
    rich = params.catalog_profile == DEFAULT_CATALOG_PROFILE
    event_count = 12 if rich else 1
    _expect(len(events) == len(sessions) == event_count, "Event/replay session population mismatch.")
    events_by_key = {r["eventKey"]: r for r in events}
    sessions_by_event = {r["eventKey"]: r for r in sessions}
    _expect(set(sessions_by_event) == set(events_by_key), "Replay event coverage mismatch.")
    for event in events:
        session = sessions_by_event[event["eventKey"]]
        _expect(event["eventStartAt"] < event["eventEndAt"] <= manifest["asOf"] and event["recordState"] == "completed",
                "Invalid completed event interval/state.")
        _expect(session["playbackMode"] == "synthetic-replay"
                and session["sessionStartAt"] == event["eventStartAt"] and session["sessionEndAt"] == event["eventEndAt"]
                and event["eventEndAt"] < session["availableFrom"] <= manifest["asOf"] < session["availableTo"],
                "Invalid replay interval/mode.")
    for rows in data.values():
        for row in rows:
            if "eventKey" in row:
                _expect(row["eventKey"] in events_by_key, "Foreign event reference.")
    if rich:
        _validate_event_links(data, set(events_by_key))
    customer_parties = [r for r in parties.values() if r["partyRole"] == "customer"]
    fan_customers = [r for r in customer_parties if r["customerType"] == "fan"]
    business_customers = [r for r in customer_parties if r["customerType"] == "business"]
    sponsors = [r for r in parties.values() if r["partyRole"] == "sponsor"]
    vendor_count = max(6, params.order_count // 5000)
    expected_population = {
        "customerParties": params.customer_count, "sponsorParties": max(8, params.customer_count // 2000),
        "fanCustomerParties": params.fan_customer_count, "businessCustomerParties": params.business_customer_count,
        "vendorMasters": vendor_count, "totalParties": params.customer_count + max(8, params.customer_count // 2000),
    }
    _expect(manifest["populationCounts"] == expected_population, "Population counts mismatch.")
    _expect(len(orders) == params.order_count, "Actual order population differs from parameters.")
    _expect(all(r["email"] == f"customer.{i:05}@example.test" for i, r in enumerate(fan_customers, 1)),
            "Only fictional example.test customer identities are supported.")
    _expect(len(customer_parties) == expected_population["customerParties"]
            and len(fan_customers) == expected_population["fanCustomerParties"]
            and len(business_customers) == expected_population["businessCustomerParties"]
            and len(sponsors) == expected_population["sponsorParties"]
            and len(accounts) == len(parties) and len(contacts) == len(fan_customers), "Actual party/account/contact populations mismatch.")
    for party in parties.values():
        _expect((party["partyRole"], party["customerType"], party["partyType"]) in {
            ("customer", "fan", "person"), ("customer", "business", "organization"), ("sponsor", None, "organization"),
        }, "Invalid customer/sponsor Party classification.")
        if party["partyType"] == "organization":
            _expect(party["email"] is None, "Organization must not invent a person contact.")
        _expect(party["projectionKind"] == "canonical-party-crosswalk" and party["businessOwner"] == "Salesforce",
                "Party projection cannot claim operational ownership.")
        origin = reference(party["sourceReference"], "Contact" if party["partyType"] == "person" else "Account")
        _expect(origin["partyKey"] == party["partyKey"] and origin["displayName"] == party["displayName"], "Party crosswalk mismatch.")
        _expect(party["sourceUpdatedAt"] == origin["sourceUpdatedAt"], "Projection timestamp differs from source.")
        if party["partyRole"] == "customer":
            _expect(party["accountSourceKey"] in accounts and accounts[party["accountSourceKey"]]["partyKey"] == party["partyKey"],
                    "Customer Party/account crosswalk mismatch.")
            account = accounts[party["accountSourceKey"]]
            allowed_segments = {"hospitality-buyer"} if party["customerType"] == "business" else {"fan", "family", "enthusiast", "vip"}
            _expect(account["segment"] in allowed_segments, "Customer account segment mismatch.")
        else:
            _expect(origin["segment"] == "sponsor", "Sponsor must reference sponsor Account.")
    for contact in contacts.values():
        _expect(contact["accountSourceKey"] in accounts and accounts[contact["accountSourceKey"]]["partyKey"] == contact["partyKey"],
                "Contact/account Party crosswalk mismatch.")
        _expect(contact["email"] == parties[contact["partyKey"]]["email"], "Contact/Party email mismatch.")
        _expect(parties[contact["partyKey"]]["customerType"] == "fan", "Contact must resolve person fan, not organization.")

    bundles: dict[str, list] = defaultdict(list)
    _expect(len(products) == (288 if rich else 4) and len(prices) == (1152 if rich else 4)
            and len(zones) == (96 if rich else 2), "Catalogue population mismatch.")
    for event_key in events_by_key:
        event_products = [p for p in products.values() if p["eventKey"] == event_key]
        _expect(Counter(p["productCode"] for p in event_products)
                == Counter({code: 6 if rich else 1 for code in ("PRD-REPLAY", "PRD-LIVE", "PRD-HOSP", "PRD-WEEKEND")}),
                "Wrong product codes or per-event coverage.")
        _expect(sum(z["eventKey"] == event_key for z in zones.values()) == (8 if rich else 2),
                "Zone event coverage mismatch.")
    paddock = next(k for k in zones if k.startswith("ZONE-PADDOCK-"))
    expected_prices = {"PRD-REPLAY": 5000, "PRD-LIVE": 7500, "PRD-HOSP": 100000, "PRD-WEEKEND": 105000}
    for product in products.values():
        code = product["productCode"]
        event = events_by_key[product["eventKey"]]
        session = sessions_by_event[product["eventKey"]]
        _expect(product["availability"] == ("unavailable-no-qualified-live-source" if code == "PRD-LIVE" else "available"),
                "Unqualified live product must remain unavailable.")
        if not rich:
            _expect(product["capacityPerUnit"] == ({paddock: 1} if code == "PRD-HOSP" else {}), "Wrong physical product capacity mapping.")
        else:
            _expect((len(product["capacityPerUnit"]) == 1 if code == "PRD-HOSP" else not product["capacityPerUnit"]),
                    "Wrong physical product capacity mapping.")
        _expect(all(k in zones and zones[k]["eventKey"] == product["eventKey"] for k in product["capacityPerUnit"]),
                "Product capacity crosses event.")
        _expect(product["saleFrom"] < product["saleTo"] and product["accessFrom"] < product["accessTo"], "Invalid product windows.")
        if code in {"PRD-HOSP", "PRD-WEEKEND", "PRD-LIVE"}:
            _expect(product["saleTo"] <= event["eventStartAt"] and product["accessFrom"] == event["eventStartAt"],
                    "Physical sale/access outside event window.")
        if code == "PRD-HOSP":
            _expect(product["accessTo"] == event["eventEndAt"], "Hospitality access beyond event.")
        if code == "PRD-REPLAY":
            _expect(product["saleFrom"] == product["accessFrom"] == session["availableFrom"]
                    and product["accessTo"] == session["availableTo"], "Replay availability mismatch.")
        if code == "PRD-WEEKEND":
            _expect(product["accessTo"] == session["availableTo"], "Bundle replay access interval mismatch.")
        _expect(all(type(units) is int and units > 0 for units in product["capacityPerUnit"].values()),
                "Physical capacity units must be positive integers.")
    prices_by_product: dict[str, list] = defaultdict(list)
    for price in prices.values():
        _expect(price["productKey"] in products
                and price["eventKey"] == products[price["productKey"]]["eventKey"]
                and price["amountMinor"] > 0
                and (rich or price["amountMinor"] == expected_prices[products[price["productKey"]]["productCode"]])
                and price["effectiveFrom"] < price["effectiveTo"], "Invalid catalogue price.")
        prices_by_product[price["productKey"]].append(price)
    _expect({r["productKey"] for r in prices.values()} == set(products), "Missing product price.")
    for product_key, versions in prices_by_product.items():
        versions = sorted(versions, key=lambda r: r["effectiveFrom"])
        _expect(len(versions) == (4 if rich else 1), "Price version population mismatch.")
        _expect(all(a["effectiveTo"] == b["effectiveFrom"] for a, b in zip(versions, versions[1:])),
                "Overlapping or gapped price intervals for product/currency.")
        _expect(not rich or (versions[0]["effectiveFrom"] <= products[product_key]["saleFrom"]
                and versions[-1]["effectiveTo"] >= products[product_key]["saleTo"]),
                "Prices do not cover product sales window.")
    for component in data["oracle/oracle_bundle_component.jsonl"]:
        _expect(type(component["quantity"]) is int and component["quantity"] > 0, "Invalid component quantity.")
        bundles[component["bundleProductKey"]].append(component)
    _expect(set(bundles) == {p["productKey"] for p in products.values() if p["productCode"] == "PRD-WEEKEND"},
            "Invalid bundle composition.")
    for bundle, components in bundles.items():
        _expect(len(components) == 2 and len({c["componentProductKey"] for c in components}) == 2,
                "Invalid bundle composition.")
        _expect(all(c["componentProductKey"] in products and c["quantity"] == 1
                    and products[c["componentProductKey"]]["eventKey"] == products[bundle]["eventKey"] for c in components),
                "Bundle component crosses event or has invalid quantity.")
        _expect({products[c["componentProductKey"]]["productCode"] for c in components} == {"PRD-REPLAY", "PRD-HOSP"},
                "Invalid bundle composition.")
        _physical_demand(bundle, products, bundles, 1)
    by_order = {}
    sold_demand = Counter({key: 0 for key in zones})
    for line in lines.values():
        _expect(line["orderKey"] in orders and line["productKey"] in products and line["priceKey"] in prices, "Missing order/product/price link.")
        order, product, price = orders[line["orderKey"]], products[line["productKey"]], prices[line["priceKey"]]
        event = events_by_key[order["eventKey"]]
        _expect(order["eventKey"] == product["eventKey"] == price["eventKey"], "Order catalogue crosses event.")
        _expect(line["orderKey"] not in by_order, "Expected exactly one line per order.")
        by_order[line["orderKey"]] = line
        _expect(type(line["quantity"]) is int and line["quantity"] > 0, "Line quantity must be a positive integer.")
        _expect(product["availability"] == "available", "Sale of unavailable product.")
        _expect(price["productKey"] == line["productKey"] and price["currency"] == line["currency"] == order["currency"]
                and price["amountMinor"] == line["unitPriceMinor"] and price["taxTreatment"] == line["taxTreatment"],
                "Selected price does not match order line.")
        _expect(price["effectiveFrom"] <= order["createdAt"] < price["effectiveTo"]
                and product["saleFrom"] <= order["createdAt"] <= order["confirmedAt"] < product["saleTo"], "Price or product not effective at order.")
        _expect(order["partyKey"] in parties and order["customerAccountSourceKey"] in accounts
                and accounts[order["customerAccountSourceKey"]]["partyKey"] == order["partyKey"], "Order/account Party mismatch.")
        _expect(parties[order["partyKey"]]["sourceUpdatedAt"] <= order["createdAt"]
                and accounts[order["customerAccountSourceKey"]]["sourceUpdatedAt"] <= order["createdAt"]
                and event["createdAt"] <= order["createdAt"]
                and product["sourceUpdatedAt"] <= order["createdAt"] and price["sourceUpdatedAt"] <= order["createdAt"],
                "Master created after dependent order.")
        _expect(line["createdAt"] == order["createdAt"] and order["lineCount"] == 1
                and order["recordState"] == order["orderState"] == "confirmed" and line["recordState"] == "open"
                and order["taxMinor"] == line["taxMinor"] == 0
                and line["netMinor"] == line["grossMinor"] == order["grossMinor"] == line["quantity"] * line["unitPriceMinor"],
                "Order/line financial mismatch.")
        _expect(order["journey"] == ("fan-purchase" if product["productCode"] == "PRD-REPLAY" else "hospitality-b2b"),
                "Incorrect order journey.")
        buyer = parties[order["partyKey"]]
        _expect(buyer["partyRole"] == "customer", "Commercial order buyer cannot be a sponsor.")
        _expect((buyer["customerType"], buyer["partyType"]) == (
            ("fan", "person") if order["journey"] == "fan-purchase" else ("business", "organization")),
            "Order journey/Party type mismatch: fan requires person; hospitality requires non-sponsor organization.")
        sold_demand.update(_physical_demand(line["productKey"], products, bundles, line["quantity"]))
    _expect(len(by_order) == params.order_count, "Order line coverage mismatch.")

    def per_order(path: str) -> dict:
        rows = data[path]
        _expect(len(rows) == len(orders) and {r["orderKey"] for r in rows} == set(orders),
                f"{path}: must cover each order exactly once.")
        return {r["orderKey"]: r for r in rows}

    payments = per_order("operational/payment_simulation.jsonl")
    entitlements = per_order("operational/entitlement.jsonl")
    reservations = per_order("operational/reservation.jsonl")
    credits = index("operational/scenario_credit.jsonl", "scenarioCreditKey")
    credits_by_order = {r["orderKey"]: r for r in credits.values()}
    _expect(len(credits_by_order) == len(credits) == max(1, params.order_count // 50), "Credit population/coverage mismatch.")
    cases = index("salesforce/case.jsonl", "caseKey")
    _expect(len(cases) == len(credits), "Case count mismatch.")
    active_demand = Counter()
    for key, order in orders.items():
        payment, entitlement, reservation, line = payments[key], entitlements[key], reservations[key], by_order[key]
        product = products[line["productKey"]]
        _expect(payment["simulatedOnly"] is True and payment["currency"] == order["currency"]
                and payment["amountMinor"] == order["grossMinor"] and payment["state"] == "approved"
                and order["createdAt"] <= payment["requestedAt"] <= payment["resolvedAt"] <= order["confirmedAt"],
                "Invalid simulated payment lifecycle/link/amount.")
        _expect(entitlement["partyKey"] == reservation["partyKey"] == order["partyKey"]
                and reservation["eventKey"] == order["eventKey"]
                and entitlement["productKey"] == line["productKey"] and entitlement["quantityGranted"] == line["quantity"]
                and entitlement["grantedAt"] == order["confirmedAt"], "Entitlement/reservation order cross-link mismatch.")
        _expect(entitlement["validFrom"] == product["accessFrom"] and entitlement["validTo"] == product["accessTo"], "Entitlement validity differs from product access.")
        component_products = [products[c["componentProductKey"]] for c in bundles[line["productKey"]]] if line["productKey"] in bundles else [product]
        expected_scopes = [{"productKey": p["productKey"], "validFrom": p["accessFrom"], "validTo": p["accessTo"]} for p in component_products]
        _expect(entitlement["accessScopes"] == expected_scopes, "Entitlement component access scope mismatch.")
        expected_state = "expired" if entitlement["validTo"] <= manifest["asOf"] else "active"
        _expect(type(entitlement["consumed"]) is bool, "Invalid consumed flag.")
        if entitlement["consumed"]:
            expected_state = "consumed"
            _expect(entitlement["consumedAt"] is not None
                    and max(entitlement["grantedAt"], max(p["accessFrom"] for p in component_products))
                    <= entitlement["consumedAt"] < entitlement["validTo"], "Invalid consumption time.")
        else:
            _expect(entitlement["consumedAt"] is None, "Unconsumed entitlement has consumption time.")
        credit = credits_by_order.get(key)
        revoked = False
        if credit:
            _expect(credit["caseKey"] in cases, "Credit missing CRM case.")
            case = cases[credit["caseKey"]]
            _expect(case["orderKey"] == key and case["partyKey"] == order["partyKey"]
                    and case["accountSourceKey"] == order["customerAccountSourceKey"]
                    and credit["entitlementKey"] == entitlement["entitlementKey"], "Credit/case/entitlement cross-link mismatch.")
            if parties[order["partyKey"]]["partyType"] == "person":
                _expect(case["contactSourceKey"] in contacts and contacts[case["contactSourceKey"]]["partyKey"] == order["partyKey"]
                        and case["contactNullReason"] is None, "Fan case must resolve its own Contact.")
            else:
                _expect(case["contactSourceKey"] is None and case["contactNullReason"] == "organization-account-no-person-contact",
                        "Business case must reference Account without inventing a person Contact.")
            _expect(case["state"] == "resolved" and credit["state"] == "issued", "Credit requires resolved case and issued approval.")
            _expect(order["confirmedAt"] < case["openedAt"] == credit["requestedAt"]
                    <= credit["decidedAt"] <= credit["issuedAt"] == case["resolvedAt"], "Invalid support/credit lifecycle.")
            _expect(0 < credit["amountMinor"] <= order["grossMinor"] and credit["currency"] == order["currency"], "Credit exceeds eligible balance or currency mismatch.")
            full = credit["amountMinor"] == order["grossMinor"]
            _expect(credit["creditType"] == ("full" if full else "partial") + "-scenario-credit-not-money-refund", "Invalid credit type.")
            if entitlement["consumed"]:
                _expect(entitlement["consumedAt"] < credit["issuedAt"], "Credit must not undo already consumed access.")
            revoked = full and not entitlement["consumed"]
            if revoked:
                expected_state = "revoked"
                _expect(entitlement["revokedAt"] == credit["issuedAt"], "Full credit revocation time mismatch.")
        _expect(entitlement["state"] == expected_state and (revoked or "revokedAt" not in entitlement), "Entitlement asOf/credit policy state mismatch.")
        demand = dict(_physical_demand(line["productKey"], products, bundles, line["quantity"]))
        _expect(all(zones[zone]["recordState"] == "active" and zones[zone]["sourceUpdatedAt"] <= order["createdAt"]
                    for zone in demand), "Capacity master unavailable at reservation.")
        _expect(all(component["recordState"] == "active" and component["sourceUpdatedAt"] <= order["createdAt"]
                    for component in bundles.get(line["productKey"], [])), "Bundle component unavailable at purchase.")
        _expect(reservation["orderLineKey"] == line["orderLineKey"] and reservation["zoneDemands"] == demand,
                "Reservation zone demand must derive from its actual order line.")
        _expect(all(type(q) is int and q > 0 for q in reservation["zoneDemands"].values()),
                "Reservation demand must use positive integer quantities.")
        _expect(reservation["capacityScope"] == ("physical" if demand else "digital-no-physical-allocation")
                and reservation["heldAt"] == order["createdAt"] and reservation["confirmedAt"] == order["confirmedAt"]
                and reservation["confirmedAt"] < reservation["expiresAt"], "Invalid reservation lifecycle.")
        _expect(reservation["state"] == ("released" if revoked else "confirmed"), "Reservation credit release mismatch.")
        if revoked:
            _expect(reservation["releasedAt"] == credit["issuedAt"], "Reservation release time mismatch.")
        else:
            active_demand.update(demand)
    _expect(manifest["capacity"]["zoneDemands"] == dict(sold_demand), "Manifest sold capacity demand mismatch.")
    _expect(manifest["capacity"]["zoneCapacities"] == {k: r["capacity"] for k, r in zones.items()}, "Manifest capacity mismatch.")
    _expect(manifest["capacity"]["bundleComponentRule"] == {key: [
        {"componentProductKey": c["componentProductKey"], "quantity": c["quantity"]} for c in components]
        for key, components in bundles.items()},
        "Manifest bundle rule mismatch.")
    for zone, row in zones.items():
        _expect(type(row["capacity"]) is int and row["capacity"] >= sold_demand[zone] >= active_demand[zone], "Derived physical demand exceeds capacity.")

    campaigns = index("salesforce/campaign.jsonl", "campaignKey")
    _expect(len(campaigns) == event_count and len(data["salesforce/consent.jsonl"]) == len(fan_customers), "Campaign/consent population mismatch.")
    consent_parties = set()
    for consent in data["salesforce/consent.jsonl"]:
        _expect(consent["partyKey"] in parties and consent["partyKey"] not in consent_parties
                and consent["purpose"] == "synthetic-demo-marketing" and consent["channel"] == "email"
                and consent["decisionBasis"] == "explicit-synthetic-fixture-not-inferred"
                and parties[consent["partyKey"]]["sourceUpdatedAt"] <= consent["decidedAt"] <= consent["effectiveAt"],
                "Invalid explicit consent decision/timing.")
        consent_parties.add(consent["partyKey"])
    _expect(consent_parties == {p["partyKey"] for p in fan_customers}, "Consent must cover person fan customers, not business customers or sponsors.")
    for touch in per_order("salesforce/campaign_touch.jsonl").values():
        _expect(touch["campaignKey"] in campaigns, "Touch missing campaign.")
        campaign, order = campaigns[touch["campaignKey"]], orders[touch["orderKey"]]
        _expect(touch["partyKey"] == order["partyKey"] and campaign["createdAt"] == campaign["startAt"]
                <= touch["occurredAt"] < campaign["endAt"]
                and parties[touch["partyKey"]]["sourceUpdatedAt"] <= touch["occurredAt"] <= order["createdAt"],
                "Incoherent campaign touch.")
        _expect(campaign["recordState"] == "ended" and campaign["endAt"] <= manifest["asOf"], "Campaign state not consistent with asOf.")
    physical_order_keys = {key for key, o in orders.items() if o["journey"] == "hospitality-b2b"}
    opportunities = data["salesforce/opportunity.jsonl"]
    _expect(len(opportunities) == len(physical_order_keys) and {o["orderKey"] for o in opportunities} == physical_order_keys, "Hospitality opportunity coverage mismatch.")
    for opportunity in opportunities:
        order = orders[opportunity["orderKey"]]
        _expect(opportunity["accountSourceKey"] == order["customerAccountSourceKey"] and opportunity["amountMinor"] == order["grossMinor"]
                and opportunity["currency"] == order["currency"] and opportunity["sourceUpdatedAt"] >= order["confirmedAt"],
                "Opportunity/order cross-link or financial mismatch.")

    bps = index("sap_plan_b/business_partner.jsonl", "sourceKey")
    suppliers = index("sap_plan_b/supplier.jsonl", "sourceKey")
    cost_centers = index("sap_plan_b/cost_center.jsonl", "sourceKey")
    _expect(len(suppliers) == len(cost_centers) == vendor_count and len(bps) == len(parties) + vendor_count, "SAP master population mismatch.")
    customer_bps = {}
    for bp in bps.values():
        _expect(bp["bpRole"] in {"Customer", "Supplier"}, "Invalid business partner role.")
        if bp["bpRole"] == "Customer":
            _expect(bp["partyKey"] in parties and bp["partyKey"] not in customer_bps, "Customer BP missing or duplicate Party crosswalk.")
            crosswalk = bp["partyCrosswalk"]
            _expect(crosswalk["canonicalEntity"] == "Party" and crosswalk["canonicalKey"] == bp["partyKey"]
                    and crosswalk["sourceReference"] == parties[bp["partyKey"]]["sourceReference"], "Customer BP Party crosswalk mismatch.")
            reference(crosswalk["sourceReference"])
            customer_bps[bp["partyKey"]] = bp
    _expect(set(customer_bps) == set(parties), "Missing customer BP for Party.")
    for supplier in suppliers.values():
        _expect(supplier["bpSourceKey"] in bps and bps[supplier["bpSourceKey"]]["bpRole"] == "Supplier"
                and bps[supplier["bpSourceKey"]]["sourceUpdatedAt"] <= supplier["sourceUpdatedAt"],
                "Supplier must resolve earlier Supplier BP.")
    _expect({s["bpSourceKey"] for s in suppliers.values()} == {b["sourceKey"] for b in bps.values() if b["bpRole"] == "Supplier"},
            "Orphan or duplicate Supplier BP.")

    agreements = index("salesforce/sponsorship_agreement.jsonl", "agreementKey")
    commitments = data["salesforce/sponsorship_commitment.jsonl"]
    _expect(len(agreements) == len(commitments) == max(event_count, 3, len(sponsors) // 2), "Sponsorship population mismatch.")
    commitment_by_agreement = {r["agreementKey"]: r for r in commitments}
    _expect(set(commitment_by_agreement) == set(agreements), "Commitment agreement coverage mismatch.")
    for agreement in agreements.values():
        event = events_by_key[agreement["eventKey"]]
        _expect(agreement["sponsorAccountKey"] in accounts and accounts[agreement["sponsorAccountKey"]]["segment"] == "sponsor",
                "Agreement must resolve sponsor Account.")
        _expect(accounts[agreement["sponsorAccountKey"]]["sourceUpdatedAt"] <= agreement["signedAt"] == agreement["validFrom"]
                < event["eventStartAt"] < agreement["validTo"], "Invalid sponsorship timeline.")
        commitment = commitment_by_agreement[agreement["agreementKey"]]
        _expect(commitment["sponsorAccountKey"] == agreement["sponsorAccountKey"]
                and commitment["currency"] == agreement["currency"] and commitment["roiClaimed"] is False
                and commitment["evidenceReference"].startswith("synthetic://")
                and 0 < commitment["fulfilledMinor"] < agreement["contractedMinor"]
                and commitment["recordState"] == "in_progress" and agreement["signedAt"] <= commitment["evidencedAt"]
                == commitment["dueAt"] == event["eventEndAt"], "Invalid evidenced sponsorship commitment.")

    docs = index("sap_plan_b/sap_document.jsonl", "erpDocumentKey")
    doc_lines = index("sap_plan_b/sap_document_line.jsonl", "erpDocumentLineKey")
    links = index("sap_plan_b/document_link.jsonl", "documentLinkKey")
    costs = index("sap_plan_b/supplier_cost.jsonl", "supplierCostKey")
    allocations = data["sap_plan_b/sap_cost_allocation.jsonl"]
    _expect(len(costs) == len(allocations) == max(event_count, 6, params.order_count // 4000), "Cost/allocation population mismatch.")
    _expect(len(docs) == len(doc_lines) == len(links) == len(orders) + len(credits) + len(agreements) + len(costs), "ERP document/line/link population mismatch.")
    invoice_orders, credit_documents, sponsor_documents, cost_documents = set(), set(), set(), set()
    invoice_posted_at = {}
    for doc in docs.values():
        _expect(doc["erpDocumentLineKey"] in doc_lines and doc["documentLinkKey"] in links, "ERP document missing line/link.")
        line, link = doc_lines[doc["erpDocumentLineKey"]], links[doc["documentLinkKey"]]
        _expect(line["erpDocumentKey"] == link["erpDocumentKey"] == doc["erpDocumentKey"]
                and line["documentSourceKey"] == doc["sourceKey"] and link["erpDocumentLineKey"] == line["erpDocumentLineKey"],
                "ERP line/link points at wrong document.")
        _expect(doc["recordState"] == doc["documentState"] == line["recordState"] == "posted"
                and link["recordState"] == "linked"
                and doc["postedAt"] == line["postedAt"] == link["linkedAt"]
                and doc["postedAt"] == doc["documentDate"] == doc["sourceUpdatedAt"], "ERP posting/link state or time mismatch.")
        _expect(type(line["lineQuantity"]) is int and line["lineQuantity"] > 0
                and line["lineQuantity"] * line["unitPriceMinor"] == line["lineNetMinor"]
                and line["lineTaxMinor"] == 0 and line["lineGrossMinor"] == line["lineNetMinor"] == doc["amountMinor"]
                and line["currency"] == doc["currency"], "ERP document/line financial mismatch.")
        _expect(doc["partnerSourceKey"] in bps, "ERP document missing business partner.")
        bp = bps[doc["partnerSourceKey"]]
        _expect(bp["sourceUpdatedAt"] <= doc["postedAt"], "Business partner created after document.")
        if doc["documentType"] in {"customer_invoice", "customer_credit_memo"}:
            _expect(bp["bpRole"] == "Customer" and bp["partyKey"] == doc["partyKey"], "Customer document must resolve Customer BP and Party.")
            if "orderKey" in doc:
                _expect(doc["orderKey"] in orders and orders[doc["orderKey"]]["partyKey"] == doc["partyKey"]
                        and link["orderKey"] == doc["orderKey"], "ERP order/Party/link mismatch.")
                order = orders[doc["orderKey"]]
                _expect(order["confirmedAt"] <= doc["postedAt"] and doc["currency"] == order["currency"], "Invoice precedes order or currency mismatch.")
                if doc["documentType"] == "customer_invoice":
                    order_line = by_order[doc["orderKey"]]
                    _expect(doc["orderKey"] not in invoice_orders and line["orderLineKey"] == order_line["orderLineKey"]
                            and line["lineQuantity"] == order_line["quantity"] and doc["amountMinor"] == order["grossMinor"]
                            and link["linkType"] == "order-to-document", "Order invoice reconciliation mismatch.")
                    invoice_orders.add(doc["orderKey"])
                    invoice_posted_at[doc["orderKey"]] = doc["postedAt"]
                else:
                    _expect(doc["scenarioCreditKey"] in credits, "Credit memo missing scenario credit.")
                    credit = credits[doc["scenarioCreditKey"]]
                    _expect(credit["orderKey"] == doc["orderKey"] and credit["amountMinor"] == doc["amountMinor"]
                            and credit["issuedAt"] <= doc["postedAt"] and link["scenarioCreditKey"] == credit["scenarioCreditKey"]
                            and link["linkType"] == "credit-to-document" and credit["scenarioCreditKey"] not in credit_documents,
                            "Credit memo reconciliation mismatch.")
                    credit_documents.add(credit["scenarioCreditKey"])
            else:
                _expect(doc["documentType"] == "customer_invoice" and doc["sponsorshipAgreementKey"] in agreements, "Missing sponsorship agreement.")
                agreement = agreements[doc["sponsorshipAgreementKey"]]
                commitment = commitment_by_agreement[agreement["agreementKey"]]
                _expect(accounts[agreement["sponsorAccountKey"]]["partyKey"] == doc["partyKey"]
                        and agreement["signedAt"] <= doc["postedAt"] and commitment["invoicedMinor"] == doc["amountMinor"]
                        and doc["amountMinor"] <= agreement["contractedMinor"]
                        and link["sponsorshipAgreementKey"] == agreement["agreementKey"] and link["linkType"] == "sponsorship-invoice"
                        and agreement["agreementKey"] not in sponsor_documents, "Sponsorship invoice mismatch.")
                sponsor_documents.add(agreement["agreementKey"])
        else:
            _expect(doc["documentType"] == "supplier_invoice" and bp["bpRole"] == "Supplier"
                    and doc["supplierSourceKey"] in suppliers and suppliers[doc["supplierSourceKey"]]["bpSourceKey"] == bp["sourceKey"],
                    "Supplier invoice must resolve Supplier BP.")
            _expect(link["linkType"] == "supplier-cost-document" and link["supplierCostKey"] in costs, "Missing supplier cost document link.")
            cost = costs[link["supplierCostKey"]]
            _expect(cost["supplierCostKey"] not in cost_documents and cost["documentSourceKey"] == doc["sourceKey"]
                    and cost["documentLineSourceKey"] == line["sourceKey"] and cost["supplierSourceKey"] == doc["supplierSourceKey"]
                    and cost["costCenterSourceKey"] in cost_centers and cost["amountMinor"] == doc["amountMinor"]
                    and cost["currency"] == doc["currency"] and suppliers[doc["supplierSourceKey"]]["sourceUpdatedAt"] <= doc["postedAt"]
                    and cost_centers[cost["costCenterSourceKey"]]["sourceUpdatedAt"] <= cost["incurredAt"],
                    "Supplier cost document reconciliation mismatch.")
            cost_documents.add(cost["supplierCostKey"])
    _expect(invoice_orders == set(orders) and credit_documents == set(credits) and sponsor_documents == set(agreements)
            and cost_documents == set(costs), "Missing/duplicate typed ERP document coverage.")
    for credit in credits.values():
        _expect(invoice_posted_at[credit["orderKey"]] <= credit["requestedAt"], "Credit requested before original invoice.")
    allocated = Counter()
    for allocation in allocations:
        _expect(allocation["supplierCostKey"] in costs, "Allocation missing supplier cost.")
        cost = costs[allocation["supplierCostKey"]]
        _expect(allocation["eventKey"] == cost["eventKey"]
                and allocation["supplierCostSourceKey"] == cost["sourceKey"] and allocation["supplierSourceKey"] == cost["supplierSourceKey"]
                and allocation["costCenterSourceKey"] == cost["costCenterSourceKey"] and allocation["currency"] == cost["currency"]
                and cost["recordState"] == "allocated" and allocation["recordState"] == "posted"
                and cost["incurredAt"] <= allocation["allocatedAt"] <= allocation["postedAt"], "Allocation source cross-link/timing mismatch.")
        if allocation["allocationTarget"] == "sponsorship-delivery":
            _expect(allocation["sponsorshipAgreementKey"] in agreements, "Missing allocation sponsorship target.")
        else:
            _expect(allocation["allocationTarget"] == "event-operation", "Invalid allocation target.")
            if "partyKey" in allocation:
                _expect(allocation["partyKey"] in parties, "Unknown allocation customer.")
        allocated[cost["supplierCostKey"]] += allocation["amountMinor"]
    _expect(dict(allocated) == {key: r["amountMinor"] for key, r in costs.items()}, "Per-cost allocation reconciliation mismatch.")

    receipts = data["operational/command_receipt.jsonl"]
    purchase_receipts = {r["orderKey"]: r for r in receipts if r["commandType"] == "purchase"}
    support_receipts = {r["scenarioCreditKey"]: r for r in receipts if r["commandType"] == "support-credit"}
    _expect(len(receipts) == len(orders) + len(credits) and set(purchase_receipts) == set(orders)
            and set(support_receipts) == set(credits) and len({r["idempotencyKey"] for r in receipts}) == len(receipts),
            "Local simulated receipt coverage/idempotency mismatch.")
    for key, receipt in purchase_receipts.items():
        _expect(receipt["idempotencyKey"] == orders[key]["idempotencyKey"] and receipt["paymentSimulationKey"] == payments[key]["paymentSimulationKey"]
                and receipt["entitlementKey"] == entitlements[key]["entitlementKey"]
                and receipt["sourceUpdatedAt"] >= orders[key]["confirmedAt"], "Purchase receipt cross-link mismatch.")
    for key, receipt in support_receipts.items():
        _expect(receipt["orderKey"] == credits[key]["orderKey"] and receipt["caseKey"] == credits[key]["caseKey"]
                and receipt["sourceUpdatedAt"] >= credits[key]["issuedAt"], "Support receipt cross-link mismatch.")
    _expect(manifest["financialTotalsBySourceCurrency"] == _financial_totals(data), "Per-source/currency financial totals mismatch.")
    reconciliation = {
        "currency": "USD",
        "commercialOrderGrossMinor": sum(r["grossMinor"] for r in orders.values()),
        "approvedSimulatedPaymentMinor": sum(r["amountMinor"] for r in payments.values()),
        "scenarioCreditMinor": sum(r["amountMinor"] for r in credits.values()),
        "commercialOrderNetAfterCreditMinor": sum(r["grossMinor"] for r in orders.values()) - sum(r["amountMinor"] for r in credits.values()),
        "postedCustomerInvoiceMinor": sum(r["amountMinor"] for r in docs.values() if r["documentType"] == "customer_invoice"),
        "postedOrderInvoiceMinor": sum(r["amountMinor"] for r in docs.values() if r["documentType"] == "customer_invoice" and "orderKey" in r),
        "postedCustomerCreditMemoMinor": sum(r["amountMinor"] for r in docs.values() if r["documentType"] == "customer_credit_memo"),
        "supplierCostMinor": sum(r["amountMinor"] for r in costs.values()),
        "allocatedCostMinor": sum(r["amountMinor"] for r in allocations),
        "sponsorshipContractedMinor": sum(r["contractedMinor"] for r in agreements.values()),
        "sponsorshipInvoicedMinor": sum(r["invoicedMinor"] for r in commitments),
        "sponsorshipFulfilledMinor": sum(r["fulfilledMinor"] for r in commitments),
    }
    _expect(manifest["reconciliation"] == reconciliation, "Separate financial reconciliation mismatch.")
    if rich:
        _expect(manifest["financialTotalsByEventSourceCurrency"] == _event_financial_totals(data),
                "Per-event/source/currency financial totals mismatch.")


def validate_dataset(output_path: Path) -> dict[str, Any]:
    try:
        manifest, data = _load_export(output_path)
        _validate_semantics(manifest, data, output_path)
        return {
            "status": "validated", "namespace": manifest["namespace"],
            "orderCount": len(data["operational/commercial_order.jsonl"]),
            "customerCount": sum(r["partyRole"] == "customer" for r in data["operational/party.jsonl"]),
            "fanCustomerCount": manifest["populationCounts"]["fanCustomerParties"],
            "businessCustomerCount": manifest["populationCounts"]["businessCustomerParties"],
            "recordCount": sum(len(rows) for rows in data.values()),
            "dataBytes": sum(item["sizeBytes"] for item in manifest["files"]),
            "datasetDigestSha256": manifest["datasetDigestSha256"],
        }
    except (KeyError, TypeError, ValueError, OSError, StopIteration, AttributeError) as exc:
        raise ValidationError(f"Invalid export structure or value: {exc}") from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate and validate deterministic synthetic high-volume source/operational fixtures."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="Generate a deterministic fixture export.")
    generate_parser.add_argument("--output-path", required=True, help="Destination directory for generated artifacts.")
    generate_parser.add_argument(
        "--customer-count",
        type=int,
        default=DEFAULT_CUSTOMER_COUNT,
        help="Total fan and business customer parties (minimum: 2; default: 10,000).",
    )
    generate_parser.add_argument(
        "--order-count",
        type=int,
        default=DEFAULT_ORDER_COUNT,
        help="Number of commercial orders (default: 25,000).",
    )
    generate_parser.add_argument("--seed", default=DEFAULT_SEED, help="Deterministic seed string.")
    generate_parser.add_argument(
        "--catalog-profile", choices=(LEGACY_PROFILE, DEFAULT_CATALOG_PROFILE),
        default=DEFAULT_CATALOG_PROFILE,
        help="Versioned catalogue profile; single-event-v1 preserves the original 13-row Oracle baseline.",
    )
    generate_parser.add_argument(
        "--run-version",
        default=DEFAULT_RUN_VERSION,
        help="Run-version namespace token (default: run-v1).",
    )
    generate_parser.add_argument(
        "--schema-version",
        default=DEFAULT_SCHEMA_VERSION,
        help="Schema version recorded in each record (default: 1.0.0).",
    )
    generate_parser.add_argument(
        "--scenario-id",
        default=DEFAULT_SCENARIO_ID,
        help="Scenario ID recorded in manifest metadata.",
    )
    generate_parser.add_argument(
        "--scenario-version",
        default=DEFAULT_SCENARIO_VERSION,
        help="Scenario version recorded in manifest metadata.",
    )
    generate_parser.add_argument(
        "--dataset-id",
        default=DEFAULT_DATASET_ID,
        help="Dataset identifier recorded in record provenance.",
    )
    generate_parser.add_argument(
        "--if-exists",
        choices=("error", "verify-noop"),
        default="error",
        help="Behavior when output path already exists and is non-empty.",
    )

    validate_parser = subparsers.add_parser("validate", help="Validate a generated fixture export.")
    validate_parser.add_argument("--output-path", required=True, help="Directory containing manifest.json and JSONL exports.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        params = GenerationParameters(
            output_path=Path(args.output_path),
            customer_count=args.customer_count,
            order_count=args.order_count,
            seed=args.seed,
            run_version=args.run_version,
            schema_version=args.schema_version,
            scenario_id=args.scenario_id,
            scenario_version=args.scenario_version,
            dataset_id=args.dataset_id,
            if_exists=args.if_exists,
            catalog_profile=args.catalog_profile,
        )
        try:
            result = generate_dataset(params)
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "validate":
        try:
            result = validate_dataset(Path(args.output_path))
        except ValidationError as exc:
            parser.error(str(exc))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
