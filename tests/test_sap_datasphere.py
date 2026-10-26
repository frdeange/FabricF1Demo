from __future__ import annotations

import copy
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from scripts.volume_fixture import GenerationParameters, generate_dataset
from sources.sap.datasphere import (
    OBJECTS,
    SOURCE_SYSTEM,
    _build,
    _replay,
    generate_package,
    main,
    validate_package,
)
from sources.sap.fixture import PackageValidationError, _index_rows, _load_fixture, _validate_relationships


class DataspherePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = tempfile.TemporaryDirectory(prefix="f1-datasphere-test-")
        cls.root = Path(cls.directory.name)
        cls.fixture = cls.root / "fixture"
        generate_dataset(GenerationParameters(
            cls.fixture, customer_count=30, order_count=60, identity_profile="natural-v1",
        ))
        cls.source, cls.records = _load_fixture(cls.fixture)
        cls.files, cls.manifest = _build(cls.fixture)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.directory.cleanup()

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="package-", dir=self.root)
        self.addCleanup(directory.cleanup)
        self.test_root = Path(directory.name)
        self.package = self.test_root / "package"
        self.package.mkdir()
        for relative_path, payload in self.files.items():
            destination = self.package / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)

    def test_actual_parquet_metadata_and_initial_delta_layout(self) -> None:
        self.assertFalse(self.manifest["native_bps_ready"])
        self.assertFalse(self.manifest["native_mirroring_ready"])
        self.assertEqual(0, self.manifest["network_operations"])
        self.assertEqual(self.source["datasetDigestSha256"], self.manifest["source_dataset_digest_sha256"])
        contract = json.loads(self.files["contract.json"])
        batches = json.loads(self.files["batches.json"])
        self.assertEqual(["initial", "delta"], [batch["label"] for batch in batches])
        self.assertEqual(8, len(contract["objects"]))
        self.assertEqual(
            "synthetic-transport-schema-index-not-SAP-DDIC",
            contract["auxiliary_objects"]["DD03ND"]["coverage"],
        )
        self.assertFalse(contract["native_bps_ready"])
        self.assertIn("not SAP DDIC datatype mappings", contract["auxiliary_objects"]["DD03ND"]["mapping"])
        for name, spec in contract["objects"].items():
            root = self.package / "datasphere" / SOURCE_SYSTEM / name
            metadata = json.loads((root / ".sap.partfile.metadata").read_bytes())
            self.assertEqual(3, metadata["version"])
            self.assertEqual("PARQUET", metadata["format"])
            self.assertEqual(
                {"sourceSystem", "sourceTenant", "sourceEntity", "sourceKey"},
                {column["name"] for column in metadata["columns"] if column.get("primaryKey")},
            )
            self.assertEqual("custom-f1-simulation-not-standard-sap-cds", spec["coverage"])
            self.assertEqual(b"", (root / "initial" / "_SUCCESS").read_bytes())
            self.assertEqual(
                (root / ".sap.partfile.metadata").read_bytes(),
                (root / "delta" / ".sap.partfile.metadata").read_bytes(),
            )
            initial_path = next((root / "initial").glob("*.parquet"))
            self.assertEqual(b"PAR1", initial_path.read_bytes()[:4])
            parquet = pq.ParquetFile(initial_path)
            self.assertEqual(
                pa.decimal128(20, 0),
                parquet.schema_arrow.field("__sequence_number").type,
            )
            self.assertEqual("SNAPPY", parquet.metadata.row_group(0).column(0).compression)
            table = parquet.read()
            self.assertEqual({"L"}, set(table.column("__operation_type").to_pylist()))
            self.assertTrue(all(value is None for value in table.column("__sequence_number").to_pylist()))

        delta_objects = batches[1]["objects"]
        self.assertEqual(
            {OBJECTS[f"sap_plan_b/{stem}.jsonl"] for stem in
             ("sap_document", "sap_document_line", "document_link")},
            set(delta_objects),
        )
        for info in delta_objects.values():
            rows = pq.read_table(self.package / info["file"]).to_pylist()
            self.assertTrue(rows)
            self.assertTrue(all(row["__operation_type"] == "U" for row in rows))
        self.assertEqual("validated", validate_package(self.package, self.fixture)["status"])

    def test_dd03nd_projection_covers_exact_transport_fields_without_native_claim(self) -> None:
        contract = json.loads(self.files["contract.json"])
        batches = json.loads(self.files["batches.json"])
        spec = contract["auxiliary_objects"]["DD03ND"]
        self.assertEqual(["STRUCOBJN", "FIELDNAME"], spec["keys"])
        dd03nd_metadata = json.loads(
            self.files["datasphere/F1_PLAN_B/DD03ND/.sap.partfile.metadata"],
        )
        dd03nd_keys = {
            column["name"] for column in dd03nd_metadata["columns"]
            if column.get("primaryKey")
        }
        self.assertEqual(set(spec["keys"]), dd03nd_keys)
        self.assertTrue(all(
            not column["nullable"] for column in dd03nd_metadata["columns"]
            if column["name"] in spec["keys"]
        ))
        self.assertEqual(
            set(OBJECTS.values()),
            {row["STRUCOBJN"] for row in pq.read_table(
                self.package / batches[0]["objects"]["DD03ND"]["file"],
            ).to_pylist()},
        )
        info = batches[0]["objects"]["DD03ND"]
        table = pq.read_table(self.package / info["file"])
        self.assertEqual(info["loads"], table.num_rows)
        self.assertEqual({"L"}, set(table.column("__operation_type").to_pylist()))
        self.assertEqual({}, batches[1]["objects"].get("DD03ND", {}))
        self.assertEqual(
            sum(len(obj["fields"]) + 3 for obj in contract["objects"].values()),
            table.num_rows,
        )
        by_table_field = {
            (row["STRUCOBJN"], row["FIELDNAME"]): row
            for row in table.to_pylist()
        }
        for object_name, obj in contract["objects"].items():
            self.assertIn((object_name, "__timestamp"), by_table_field)
            for field in obj["fields"]:
                row = by_table_field[(object_name, field["name"])]
                self.assertEqual(
                    "DECIMAL" if field["encoding"] == "integer" else "NVARCHAR",
                    row["DATATYPE"],
                )
                self.assertEqual(0, row["DECIMALS"])

    def test_replay_preserves_exact_keys_finances_crosswalks_and_credit_links(self) -> None:
        replay = _replay(self.package)
        self.assertEqual(_index_rows(self.records), _index_rows(replay))
        source_docs = self.records["sap_plan_b/sap_document.jsonl"]
        replay_docs = replay["sap_plan_b/sap_document.jsonl"]
        for document_type in ("customer_invoice", "customer_credit_memo", "supplier_invoice"):
            self.assertEqual(
                sum(row["amountMinor"] for row in source_docs if row["documentType"] == document_type),
                sum(row["amountMinor"] for row in replay_docs if row["documentType"] == document_type),
            )
        self.assertTrue(all(type(row["amountMinor"]) is int for row in replay_docs))
        self.assertEqual(self.source["reconciliation"], self.manifest["financial_reconciliation"])

    def test_determinism_idempotence_and_separate_output(self) -> None:
        other = self.test_root / "other"
        self.assertEqual("generated", generate_package(self.fixture, other)["status"])
        self.assertEqual(
            self.files,
            {path.relative_to(other).as_posix(): path.read_bytes()
             for path in other.rglob("*") if path.is_file()},
        )
        self.assertEqual("no-op-verified", generate_package(
            self.fixture, other, if_exists="verify-noop",
        )["status"])
        with self.assertRaises(FileExistsError):
            generate_package(self.fixture, other)
        with self.assertRaisesRegex(ValueError, "separate"):
            generate_package(self.fixture, self.fixture / "output")
        self.assertEqual(0, len(list(other.parent.glob(".sap-stage-*"))))

    def test_delete_operation_schema_and_rehashed_corruption_are_rejected(self) -> None:
        batches = json.loads(self.files["batches.json"])
        part = self.package / next(iter(batches[1]["objects"].values()))["file"]
        table = pq.read_table(part)
        operations = pa.array(["X"] * len(table), type=pa.string())
        mutated = table.set_column(0, table.schema.field(0), operations)
        pq.write_table(mutated, part, compression="snappy", use_dictionary=False)
        with self.assertRaisesRegex(PackageValidationError, "operation/sequence/timestamp"):
            _replay(self.package)
        manifest = copy.deepcopy(self.manifest)
        relative = part.relative_to(self.package).as_posix()
        manifest["files"][relative]["sha256"] = hashlib.sha256(part.read_bytes()).hexdigest()
        manifest["files"][relative]["size_bytes"] = part.stat().st_size
        (self.package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(FileExistsError):
            validate_package(self.package, self.fixture)
        with self.assertRaises(FileExistsError):
            generate_package(self.fixture, self.package, if_exists="verify-noop")

    def test_cli_requires_fixture_anchor_and_reports_validation(self) -> None:
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0, main([
                "validate", "--fixture-path", str(self.fixture), "--output-path", str(self.package),
            ]))
        self.assertEqual("validated", json.loads(output.getvalue())["status"])

    def test_supplier_partner_and_invoice_line_cross_references_are_checked(self) -> None:
        changed = copy.deepcopy(self.records)
        invoice = next(row for row in changed["sap_plan_b/sap_document.jsonl"]
                       if row["documentType"] == "supplier_invoice")
        other = next(row for row in changed["sap_plan_b/supplier.jsonl"]
                     if row["sourceKey"] != invoice["supplierSourceKey"])
        invoice["partnerSourceKey"] = other["bpSourceKey"]
        with self.assertRaisesRegex(PackageValidationError, "Supplier invoice"):
            _validate_relationships(_index_rows(changed), self.source["reconciliation"])
        changed = copy.deepcopy(self.records)
        cost = changed["sap_plan_b/supplier_cost.jsonl"][0]
        other_line = next(row for row in changed["sap_plan_b/sap_document_line.jsonl"]
                          if row["documentSourceKey"] != cost["documentSourceKey"])
        cost["documentLineSourceKey"] = other_line["sourceKey"]
        with self.assertRaisesRegex(PackageValidationError, "Supplier cost"):
            _validate_relationships(_index_rows(changed), self.source["reconciliation"])


if __name__ == "__main__":
    unittest.main()
