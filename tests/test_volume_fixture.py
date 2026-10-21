from __future__ import annotations

import copy
import hashlib
import io
import itertools
import json
import tempfile
import unittest
from collections import Counter
from dataclasses import replace
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts.volume_fixture import (
    DEFAULT_CUSTOMER_COUNT,
    DEFAULT_ORDER_COUNT,
    DEFAULT_CATALOG_PROFILE,
    FILE_SPECS,
    LEGACY_PROFILE,
    NATURAL_IDENTITY_PROFILE,
    GenerationParameters,
    ValidationError,
    build_export_records,
    generate_dataset,
    main,
    validate_dataset,
)

ROOT = Path(__file__).resolve().parents[1]
ORDER = "operational/commercial_order.jsonl"
LINE = "operational/commercial_order_line.jsonl"
PAYMENT = "operational/payment_simulation.jsonl"
ENTITLEMENT = "operational/entitlement.jsonl"
RESERVATION = "operational/reservation.jsonl"
CREDIT = "operational/scenario_credit.jsonl"
PARTY = "operational/party.jsonl"
BP = "sap_plan_b/business_partner.jsonl"
DOC = "sap_plan_b/sap_document.jsonl"
DOCLINE = "sap_plan_b/sap_document_line.jsonl"
LINK = "sap_plan_b/document_link.jsonl"
PRODUCT = "oracle/oracle_catalog_product.jsonl"
PRICE = "oracle/oracle_price_list_entry.jsonl"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _digest(manifest: dict) -> str:
    # Deliberately recompute independently of the production helper.
    payload = {
        "namespace": manifest["namespace"],
        "parameters": manifest["parameters"],
        "files": [{k: f[k] for k in ("path", "recordCount", "sha256")} for f in manifest["files"]],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class VolumeFixtureIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="volume-test-", dir=ROOT)
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.output = self.root / "export"
        self.params = GenerationParameters(self.output, customer_count=30, order_count=600,
                                           catalog_profile=LEGACY_PROFILE)

    def generate_small(self) -> None:
        self.assertEqual("generated", generate_dataset(self.params)["status"])
        self.assertEqual("validated", validate_dataset(self.output)["status"])

    def manifest(self) -> dict:
        return json.loads((self.output / "manifest.json").read_bytes())

    def write_manifest(self, manifest: dict, *, refresh_digest: bool = True) -> None:
        if refresh_digest:
            manifest["datasetDigestSha256"] = _digest(manifest)
        (self.output / "manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")

    def corrupt(self, changes: dict[str, list[dict]]) -> None:
        manifest = self.manifest()
        for path, rows in changes.items():
            payload = ("\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows) + "\n").encode()
            (self.output / path).write_bytes(payload)
            entry = next(f for f in manifest["files"] if f["path"] == path)
            entry.update(recordCount=len(rows), sizeBytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        self.write_manifest(manifest)
        self.assertEqual(_digest(manifest), self.manifest()["datasetDigestSha256"])

    def rows(self, path: str) -> list[dict]:
        return _read_jsonl(self.output / path)

    def assert_semantic_rejection(self, message: str) -> None:
        with self.assertRaisesRegex(ValidationError, message):
            validate_dataset(self.output)

    def test_generate_and_validate_exact_default_scale(self) -> None:
        result = generate_dataset(GenerationParameters(self.output))
        self.assertEqual("generated", result["status"])
        validation = validate_dataset(self.output)
        self.assertEqual("validated", validation["status"])
        self.assertEqual(DEFAULT_CUSTOMER_COUNT, validation["customerCount"])
        self.assertEqual(DEFAULT_ORDER_COUNT, validation["orderCount"])
        manifest = self.manifest()
        self.assertEqual(10000, manifest["populationCounts"]["customerParties"])
        self.assertEqual(8000, manifest["populationCounts"]["fanCustomerParties"])
        self.assertEqual(2000, manifest["populationCounts"]["businessCustomerParties"])
        self.assertEqual(8, manifest["populationCounts"]["sponsorParties"])
        self.assertEqual(Counter({("customer", "fan", "person"): 8000,
                                  ("customer", "business", "organization"): 2000,
                                  ("sponsor", None, "organization"): 8}),
                         Counter((r["partyRole"], r["customerType"], r["partyType"]) for r in self.rows(PARTY)))
        self.assertEqual(8000, len(self.rows("salesforce/contact.jsonl")))
        self.assertEqual(25000, manifest["parameters"]["orderCount"])
        self.assertEqual(set(FILE_SPECS), {f["path"] for f in manifest["files"]})
        self.assertEqual(_digest(manifest), validation["datasetDigestSha256"])
        self.assertEqual(10014, sum(f["recordCount"] for f in manifest["files"] if f["path"] == BP))
        self.assertEqual(DEFAULT_CATALOG_PROFILE, manifest["parameters"]["catalogProfile"])
        self.assertEqual(
            {"OracleEvent": 12, "OracleCircuitZone": 96, "OracleCatalogProduct": 288,
             "OraclePriceListEntry": 1152, "OracleBundleComponent": 144},
            manifest["countsBySourceEntity"]["oracle"],
        )
        events = {r["eventKey"] for r in self.rows("oracle/oracle_event.jsonl")}
        for path in (ORDER, ENTITLEMENT, RESERVATION, DOC, "salesforce/campaign.jsonl",
                     "salesforce/campaign_touch.jsonl", "salesforce/opportunity.jsonl", "salesforce/case.jsonl",
                     "salesforce/sponsorship_agreement.jsonl", "sap_plan_b/supplier_cost.jsonl"):
            self.assertEqual(events, {r["eventKey"] for r in self.rows(path)}, path)
        products = {r["productKey"] for r in self.rows(PRODUCT) if r["availability"] == "available"}
        self.assertEqual(products, {r["productKey"] for r in self.rows(LINE)})
        totals = manifest["financialTotalsByEventSourceCurrency"]
        self.assertEqual(events, set(totals))
        for event in totals.values():
            operational = event["synthetic-operational"]["USD"]
            sap = event["sap-plan-b-synthetic"]["USD"]
            self.assertEqual(operational["commercialOrderGrossMinor"], sap["postedOrderInvoiceMinor"])
            self.assertEqual(operational["scenarioCreditMinor"], sap["postedCustomerCreditMemoMinor"])
            self.assertEqual(sap["supplierCostMinor"], sap["allocatedCostMinor"])

    def test_determinism_noop_and_no_overwrite_leave_all_bytes_unchanged(self) -> None:
        self.generate_small()
        self.assertEqual("5f7724052ddc0830da6df79482231eaa0d6192a1dfe2951b3d0c7dd24ea28ce8",
                         self.manifest()["datasetDigestSha256"])
        before = {p.relative_to(self.output): p.read_bytes() for p in self.output.rglob("*") if p.is_file()}
        self.assertEqual("no-op-verified", generate_dataset(replace(self.params, if_exists="verify-noop"))["status"])
        with self.assertRaises(FileExistsError):
            generate_dataset(self.params)
        with self.assertRaises(FileExistsError):
            generate_dataset(replace(self.params, seed="different", if_exists="verify-noop"))
        for path, payload in before.items():
            self.assertEqual(payload, (self.output / path).read_bytes())
        other = self.root / "other"
        generate_dataset(replace(self.params, output_path=other))
        self.assertEqual(before, {p.relative_to(other): p.read_bytes() for p in other.rglob("*") if p.is_file()})

    def test_all_keys_are_disjoint_for_every_namespace_dimension(self) -> None:
        params = replace(self.params, customer_count=3, order_count=5, run_version="a.b")
        variations = [
            params, replace(params, dataset_id="other-dataset"), replace(params, scenario_id="other-scenario"),
            replace(params, scenario_version="2.0.0"), replace(params, seed="other-seed"),
            replace(params, run_version="a-b"),
        ]

        def keys(value):
            result = set()
            if isinstance(value, dict):
                for field, item in value.items():
                    if field.endswith("Key") and isinstance(item, str):
                        result.add(item)
                    result.update(keys(item))
            elif isinstance(value, list):
                for item in value:
                    result.update(keys(item))
            return result

        key_sets = []
        for variant in variations:
            records, manifest = build_export_records(variant)
            key_sets.append(keys(records) | {manifest["publicationKey"]})
        for a, b in itertools.combinations(key_sets, 2):
            self.assertTrue(a.isdisjoint(b))

    def test_policy_states_physical_demand_and_source_crosswalks(self) -> None:
        self.generate_small()
        parties, bps = self.rows(PARTY), self.rows(BP)
        self.assertEqual(Counter({("customer", "fan", "person"): 24,
                                  ("customer", "business", "organization"): 6,
                                  ("sponsor", None, "organization"): 8}),
                         Counter((r["partyRole"], r["customerType"], r["partyType"]) for r in parties))
        self.assertEqual(30, sum(r["partyRole"] == "customer" for r in parties))
        self.assertEqual(len(parties), sum(bp["bpRole"] == "Customer" for bp in bps))
        self.assertTrue(all(bp["canonicalKey"] is None and bp["canonicalEntity"] is None for bp in bps))
        identities = [tuple(r[k] for k in ("sourceSystem", "sourceTenant", "sourceEntity", "sourceKey"))
                      for path in FILE_SPECS for r in self.rows(path)]
        self.assertEqual(len(identities), len(set(identities)))
        products = {r["productKey"]: r for r in self.rows(PRODUCT)}
        orders = {r["orderKey"]: r for r in self.rows(ORDER)}
        lines = {r["orderKey"]: r for r in self.rows(LINE)}
        entitlements = {r["orderKey"]: r for r in self.rows(ENTITLEMENT)}
        party_by_key = {r["partyKey"]: r for r in parties}
        for order in orders.values():
            buyer = party_by_key[order["partyKey"]]
            self.assertEqual("customer", buyer["partyRole"])
            self.assertEqual("person" if order["journey"] == "fan-purchase" else "organization", buyer["partyType"])
            self.assertEqual("Contact" if buyer["partyType"] == "person" else "Account", buyer["sourceReference"]["sourceEntity"])
        contacts = {r["sourceKey"]: r for r in self.rows("salesforce/contact.jsonl")}
        for case in self.rows("salesforce/case.jsonl"):
            buyer = party_by_key[case["partyKey"]]
            self.assertEqual(buyer["accountSourceKey"], case["accountSourceKey"])
            if buyer["partyType"] == "person":
                self.assertEqual(buyer["partyKey"], contacts[case["contactSourceKey"]]["partyKey"])
            else:
                self.assertIsNone(case["contactSourceKey"])
                self.assertEqual("organization-account-no-person-contact", case["contactNullReason"])
        for reservation in self.rows(RESERVATION):
            line = lines[reservation["orderKey"]]
            product = products[line["productKey"]]
            if product["productCode"] == "PRD-REPLAY":
                self.assertEqual({}, reservation["zoneDemands"])
            else:
                self.assertEqual(line["quantity"], sum(reservation["zoneDemands"].values()))
        policies = set()
        for credit in self.rows(CREDIT):
            entitlement = entitlements[credit["orderKey"]]
            full = credit["amountMinor"] == orders[credit["orderKey"]]["grossMinor"]
            policies.add((full, entitlement["consumed"]))
            if entitlement["consumed"]:
                self.assertEqual("consumed", entitlement["state"])
            elif full:
                self.assertEqual("revoked", entitlement["state"])
            else:
                self.assertIn(entitlement["state"], {"active", "expired"})
        self.assertEqual({(True, False), (False, False), (True, True), (False, True)}, policies)
        reconciliation = self.manifest()["reconciliation"]
        self.assertEqual(reconciliation["commercialOrderGrossMinor"], reconciliation["postedOrderInvoiceMinor"])
        self.assertEqual(reconciliation["postedCustomerInvoiceMinor"],
                         reconciliation["postedOrderInvoiceMinor"] + reconciliation["sponsorshipInvoicedMinor"])

    def test_journey_buyer_type_and_sponsor_exclusion_rejected_after_rehash(self) -> None:
        self.generate_small()
        parties = self.rows(PARTY)
        accounts = {r["partyKey"]: r["sourceKey"] for r in self.rows("salesforce/account.jsonl")}
        fan = next(p for p in parties if p["customerType"] == "fan")
        business = next(p for p in parties if p["customerType"] == "business")
        sponsor = next(p for p in parties if p["partyRole"] == "sponsor")
        original = self.rows(ORDER)
        for index, wrong_buyer, message in [
            (1, fan, "journey/Party type mismatch"),
            (2, fan, "journey/Party type mismatch"),
            (0, business, "journey/Party type mismatch"),
            (1, sponsor, "buyer cannot be a sponsor"),
            (0, sponsor, "buyer cannot be a sponsor"),
        ]:
            with self.subTest(index=index, wrong_buyer=wrong_buyer["partyRole"] + str(wrong_buyer["customerType"])):
                rows = copy.deepcopy(original)
                rows[index].update(partyKey=wrong_buyer["partyKey"], customerAccountSourceKey=accounts[wrong_buyer["partyKey"]])
                self.corrupt({ORDER: rows})
                try:
                    self.assert_semantic_rejection(message)
                finally:
                    self.corrupt({ORDER: original})

    def test_missing_bp_partner_and_wrong_bp_role_rejected_after_rehash(self) -> None:
        self.generate_small()
        original = self.rows(DOC)
        supplier = next(r for r in self.rows(BP) if r["bpRole"] == "Supplier")
        for partner in (None, supplier["sourceKey"], self.rows("salesforce/account.jsonl")[0]["sourceKey"]):
            with self.subTest(partner=partner):
                rows = copy.deepcopy(original)
                if partner is None:
                    rows[0].pop("partnerSourceKey")
                else:
                    rows[0]["partnerSourceKey"] = partner
                self.corrupt({DOC: rows})
                self.assert_semantic_rejection("business partner|Customer BP|structure")

    def test_duplicate_source_identity_rejected_after_rehash(self) -> None:
        self.generate_small()
        rows = self.rows("salesforce/contact.jsonl")
        rows[1]["sourceKey"] = rows[0]["sourceKey"]
        self.corrupt({"salesforce/contact.jsonl": rows})
        self.assert_semantic_rejection("Duplicate source identity")

    def test_missing_bp_master_rejected_with_counts_and_all_digests_refreshed(self) -> None:
        self.generate_small()
        rows = self.rows(BP)
        rows.pop(next(i for i, r in enumerate(rows) if r["bpRole"] == "Customer"))
        self.corrupt({BP: rows})
        manifest = self.manifest()
        manifest["countsBySourceEntity"]["sap-plan-b-synthetic"]["BusinessPartner"] -= 1
        self.write_manifest(manifest)
        self.assert_semantic_rejection("SAP master population")

    def test_missing_scope_and_typed_projection_reference_rejected_after_rehash(self) -> None:
        self.generate_small()
        original = self.rows(PARTY)
        for mutate, pattern in [
            (lambda r: r.pop("datasetId"), "scope mismatch"),
            (lambda r: r["sourceReference"].update(sourceEntity="Account"), "Wrong source reference|Missing typed"),
            (lambda r: r.update(canonicalKey=r["sourceKey"]), "canonical key"),
        ]:
            with self.subTest(pattern=pattern):
                rows = copy.deepcopy(original)
                mutate(rows[0])
                self.corrupt({PARTY: rows})
                self.assert_semantic_rejection(pattern)

    def test_live_sale_live_price_and_cleared_zone_demands_rejected_after_rehash(self) -> None:
        self.generate_small()
        live = next(r for r in self.rows(PRODUCT) if r["productCode"] == "PRD-LIVE")
        live_price = next(r for r in self.rows(PRICE) if r["productKey"] == live["productKey"])
        lines, reservations = self.rows(LINE), self.rows(RESERVATION)
        self.assertTrue(reservations[1]["zoneDemands"])
        lines[1].update(productKey=live["productKey"], priceKey=live_price["priceKey"])
        reservations[1]["zoneDemands"] = {}
        self.corrupt({LINE: lines, RESERVATION: reservations})
        self.assert_semantic_rejection("Sale of unavailable product")

    def test_price_quantity_financial_and_link_corruptions_rejected_after_rehash(self) -> None:
        self.generate_small()
        mutations = [
            (LINE, "priceKey", lambda rows: self.rows(PRICE)[2]["priceKey"], "Selected price"),
            (LINE, "quantity", lambda rows: True, "positive integer"),
            (LINE, "quantity", lambda rows: 0, "positive integer"),
            (LINE, "quantity", lambda rows: 1.5, "positive integer"),
            (LINE, "unitPriceMinor", lambda rows: rows[0]["unitPriceMinor"] + 1, "Selected price"),
            (LINE, "unitPriceMinor", lambda rows: 5000.0, "integer minor units"),
            (LINE, "currency", lambda rows: "EUR", "Unsupported currency"),
            (LINE, "orderKey", lambda rows: rows[1]["orderKey"], "one line|order population|coverage|effective at order"),
            (PAYMENT, "amountMinor", lambda rows: rows[0]["amountMinor"] + 1, "payment"),
            (DOC, "amountMinor", lambda rows: rows[0]["amountMinor"] + 1, "financial mismatch"),
            (DOCLINE, "lineNetMinor", lambda rows: rows[0]["lineNetMinor"] + 1, "financial mismatch"),
            (LINK, "erpDocumentKey", lambda rows: rows[1]["erpDocumentKey"], "wrong document"),
            (CREDIT, "amountMinor", lambda rows: 10**12, "eligible balance"),
            (CREDIT, "caseKey", lambda rows: rows[1]["caseKey"], "cross-link mismatch"),
            ("sap_plan_b/sap_cost_allocation.jsonl", "amountMinor", lambda rows: rows[0]["amountMinor"] + 1, "Per-cost"),
            ("salesforce/sponsorship_commitment.jsonl", "invoicedMinor", lambda rows: rows[0]["invoicedMinor"] + 1, "Sponsorship invoice"),
        ]
        originals = {path: self.rows(path) for path, *_ in mutations}
        for path, field, value, pattern in mutations:
            with self.subTest(path=path, field=field):
                rows = copy.deepcopy(originals[path])
                rows[0][field] = value(rows)
                self.corrupt({path: rows})
                try:
                    self.assert_semantic_rejection(pattern)
                finally:
                    self.corrupt({path: originals[path]})

    def test_timing_capacity_and_credit_policy_corruptions_rejected_after_rehash(self) -> None:
        self.generate_small()
        mutations = [
            (ORDER, lambda r: r.update(createdAt="2031-01-01T00:00:00Z"), "Future visible|effective at order"),
            (PARTY, lambda r: r.update(sourceUpdatedAt="2030-12-01T00:00:00Z", ingestedAt="2030-12-01T00:01:00Z"), "Projection timestamp|Master created"),
            (ENTITLEMENT, lambda r: r.update(validTo="2030-06-01T00:00:00Z"), "validity differs"),
            (ENTITLEMENT, lambda r: r.update(state="active", recordState="active"), "policy state"),
            (RESERVATION, lambda r: r.update(zoneDemands={}), "derive from"),
            (RESERVATION, lambda r: r.update(zoneDemands={k: True for k in r["zoneDemands"]}), "positive integer"),
            (PRICE, lambda r: r.update(effectiveFrom="2030-12-01T00:00:00Z"), "effective at order"),
            ("salesforce/campaign_touch.jsonl", lambda r: r.update(occurredAt="2029-01-01T00:00:00Z"), "campaign touch"),
            ("salesforce/consent.jsonl", lambda r: r.update(decisionBasis="inferred-from-purchase"), "explicit consent"),
            (CREDIT, lambda r: r.update(issuedAt="2029-01-01T00:00:00Z"), "credit lifecycle"),
        ]
        for path, mutate, pattern in mutations:
            with self.subTest(path=path, pattern=pattern):
                original = self.rows(path)
                rows = copy.deepcopy(original)
                index = 1 if path == RESERVATION else 0
                mutate(rows[index])
                self.corrupt({path: rows})
                try:
                    self.assert_semantic_rejection(pattern)
                finally:
                    self.corrupt({path: original})
        zones = self.rows("oracle/oracle_circuit_zone.jsonl")
        next(z for z in zones if z["zoneKey"].startswith("ZONE-PADDOCK"))["capacity"] = 0
        manifest = self.manifest()
        manifest["capacity"]["zoneCapacities"] = {z["zoneKey"]: z["capacity"] for z in zones}
        self.write_manifest(manifest)
        self.corrupt({"oracle/oracle_circuit_zone.jsonl": zones})
        self.assert_semantic_rejection("exceeds capacity")

    def test_manifest_corruptions_and_exact_file_set_rejected(self) -> None:
        self.generate_small()
        original = self.manifest()
        mutations = [
            (lambda m: m.update(datasetDigestSha256="0" * 64), "Aggregate dataset digest", False),
            (lambda m: m["populationCounts"].update(customerParties=999), "Population counts", True),
            (lambda m: m["populationCounts"].update(fanCustomerParties=0), "Population counts", True),
            (lambda m: m["populationCounts"].update(businessCustomerParties=0), "Population counts", True),
            (lambda m: m["countsBySourceEntity"]["oracle"].update(OracleEvent=2), "entity counts", True),
            (lambda m: m.update(namespace="other"), "scope mismatch", True),
            (lambda m: m["files"].pop(), "exact supported file set", True),
            (lambda m: m["files"].append(m["files"][0]), "exact supported file set", True),
            (lambda m: m["files"][0].update(path="../escape.jsonl"), "exact supported file set", True),
            (lambda m: m["files"][0].update(sizeBytes=0), "Byte size", True),
            (lambda m: m["financialTotalsBySourceCurrency"]["salesforce"]["USD"].update(sponsorshipFulfilledMinor=0), "Per-source/currency", True),
            (lambda m: m["reconciliation"].update(sponsorshipContractedMinor=0), "financial reconciliation", True),
        ]
        for mutate, pattern, refresh in mutations:
            with self.subTest(pattern=pattern):
                manifest = copy.deepcopy(original)
                mutate(manifest)
                self.write_manifest(manifest, refresh_digest=refresh)
                self.assert_semantic_rejection(pattern)
        self.write_manifest(original)
        (self.output / "extra.jsonl").write_text("{}\n", encoding="utf-8")
        self.assert_semantic_rejection("unlisted export files")

    def test_invalid_parameters_fail_without_partial_output(self) -> None:
        for changes in [
            {"customer_count": 0}, {"order_count": -1}, {"customer_count": True},
            {"order_count": 1.5}, {"seed": ""}, {"run_version": " "},
            {"scenario_id": ""}, {"scenario_version": ""}, {"dataset_id": ""},
            {"schema_version": "unsupported"}, {"if_exists": "overwrite"},
        ]:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    generate_dataset(replace(self.params, **changes))
                self.assertFalse(self.output.exists())
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as error:
                main(["generate", "--output-path", str(self.output), "--order-count", "0"])
        self.assertEqual(2, error.exception.code)
        self.assertEqual("", output.getvalue())
        self.assertFalse(self.output.exists())

    def test_one_customer_cannot_represent_both_required_types(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 2.*person fans.*organization hospitality"):
            generate_dataset(replace(self.params, customer_count=1))
        self.assertFalse(self.output.exists())
        with redirect_stderr(io.StringIO()) as errors, redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as error:
                main(["generate", "--output-path", str(self.output), "--customer-count", "1"])
        self.assertEqual(2, error.exception.code)
        self.assertIn("both person fans and organization hospitality buyers", errors.getvalue())
        self.assertEqual("", output.getvalue())
        self.assertFalse(self.output.exists())

    def generate_rich(self, order_count: int = 600) -> None:
        self.params = replace(self.params, catalog_profile=DEFAULT_CATALOG_PROFILE, order_count=order_count)
        self.generate_small()

    def test_rich_profile_determinism_isolation_and_minimum_coverage(self) -> None:
        self.generate_rich(36)
        self.assertEqual("no-op-verified", generate_dataset(replace(self.params, if_exists="verify-noop"))["status"])
        before = {p.relative_to(self.output): p.read_bytes() for p in self.output.rglob("*") if p.is_file()}
        other = self.root / "rich-other"
        generate_dataset(replace(self.params, output_path=other))
        self.assertEqual(before, {p.relative_to(other): p.read_bytes() for p in other.rglob("*") if p.is_file()})
        self.assertEqual(12, len(self.rows("oracle/oracle_event.jsonl")))
        self.assertEqual(Counter({e["eventKey"]: 3 for e in self.rows("oracle/oracle_event.jsonl")}),
                         Counter(r["eventKey"] for r in self.rows(ORDER)))
        with self.assertRaises(FileExistsError):
            generate_dataset(replace(self.params, catalog_profile=LEGACY_PROFILE, if_exists="verify-noop"))
        rich_records, _ = build_export_records(self.params)
        legacy_records, _ = build_export_records(replace(self.params, catalog_profile=LEGACY_PROFILE))
        rich_keys = {r["sourceKey"] for rows in rich_records.values() for r in rows}
        self.assertTrue(rich_keys.isdisjoint(r["sourceKey"] for rows in legacy_records.values() for r in rows))
        with self.assertRaisesRegex(ValueError, "at least 36"):
            generate_dataset(replace(self.params, output_path=self.root / "too-small", order_count=35))

    def test_rich_cross_event_links_rejected_after_rehash(self) -> None:
        self.generate_rich()
        events = self.rows("oracle/oracle_event.jsonl")
        for path in (ORDER, LINE, PAYMENT, ENTITLEMENT, RESERVATION, CREDIT, DOC, DOCLINE, LINK,
                     "salesforce/campaign_touch.jsonl", "salesforce/opportunity.jsonl",
                     "salesforce/case.jsonl", "salesforce/sponsorship_commitment.jsonl",
                     "sap_plan_b/sap_cost_allocation.jsonl"):
            with self.subTest(path=path):
                original = self.rows(path)
                rows = copy.deepcopy(original)
                rows[0]["eventKey"] = next(e["eventKey"] for e in events if e["eventKey"] != rows[0]["eventKey"])
                self.corrupt({path: rows})
                try:
                    self.assert_semantic_rejection("crosses event")
                finally:
                    self.corrupt({path: original})

    def test_rich_price_overlap_gap_and_wrong_effective_version_rejected_after_rehash(self) -> None:
        self.generate_rich()
        original = self.rows(PRICE)
        for boundary in ("2030-03-31T00:00:00Z", "2030-04-02T00:00:00Z"):
            rows = copy.deepcopy(original)
            rows[1]["effectiveFrom"] = boundary
            self.corrupt({PRICE: rows})
            try:
                self.assert_semantic_rejection("Overlapping or gapped")
            finally:
                self.corrupt({PRICE: original})
        lines = self.rows(LINE)
        selected = next(p for p in original if p["priceKey"] == lines[0]["priceKey"])
        alternative = next(p for p in original if p["productKey"] == selected["productKey"]
                           and p["priceKey"] != selected["priceKey"])
        lines[0]["priceKey"] = alternative["priceKey"]
        self.corrupt({LINE: lines})
        self.assert_semantic_rejection("Selected price|not effective")

    def test_rich_bundle_capacity_and_coverage_rejected_after_rehash(self) -> None:
        self.generate_rich()
        path = "oracle/oracle_bundle_component.jsonl"
        original = self.rows(path)
        for target in (original[2]["componentProductKey"], original[0]["bundleProductKey"]):
            rows = copy.deepcopy(original)
            if target == original[2]["componentProductKey"]:
                target = next(r["componentProductKey"] for r in original if r["eventKey"] != rows[0]["eventKey"])
            rows[0]["componentProductKey"] = target
            self.corrupt({path: rows})
            try:
                self.assert_semantic_rejection("crosses event|Invalid bundle")
            finally:
                self.corrupt({path: original})
        original_products = self.rows(PRODUCT)
        products = copy.deepcopy(original_products)
        hospitality = next(p for p in products if p["productCode"] == "PRD-HOSP")
        other_zone = next(z for z in self.rows("oracle/oracle_circuit_zone.jsonl")
                          if z["eventKey"] != hospitality["eventKey"])
        hospitality["capacityPerUnit"] = {other_zone["zoneKey"]: 1}
        self.corrupt({PRODUCT: products})
        self.assert_semantic_rejection("capacity crosses event")
        self.corrupt({PRODUCT: original_products})
        zones_path = "oracle/oracle_circuit_zone.jsonl"
        zones = self.rows(zones_path)
        zone_key = next(key for r in self.rows(RESERVATION) for key in r["zoneDemands"])
        next(z for z in zones if z["zoneKey"] == zone_key)["capacity"] = 0
        manifest = self.manifest()
        manifest["capacity"]["zoneCapacities"][zone_key] = 0
        self.write_manifest(manifest)
        self.corrupt({zones_path: zones})
        self.assert_semantic_rejection("exceeds capacity")

    def test_rich_manifest_event_finances_and_missing_coverage_rejected_after_rehash(self) -> None:
        self.generate_rich()
        original_manifest = self.manifest()
        manifest = copy.deepcopy(original_manifest)
        event = next(iter(manifest["financialTotalsByEventSourceCurrency"].values()))
        event["sap-plan-b-synthetic"]["USD"]["postedOrderInvoiceMinor"] += 1
        self.write_manifest(manifest)
        self.assert_semantic_rejection("Per-event/source/currency")
        self.write_manifest(original_manifest)
        rows = self.rows("operational/replay_session.jsonl")
        rows[-1]["eventKey"] = rows[0]["eventKey"]
        self.corrupt({"operational/replay_session.jsonl": rows})
        self.assert_semantic_rejection("Replay event coverage")

    def test_natural_identities_preserve_all_keys_relationships_and_oracle_bytes(self) -> None:
        for profile in (LEGACY_PROFILE, DEFAULT_CATALOG_PROFILE):
            with self.subTest(profile=profile):
                baseline = replace(self.params, catalog_profile=profile)
                natural = replace(baseline, identity_profile=NATURAL_IDENTITY_PROFILE)
                old, old_manifest = build_export_records(baseline)
                new, new_manifest = build_export_records(natural)
                self.assertEqual(baseline.namespace, natural.namespace)
                self.assertEqual(baseline.key_token, natural.key_token)
                self.assertEqual(old_manifest["reconciliation"], new_manifest["reconciliation"])
                self.assertEqual(old_manifest["populationCounts"], new_manifest["populationCounts"])
                self.assertEqual(NATURAL_IDENTITY_PROFILE, new_manifest["parameters"]["identityProfile"])
                for path in FILE_SPECS:
                    if path.startswith("oracle/"):
                        self.assertEqual(old[path], new[path])
                    for before, after in zip(old[path], new[path], strict=True):
                        changed = {field for field in before.keys() | after.keys() if before.get(field) != after.get(field)}
                        self.assertLessEqual(changed, {"displayName", "firstName", "lastName", "identityProfile"})
                natural_path = self.root / profile
                generate_dataset(replace(natural, output_path=natural_path))
                self.assertEqual("validated", validate_dataset(natural_path)["status"])
                self.assertEqual("no-op-verified", generate_dataset(
                    replace(natural, output_path=natural_path, if_exists="verify-noop"))["status"])
                with self.assertRaises(FileExistsError):
                    generate_dataset(replace(baseline, output_path=natural_path, if_exists="verify-noop"))

    def test_natural_profile_full_scale_safe_names_and_cross_source_identity(self) -> None:
        generate_dataset(GenerationParameters(self.output, identity_profile=NATURAL_IDENTITY_PROFILE))
        validation = validate_dataset(self.output)
        self.assertEqual((10000, 25000, 308365),
                         (validation["customerCount"], validation["orderCount"], validation["recordCount"]))
        parties = {r["partyKey"]: r for r in self.rows(PARTY)}
        accounts = {r["partyKey"]: r for r in self.rows("salesforce/account.jsonl")}
        fans = [p for p in parties.values() if p["partyType"] == "person"]
        self.assertEqual(8000, len({p["displayName"] for p in fans}))
        for party in parties.values():
            self.assertNotIn("Synthetic", party["displayName"])
            self.assertFalse(any(c.isdigit() for c in party["displayName"]))
            self.assertEqual(party["displayName"], accounts[party["partyKey"]]["displayName"])
            self.assertEqual("synthetic-only", party["syntheticProvenance"])
            if party["partyType"] == "person":
                self.assertEqual(f"{party['firstName']} {party['lastName']}", party["displayName"])
                self.assertTrue(party["email"].endswith("@example.test"))
            else:
                self.assertNotIn("firstName", party)
                self.assertIsNone(party["email"])
        for contact in self.rows("salesforce/contact.jsonl"):
            party = parties[contact["partyKey"]]
            for field in ("firstName", "lastName", "displayName", "email"):
                self.assertEqual(party[field], contact[field])
        for bp in self.rows(BP):
            if bp["bpRole"] == "Customer":
                self.assertEqual(parties[bp["partyKey"]]["displayName"], bp["displayName"])
        bps = {r["sourceKey"]: r for r in self.rows(BP)}
        for supplier in self.rows("sap_plan_b/supplier.jsonl"):
            self.assertEqual(supplier["displayName"], bps[supplier["bpSourceKey"]]["displayName"])

    def test_natural_names_and_marker_corruption_rejected_after_rehash(self) -> None:
        self.params = replace(self.params, catalog_profile=DEFAULT_CATALOG_PROFILE,
                              identity_profile=NATURAL_IDENTITY_PROFILE)
        self.generate_small()
        for path, field, value in (
            ("salesforce/contact.jsonl", "firstName", "Trial"),
            ("salesforce/contact.jsonl", "displayName", "Synthetic Customer00001"),
            ("salesforce/account.jsonl", "displayName", "Trial marker account"),
            (BP, "displayName", "Other Company"),
            ("sap_plan_b/supplier.jsonl", "displayName", "Other Supplier"),
            (PARTY, "identityProfile", "unmarked"),
        ):
            with self.subTest(path=path, field=field):
                original = self.rows(path)
                rows = copy.deepcopy(original)
                rows[0][field] = value
                self.corrupt({path: rows})
                try:
                    self.assert_semantic_rejection("Natural synthetic identity|crosswalk mismatch")
                finally:
                    self.corrupt({path: original})

    def test_smallest_population_and_malformed_export_fail_explicitly(self) -> None:
        generate_dataset(replace(self.params, customer_count=2, order_count=3))
        self.assertEqual("validated", validate_dataset(self.output)["status"])
        self.assertEqual(1, self.manifest()["populationCounts"]["fanCustomerParties"])
        self.assertEqual(1, self.manifest()["populationCounts"]["businessCustomerParties"])
        self.assertEqual({"fan-purchase", "hospitality-b2b"}, {r["journey"] for r in self.rows(ORDER)})
        (self.output / "manifest.json").write_text("{", encoding="utf-8")
        self.assert_semantic_rejection("Invalid export structure")


if __name__ == "__main__":
    unittest.main()
