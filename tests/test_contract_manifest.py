from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class CanonicalContractManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contracts = load_json("contracts/canonical-contracts.json")
        cls.manifest = load_json("scenarios/canonical-scenario-manifest.json")

    def test_manifest_covers_every_contract_entity(self) -> None:
        contract_entities = {entity["name"]: entity for entity in self.contracts["entities"]}
        expected_counts = self.manifest["expectedEntityCounts"]

        self.assertEqual(set(contract_entities), set(expected_counts))
        self.assertEqual(len(contract_entities), len(self.contracts["entities"]))
        for name, entity in contract_entities.items():
            with self.subTest(entity=name):
                self.assertTrue(entity["key"])
                self.assertTrue(entity["owner"])
                self.assertTrue(entity["grain"])
                self.assertTrue(entity["states"])
                self.assertTrue(entity["unit"])
                self.assertTrue(entity["timestamps"])
                self.assertTrue(entity["pii"])
                self.assertTrue(entity["operations"])
                self.assertTrue(entity["planA"])
                self.assertTrue(entity["planB"])
                self.assertGreater(expected_counts[name], 0)

    def test_scenario_has_four_complete_and_unique_journeys(self) -> None:
        journeys = self.manifest["journeys"]
        self.assertEqual(
            {
                "fan-purchase",
                "hospitality-b2b",
                "complaint-credit",
                "sponsorship",
            },
            {journey["journeyId"] for journey in journeys},
        )
        self.assertEqual(len(journeys), len({journey["journeyId"] for journey in journeys}))

        for journey in journeys:
            with self.subTest(journey=journey["journeyId"]):
                self.assertTrue(journey["inputs"])
                self.assertTrue(journey["expectedOutputs"])
                self.assertEqual("synthetic-only", journey["inputs"]["dataOrigin"])

    def test_expected_entity_counts_reconcile_by_fixture_and_journey(self) -> None:
        contributions = self.manifest["expectedEntityCountContributions"]
        totals = dict(contributions["referenceInputs"])
        for journey, counts in contributions["journeys"].items():
            self.assertIn(journey, {item["journeyId"] for item in self.manifest["journeys"]})
            for entity, count in counts.items():
                totals[entity] = totals.get(entity, 0) + count

        self.assertEqual(self.manifest["expectedEntityCounts"], totals)
        inputs = self.manifest["referenceInputs"]
        self.assertEqual(len(inputs["drivers"]), contributions["referenceInputs"]["Driver"])
        self.assertEqual(len(inputs["circuitZones"]), contributions["referenceInputs"]["CircuitZone"])
        self.assertEqual(len(inputs["products"]), contributions["referenceInputs"]["Product"])
        self.assertEqual(len(inputs["prices"]), contributions["referenceInputs"]["Price"])
        self.assertEqual(len(inputs["bundleComponents"]), contributions["referenceInputs"]["BundleComponent"])
        self.assertEqual(len(inputs["parties"]), contributions["referenceInputs"]["Party"])
        self.assertEqual(len(self.manifest["erpDocuments"]), self.manifest["expectedEntityCounts"]["ERPDocument"])
        product_keys = {product["productKey"] for product in inputs["products"]}
        self.assertEqual(product_keys, {price["productKey"] for price in inputs["prices"]})
        self.assertTrue(
            all(
                not {"unitPriceMinor", "currency", "taxTreatment"}.intersection(product)
                for product in inputs["products"]
            )
        )
        self.assertTrue(
            all(
                price["recordState"] == "active"
                and price["effectiveFrom"] < price["effectiveTo"]
                and price["currency"] == "USD"
                and price["taxTreatment"] == "not_applicable"
                for price in inputs["prices"]
            )
        )

    def test_all_fixture_data_is_synthetic_and_live_is_not_claimed(self) -> None:
        self.assertEqual("synthetic-only", self.manifest["dataOrigin"])
        self.assertIn("NOT CONNECTED SOURCE DATA", self.manifest["provenanceLabel"])
        self.assertEqual("B", self.manifest["sapPlan"])
        self.assertEqual("unavailable-not-tested", self.manifest["replay"]["liveSession"])
        self.assertEqual(
            {"RACE-EVT-SYN-001", "RACE-EVT-SYN-002"},
            set(self.manifest["replay"]["visibleRaceEventKeysAtPlaybackAt"]),
        )
        self.assertEqual(
            {"RACE-EVT-SYN-003"},
            set(self.manifest["replay"]["hiddenRaceEventKeysAtPlaybackAt"]),
        )

        self.assertEqual("synthetic-only", self.manifest["referenceInputs"]["event"]["dataOrigin"])
        self.assertEqual("synthetic-only", self.manifest["referenceInputs"]["session"]["dataOrigin"])
        self.assertEqual("synthetic-only", self.manifest["referenceInputs"]["sponsorAccount"]["dataOrigin"])
        self.assertEqual("synthetic-only", self.manifest["referenceInputs"]["incident"]["dataOrigin"])
        self.assertTrue(all(record["email"].endswith(".test") for record in self.manifest["referenceInputs"]["parties"] if "email" in record))
        self.assertTrue(
            all("Synthetic" in record["displayName"] for record in self.manifest["referenceInputs"]["drivers"])
        )
        self.assertTrue(all("Synthetic" in record["displayName"] for record in self.manifest["referenceInputs"]["circuitZones"]))
        self.assertTrue(all(document["dataOrigin"] == "synthetic-only" for document in self.manifest["erpDocuments"]))

    def test_replay_as_of_excludes_future_event_and_uses_distinct_clocks(self) -> None:
        replay = self.manifest["replay"]
        visible_at = replay["playbackAt"]
        samples = replay["eventSamples"]

        self.assertEqual(3, self.manifest["expectedEntityCounts"]["RaceEventEnvelope"])
        common_fields = set(self.contracts["commonFields"]["required"])
        self.assertTrue(common_fields.issubset(replay["publication"]))
        self.assertTrue(all(common_fields.issubset(sample) for sample in samples))
        self.assertEqual(replay["publicationKey"], replay["publication"]["publicationKey"])
        self.assertTrue(all(sample["publicationKey"] == replay["publicationKey"] for sample in samples))
        self.assertTrue(all(sample["dataOrigin"] == "synthetic-only" for sample in samples))
        self.assertTrue(all("eventTime" in sample and "ingestedAt" in sample for sample in samples))
        self.assertEqual("2030-06-15T14:02:10Z", samples[-1]["eventTime"])
        self.assertGreater(samples[-1]["eventTime"], visible_at)
        self.assertLessEqual(samples[-1]["ingestedAt"], replay["visibilityAsOf"])
        self.assertLessEqual(replay["publication"]["publishedAt"], replay["visibilityAsOf"])
        visible = [sample["raceEventKey"] for sample in samples if sample["eventTime"] <= visible_at]
        self.assertEqual(replay["visibleRaceEventKeysAtPlaybackAt"], visible)

    def test_financial_reconciliation_keeps_measures_distinct(self) -> None:
        journeys = {journey["journeyId"]: journey["expectedOutputs"] for journey in self.manifest["journeys"]}
        fan = journeys["fan-purchase"]
        hospitality = journeys["hospitality-b2b"]
        complaint = journeys["complaint-credit"]
        sponsor = journeys["sponsorship"]
        totals = self.manifest["reconciliation"]
        documents = self.manifest["erpDocuments"]

        order_gross = fan["orderGrossMinor"] + hospitality["orderGrossMinor"]
        simulated_payments = fan["paymentAmountMinor"] + hospitality["paymentAmountMinor"]
        self.assertEqual(order_gross, totals["commercialOrderGrossMinor"])
        self.assertEqual(simulated_payments, totals["approvedSimulatedPaymentMinor"])
        self.assertEqual(complaint["creditAmountMinor"], totals["scenarioCreditMinor"])
        self.assertEqual(
            order_gross - complaint["creditAmountMinor"],
            totals["commercialOrderNetAfterCreditMinor"],
        )
        by_type = {
            document_type: sum(
                doc["amountMinor"] for doc in documents if doc["documentType"] == document_type
            )
            for document_type in {doc["documentType"] for doc in documents}
        }
        self.assertEqual(by_type["customer_invoice"], totals["postedCustomerInvoiceMinor"])
        self.assertEqual(by_type["customer_credit_memo"], totals["postedCustomerCreditMemoMinor"])
        self.assertEqual(by_type["supplier_invoice"], totals["supplierCostMinor"])
        self.assertEqual(
            hospitality["allocatedCostMinor"] + sponsor["allocatedCostMinor"],
            totals["supplierCostMinor"],
        )
        self.assertEqual(6, len(documents))
        self.assertTrue(
            all(
                doc["lineGrossMinor"] == doc["amountMinor"]
                and doc["lineNetMinor"] + doc["lineTaxMinor"] == doc["lineGrossMinor"]
                and doc["taxTreatment"] == "not_applicable"
                for doc in documents
            )
        )
        self.assertEqual(6, self.manifest["expectedEntityCounts"]["ERPDocument"])
        self.assertEqual(6, self.manifest["expectedEntityCounts"]["ERPDocumentLine"])
        self.assertEqual(6, self.manifest["expectedEntityCounts"]["DocumentLink"])
        self.assertEqual(
            {doc["erpDocumentLineKey"] for doc in documents},
            {f"ERPL-SYN-{index:03}" for index in range(1, 7)},
        )
        self.assertEqual(
            {doc["documentLinkKey"] for doc in documents},
            {
                journey["expectedOutputs"][key]
                for journey in self.manifest["journeys"]
                for key in journey["expectedOutputs"]
                if "LinkKey" in key
            },
        )
        self.assertFalse(sponsor["roiClaimed"])
        self.assertTrue(sponsor["commitmentEvidenceReference"].startswith("synthetic://"))
        self.assertNotEqual(sponsor["contractedMinor"], sponsor["invoicedMinor"])
        self.assertNotEqual(sponsor["invoicedMinor"], sponsor["fulfilledMinor"])

    def test_retry_and_credit_access_contract_are_explicit(self) -> None:
        fan = next(item for item in self.manifest["journeys"] if item["journeyId"] == "fan-purchase")
        complaint = next(
            item for item in self.manifest["journeys"] if item["journeyId"] == "complaint-credit"
        )
        output = fan["expectedOutputs"]
        credit = complaint["expectedOutputs"]

        self.assertTrue(output["retryReturnsSameKeys"])
        self.assertEqual(0, output["additionalOrdersOnRetry"])
        self.assertEqual(0, output["additionalPaymentsOnRetry"])
        self.assertEqual(0, output["additionalEntitlementsOnRetry"])
        self.assertEqual("full-scenario-credit-not-money-refund", credit["creditType"])
        self.assertEqual("revoked", credit["entitlementStateAfterCredit"])

    def test_source_seed_records_have_required_identity_and_unique_upsert_keys(self) -> None:
        source_seed = self.manifest["sourceSeed"]
        self.assertEqual("B", source_seed["sapPlan"])
        self.assertEqual("deterministic-upsert-noop", source_seed["idempotency"]["sameVersionBehavior"])
        self.assertEqual("not-started-conditional", source_seed["adapterQualification"]["sapPlanA"])

        records: list[dict] = []
        for source_system in source_seed["sourceSystems"]:
            self.assertTrue(source_system["schemaLabel"])
            records.extend(source_system["records"])

        self.assertGreater(len(records), 0)

        key_fields = source_seed["idempotency"]["upsertIdentityFields"]
        identities = set()
        canonical_identities = set()
        valid_journeys = {journey["journeyId"] for journey in self.manifest["journeys"]}
        for source_system in source_seed["sourceSystems"]:
            for record in source_system["records"]:
                self.assertEqual(source_system["sourceSystem"], record["sourceSystem"])
                self.assertEqual(source_system["sourceTenant"], record["sourceTenant"])

        for record in records:
            with self.subTest(sourceKey=record["sourceKey"], sourceEntity=record["sourceEntity"]):
                self.assertTrue(record["sourceEntity"])
                self.assertTrue(record["sourceKey"])
                self.assertEqual("seeded", record["recordState"])
                self.assertEqual("synthetic-only", record["syntheticProvenance"])
                self.assertEqual(self.manifest["scenarioId"], record["scenarioId"])
                self.assertEqual(self.manifest["scenarioVersion"], record["scenarioVersion"])
                self.assertEqual(self.manifest["datasetId"], record["datasetId"])
                self.assertEqual("1.0.0", record["schemaVersion"])
                self.assertTrue(record["refs"])
                self.assertTrue(set(record["journeys"]).issubset(valid_journeys))
                identity = tuple(record[field] for field in key_fields)
                self.assertNotIn(identity, identities)
                identities.add(identity)
                canonical_entity = record["canonicalEntity"]
                canonical_key = record["canonicalKey"]
                if canonical_entity is None or canonical_key is None:
                    self.assertIsNone(canonical_entity)
                    self.assertIsNone(canonical_key)
                    self.assertEqual(
                        "source-reference-only-no-canonical-entity",
                        record["mappingStatus"],
                    )
                else:
                    canonical_identity = (
                        record["sourceSystem"],
                        canonical_entity,
                        canonical_key,
                    )
                    self.assertNotIn(canonical_identity, canonical_identities)
                    canonical_identities.add(canonical_identity)

    def test_source_seed_referential_integrity_for_oracle_salesforce_and_sap_plan_b(self) -> None:
        source_seed = self.manifest["sourceSeed"]
        by_system = {
            source_system["sourceSystem"]: source_system["records"]
            for source_system in source_seed["sourceSystems"]
        }

        oracle_records = by_system["oracle"]
        salesforce_records = by_system["salesforce"]
        sap_records = by_system["sap-plan-b-synthetic"]

        oracle_by_key = {record["sourceKey"]: record for record in oracle_records}
        def assert_source_ref(records_by_key: dict, source_key: str, source_entity: str) -> None:
            self.assertIn(source_key, records_by_key)
            self.assertEqual(source_entity, records_by_key[source_key]["sourceEntity"])

        for record in oracle_records:
            refs = record["refs"]
            if record["sourceEntity"] == "OracleCatalogProduct":
                assert_source_ref(oracle_by_key, refs["eventSourceKey"], "OracleEvent")
                if "zoneSourceKey" in refs:
                    assert_source_ref(oracle_by_key, refs["zoneSourceKey"], "OracleCircuitZone")
            if record["sourceEntity"] == "OracleBundleComponent":
                assert_source_ref(oracle_by_key, refs["bundleProductSourceKey"], "OracleCatalogProduct")
                assert_source_ref(oracle_by_key, refs["componentProductSourceKey"], "OracleCatalogProduct")
            if record["sourceEntity"] == "OraclePriceListEntry":
                assert_source_ref(oracle_by_key, refs["eventSourceKey"], "OracleEvent")
                assert_source_ref(oracle_by_key, refs["productSourceKey"], "OracleCatalogProduct")

        salesforce_by_key = {record["sourceKey"]: record for record in salesforce_records}
        for record in salesforce_records:
            refs = record["refs"]
            if record["sourceEntity"] == "Opportunity":
                assert_source_ref(salesforce_by_key, refs["accountSourceKey"], "Account")
            if record["sourceEntity"] == "Case":
                assert_source_ref(salesforce_by_key, refs["contactSourceKey"], "Contact")
                self.assertEqual("ORD-SYN-FAN-001", refs["orderKey"])
            if record["sourceEntity"] == "Sponsorship_Commitment__c":
                assert_source_ref(salesforce_by_key, refs["opportunitySourceKey"], "Opportunity")
                self.assertEqual("illustrative-custom-api-name-unqualified", refs["objectQualification"])

        sap_by_key = {record["sourceKey"]: record for record in sap_records}
        sap_docs = [record for record in sap_records if record["sourceEntity"] == "SAPDocument"]
        sap_lines = [record for record in sap_records if record["sourceEntity"] == "SAPDocumentLine"]
        sap_allocs = [record for record in sap_records if record["sourceEntity"] == "SAPCostAllocation"]
        sap_supplier_costs = [record for record in sap_records if record["sourceEntity"] == "SupplierCost"]
        self.assertEqual(6, len(sap_docs))
        self.assertEqual(6, len(sap_lines))
        self.assertEqual(2, len(sap_allocs))
        self.assertEqual(2, len(sap_supplier_costs))

        for record in sap_docs:
            refs = record["refs"]
            assert_source_ref(sap_by_key, refs["documentLineSourceKey"], "SAPDocumentLine")
            if refs["documentType"] == "supplier_invoice":
                assert_source_ref(sap_by_key, refs["partnerSourceKey"], "Supplier")
                supplier = sap_by_key[refs["partnerSourceKey"]]
                assert_source_ref(sap_by_key, supplier["refs"]["bpSourceKey"], "BusinessPartner")
                self.assertEqual("Supplier", sap_by_key[supplier["refs"]["bpSourceKey"]]["refs"]["bpRole"])
            else:
                assert_source_ref(sap_by_key, refs["partnerSourceKey"], "BusinessPartner")
                self.assertEqual("Customer", sap_by_key[refs["partnerSourceKey"]]["refs"]["bpRole"])
            if refs.get("orderKey"):
                self.assertIn(refs["orderKey"], {"ORD-SYN-FAN-001", "ORD-SYN-HOSP-001"})
        for record in sap_lines:
            refs = record["refs"]
            assert_source_ref(sap_by_key, refs["documentSourceKey"], "SAPDocument")
            self.assertEqual(
                refs["lineNetMinor"] + refs["lineTaxMinor"],
                refs["lineGrossMinor"],
            )
        for record in sap_supplier_costs:
            refs = record["refs"]
            assert_source_ref(sap_by_key, refs["supplierSourceKey"], "Supplier")
            assert_source_ref(sap_by_key, refs["costCenterSourceKey"], "CostCenter")
            assert_source_ref(sap_by_key, refs["documentSourceKey"], "SAPDocument")
            assert_source_ref(sap_by_key, refs["documentLineSourceKey"], "SAPDocumentLine")
            self.assertEqual(refs["amountMinor"], sap_by_key[refs["documentLineSourceKey"]]["refs"]["lineGrossMinor"])
        for record in sap_allocs:
            refs = record["refs"]
            assert_source_ref(sap_by_key, refs["supplierSourceKey"], "Supplier")
            assert_source_ref(sap_by_key, refs["costCenterSourceKey"], "CostCenter")
            assert_source_ref(sap_by_key, refs["supplierCostSourceKey"], "SupplierCost")
            self.assertEqual(refs["supplierCostKey"], sap_by_key[refs["supplierCostSourceKey"]]["canonicalKey"])

    def test_source_seed_is_deterministic_and_run_version_isolated(self) -> None:
        source_seed = self.manifest["sourceSeed"]
        payload = {
            "scenarioId": source_seed["scenarioId"],
            "scenarioVersion": source_seed["scenarioVersion"],
            "datasetId": source_seed["datasetId"],
            "seed": source_seed["seed"],
            "sourceSystems": source_seed["sourceSystems"],
        }
        expected_digest = source_seed["idempotency"]["deterministicRecordDigestSha256"]
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(expected_digest, digest)

        isolation = source_seed["idempotency"]["runVersionIsolation"]
        examples = isolation["examples"]
        self.assertEqual(2, len(examples))
        self.assertNotEqual(examples[0]["namespace"], examples[1]["namespace"])
        for example in examples:
            self.assertIn(example["runVersion"], example["namespace"])
            self.assertEqual(
                isolation["namespaceTemplate"].format(
                    scenarioId=source_seed["scenarioId"],
                    scenarioVersion=source_seed["scenarioVersion"],
                    datasetId=source_seed["datasetId"],
                    runVersion=example["runVersion"],
                ),
                example["namespace"],
            )

    def test_source_seed_excludes_invalid_or_missing_inputs(self) -> None:
        source_seed = self.manifest["sourceSeed"]
        seeded_source_keys = {
            (record["sourceSystem"], record["sourceTenant"], record["sourceKey"])
            for source_system in source_seed["sourceSystems"]
            for record in source_system["records"]
        }
        seeded_records = {
            (record["sourceSystem"], record["sourceTenant"], record["sourceKey"]): record
            for source_system in source_seed["sourceSystems"]
            for record in source_system["records"]
        }
        source_records_by_key = {
            source_system["sourceSystem"]: {
                record["sourceKey"]: record for record in source_system["records"]
            }
            for source_system in source_seed["sourceSystems"]
        }
        for invalid in source_seed["invalidInputScenarios"]:
            with self.subTest(invalid=invalid["id"]):
                self.assertFalse(invalid["representedInSeed"])
                invalid_record = invalid["sourceRecord"]
                identity = (
                    invalid_record["sourceSystem"],
                    invalid_record["sourceTenant"],
                    invalid_record["sourceKey"],
                )
                self.assertNotIn(identity, seeded_source_keys)
                self.assertNotIn(invalid_record["sourceKey"], source_records_by_key[invalid_record["sourceSystem"]])
                self.assertEqual({}, seeded_records.get(identity, {}))

                invalid_refs = invalid_record["refs"]
                if "priceSourceKey" in invalid_refs:
                    self.assertNotIn(invalid_refs["priceSourceKey"], source_records_by_key["oracle"])
                if "accountSourceKey" in invalid_refs:
                    self.assertNotIn(invalid_refs["accountSourceKey"], source_records_by_key["salesforce"])
                if "partnerSourceKey" in invalid_refs:
                    self.assertNotIn(
                        invalid_refs["partnerSourceKey"],
                        source_records_by_key["sap-plan-b-synthetic"],
                    )
                if "costCenterSourceKey" in invalid_refs:
                    self.assertNotIn(
                        invalid_refs["costCenterSourceKey"],
                        source_records_by_key["sap-plan-b-synthetic"],
                    )

        self.assertEqual(
            self.manifest["expectedEntityCounts"]["CommercialOrder"],
            len(
                {
                    journey["expectedOutputs"]["orderKey"]
                    for journey in self.manifest["journeys"]
                    if "orderKey" in journey["expectedOutputs"]
                }
            ),
        )


if __name__ == "__main__":
    unittest.main()
