from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from collections import Counter
from dataclasses import replace
from pathlib import Path

from scripts.volume_fixture import (
    DEMO_DATA_PROFILE,
    FILE_SPECS,
    NATURAL_IDENTITY_PROFILE,
    GenerationParameters,
    ValidationError,
    build_export_records,
    generate_dataset,
    validate_dataset,
)
from sources.oracle.seed import build_seed_sql


def _rehash(output: Path) -> dict:
    manifest = json.loads((output / "manifest.json").read_bytes())
    for entry in manifest["files"]:
        payload = (output / entry["path"]).read_bytes()
        entry.update(recordCount=len(payload.splitlines()), sizeBytes=len(payload),
                     sha256=hashlib.sha256(payload).hexdigest())
    digest_input = {
        "namespace": manifest["namespace"], "parameters": manifest["parameters"],
        "files": [{k: entry[k] for k in ("path", "recordCount", "sha256")} for entry in manifest["files"]],
    }
    manifest["datasetDigestSha256"] = hashlib.sha256(
        json.dumps(digest_input, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return manifest


class DemoFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="bounded-demo-test-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.output = self.root / "demo"
        self.params = GenerationParameters(
            self.output, customer_count=430, order_count=1500,
            data_profile=DEMO_DATA_PROFILE, identity_profile=NATURAL_IDENTITY_PROFILE,
        )

    def test_complete_demo_budget_roles_and_relationships(self) -> None:
        generate_dataset(self.params)
        result = validate_dataset(self.output)
        self.assertEqual((430, 400, 30, 1500), (
            result["customerCount"], result["fanCustomerCount"], result["businessCustomerCount"],
            result["orderCount"],
        ))
        manifest = json.loads((self.output / "manifest.json").read_bytes())
        plan = manifest["crmDemoPlan"]
        self.assertEqual((1668, 120, 1788, 212, 2000), (
            plan["logicalSelectedRows"], plan["sharedAuxiliaryReserveRows"],
            plan["plannedRowsIncludingReserve"], plan["unassignedHeadroomRows"], plan["recordLimit"],
        ))
        self.assertIsNone(plan["physicalRows"])
        self.assertIsNone(plan["physicalStorageBytes"])
        self.assertTrue(plan["loadStatus"].startswith("blocked-"))
        expected = {
            "account": 438, "contact": 514, "campaign": 12, "consent": 400,
            "campaign_touch": 120, "opportunity": 120, "case": 40,
            "sponsorship_agreement": 12, "sponsorship_commitment": 12,
        }
        records, _ = build_export_records(self.params)
        for entity, count in expected.items():
            path = f"salesforce/{entity}.jsonl"
            self.assertEqual(count, plan["families"][path]["selectedCount"])
            source_rows = {r["sourceKey"]: r for r in records[path]}
            self.assertTrue(set(plan["families"][path]["sourceKeys"]) <= source_rows.keys())
        parties = {r["partyKey"]: r for r in records["operational/party.jsonl"]}
        self.assertEqual(438, len(parties))
        contacts = records["salesforce/contact.jsonl"]
        self.assertEqual(Counter({"buyer": 38, "admin": 38, "billing": 38}),
                         Counter(c["contactRole"] for c in contacts if "contactRole" in c))
        for contact in contacts:
            if "contactRole" in contact:
                self.assertEqual("organization", parties[contact["partyKey"]]["partyType"])
                self.assertIsNone(contact["canonicalKey"])
                self.assertIsNone(contact["canonicalEntity"])
                self.assertTrue(contact["email"].endswith("@example.test"))
                self.assertEqual(f"{contact['firstName']} {contact['lastName']}", contact["displayName"])
        for case in records["salesforce/case.jsonl"]:
            if parties[case["partyKey"]]["partyType"] == "organization":
                self.assertIsNone(case["contactSourceKey"])
                self.assertEqual("organization-account-no-person-contact", case["contactNullReason"])
        self.assertEqual({r["eventKey"] for r in records["oracle/oracle_event.jsonl"]},
                         {r["eventKey"] for r in records["salesforce/case.jsonl"]})
        self.assertEqual({"F1_EVENT": 12, "F1_ZONE": 96, "F1_PRODUCT": 288,
                          "F1_PRICE": 1152, "F1_BUNDLE_COMPONENT": 144}, build_seed_sql(self.output)[1])
        for path in ("salesforce/campaign_touch.jsonl", "salesforce/opportunity.jsonl"):
            selected = set(plan["families"][path]["sourceKeys"])
            self.assertEqual(Counter({r["eventKey"]: 10 for r in records["oracle/oracle_event.jsonl"]}),
                             Counter(r["eventKey"] for r in records[path] if r["sourceKey"] in selected))

    def test_shared_master_identity_and_names_but_disjoint_transaction_facts(self) -> None:
        demo, demo_manifest = build_export_records(self.params)
        volume_params = replace(self.params, data_profile="volume-v1", customer_count=10000, order_count=36)
        volume, _ = build_export_records(volume_params)
        self.assertNotEqual(self.params.namespace, volume_params.namespace)
        self.assertEqual(self.params.master_key_token, volume_params.key_token)
        for path in ("operational/party.jsonl", "salesforce/account.jsonl", "salesforce/contact.jsonl"):
            originals = {r["sourceKey"]: r for r in volume[path]}
            for row in demo[path]:
                if row.get("contactRole"):
                    self.assertNotIn(row["sourceKey"], originals)
                    continue
                original = originals[row["sourceKey"]]
                for field in ("sourceSystem", "sourceTenant", "sourceEntity", "sourceKey",
                              "canonicalKey", "displayName", "email", "partyKey"):
                    self.assertEqual(original.get(field), row.get(field), (path, field))
                self.assertEqual(original.get("sourceReference"), row.get("sourceReference"))
        for path in FILE_SPECS:
            if path in {"operational/party.jsonl", "salesforce/account.jsonl", "salesforce/contact.jsonl"}:
                continue
            old_ids = {tuple(r[k] for k in ("sourceSystem", "sourceTenant", "sourceEntity", "sourceKey"))
                       for r in volume[path]}
            self.assertTrue(old_ids.isdisjoint(
                tuple(r[k] for k in ("sourceSystem", "sourceTenant", "sourceEntity", "sourceKey"))
                for r in demo[path]), path)
        self.assertEqual(438, len(demo_manifest["crmDemoPlan"]["masterSelection"]["crosswalk"]))

    def test_determinism_and_collision_protection(self) -> None:
        first = generate_dataset(self.params)
        self.assertEqual("generated", first["status"])
        self.assertEqual("no-op-verified", generate_dataset(replace(self.params, if_exists="verify-noop"))["status"])
        other = self.root / "again"
        generate_dataset(replace(self.params, output_path=other))
        self.assertEqual(
            {p.relative_to(self.output): p.read_bytes() for p in self.output.rglob("*") if p.is_file()},
            {p.relative_to(other): p.read_bytes() for p in other.rglob("*") if p.is_file()},
        )
        with self.assertRaises(FileExistsError):
            generate_dataset(replace(self.params, seed="other", if_exists="verify-noop"))
        for changes in ({"customer_count": 431}, {"order_count": 1499},
                        {"identity_profile": "baseline-v1"}, {"catalog_profile": "single-event-v1"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                generate_dataset(replace(self.params, output_path=self.root / "invalid", **changes))
            self.assertFalse((self.root / "invalid").exists())

    def test_semantic_rejection_with_refreshed_hashes_and_budget_metadata(self) -> None:
        generate_dataset(self.params)
        manifest = _rehash(self.output)
        original_manifest = copy.deepcopy(manifest)
        for field, value in (("logicalSelectedRows", 952), ("physicalRows", 1668),
                             ("loadStatus", "ready"), ("sharedAuxiliaryReserveRows", 0)):
            with self.subTest(field=field):
                manifest = copy.deepcopy(original_manifest)
                manifest["crmDemoPlan"][field] = value
                (self.output / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaisesRegex(ValidationError, "CRM demo selection"):
                    validate_dataset(self.output)
        (self.output / "manifest.json").write_text(json.dumps(original_manifest), encoding="utf-8")
        path = self.output / "salesforce" / "contact.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        next(r for r in rows if r.get("contactRole") == "billing")["contactRole"] = "buyer"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        (self.output / "manifest.json").write_text(json.dumps(_rehash(self.output)), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "B2B interlocutor"):
            validate_dataset(self.output)

    def test_volume_canonical_order_collision_rejected_even_with_all_references_rewired(self) -> None:
        generate_dataset(self.params)
        path = self.output / "operational" / "commercial_order.jsonl"
        old_key = json.loads(path.read_text().splitlines()[0])["orderKey"]
        colliding_key = f"ORD-{self.params.master_key_token}-000001"

        def replace_reference(value):
            if isinstance(value, dict):
                return {key: replace_reference(item) for key, item in value.items()}
            if isinstance(value, list):
                return [replace_reference(item) for item in value]
            return colliding_key if value == old_key else value

        for relative_path in FILE_SPECS:
            path = self.output / relative_path
            rows = [replace_reference(json.loads(line)) for line in path.read_text().splitlines()]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        (self.output / "manifest.json").write_text(json.dumps(_rehash(self.output)), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "wrong canonical/row identity domain"):
            validate_dataset(self.output)


if __name__ == "__main__":
    unittest.main()
