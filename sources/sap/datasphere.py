"""Datasphere-like local transport; see THIRD-PARTY-NOTICES.txt for attribution."""
from __future__ import annotations

import argparse
import json
import tempfile
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from sources.sap.fixture import (
    SAP_FILES,
    PackageValidationError,
    _identity,
    _index_rows,
    _json_bytes,
    _load_fixture,
    _paths_overlap,
    _sha256,
    _validate_relationships,
    _verify_existing_noop,
)


REFERENCE = (
    "https://github.com/fredgis/FabricHubDemo/blob/"
    "5ad08f4c3d6352408de84a96796b4bfdf393b23f/sources/sap/datasphere.py"
)
SOURCE_SYSTEM = "F1_PLAN_B"
DD03ND_NAME = "DD03ND"
KEY_FIELDS = ("sourceSystem", "sourceTenant", "sourceEntity", "sourceKey")
TECHNICAL_FIELDS = ("__operation_type", "__sequence_number", "__timestamp")
OBJECTS = {
    path: "ZF1_" + Path(path).stem.upper()
    for path in SAP_FILES
}
FORMAT = "f1-sap-plan-b-datasphere-like-v1"


def _utc(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
        raise PackageValidationError("Extraction timestamps must be UTC.")
    return stamp


def _encode(value: Any, encoding: str) -> Any:
    if value is None:
        return None
    if encoding == "integer":
        if type(value) is not int or abs(value) >= 10**20:
            raise PackageValidationError("Integer exceeds exact DECIMAL(20,0) transport range.")
        return Decimal(value)
    if encoding in {"json", "boolean"}:
        return _json_bytes(value).decode("utf-8")
    return value


def _fields(
    rows: list[dict[str, Any]], key_fields: tuple[str, ...] = KEY_FIELDS,
) -> list[dict[str, Any]]:
    if not rows:
        raise PackageValidationError("A source object needs rows to establish its local schema.")
    result = []
    for name in sorted({name for row in rows for name in row}):
        if name.startswith("__"):
            raise PackageValidationError("Source field collides with a technical column.")
        values = [row[name] for row in rows if row.get(name) is not None]
        types = {type(value) for value in values}
        if types <= {str}:
            encoding = "text"
        elif types == {int}:
            encoding = "integer"
        elif types == {bool}:
            encoding = "boolean"
        elif types <= {dict, list}:
            encoding = "json"
        else:
            raise PackageValidationError(f"Unsupported or mixed source types for {name}: {types}.")
        required = all(name in row for row in rows)
        if not required and any(name in row and row[name] is None for row in rows):
            raise PackageValidationError(f"Ambiguous absent/null optional source field: {name}.")
        encoded = [_encode(value, encoding) for value in values]
        result.append({
            "name": name,
            "encoding": encoding,
            "key": name in key_fields,
            "required": required,
            "length": max([1] + [len(value) for value in encoded if isinstance(value, str)]),
        })
    return result


def _schema(fields: list[dict[str, Any]]) -> pa.Schema:
    return pa.schema([
        pa.field("__operation_type", pa.string()),
        pa.field("__sequence_number", pa.decimal128(20, 0)),
        pa.field("__timestamp", pa.timestamp("us", tz="UTC")),
        *[
            pa.field(
                field["name"],
                pa.decimal128(20, 0) if field["encoding"] == "integer" else pa.string(),
                nullable=not field["key"],
            )
            for field in fields
        ],
    ])


def _metadata(object_name: str, fields: list[dict[str, Any]]) -> bytes:
    columns = []
    for name, data_type, template in (
        ("__operation_type", {"dataType": "NVARCHAR", "length": 1}, "string"),
        ("__sequence_number", {"dataType": "DECIMAL", "precision": 20, "scale": 0}, "uint64"),
        ("__timestamp", {"dataType": "TIMESTAMP"}, "timestamp"),
    ):
        columns.append({
            "name": name, **data_type, "nullable": True,
            "properties": [
                {"namespace": "com.sap.vflow", "name": "vtype-template", "value": template},
                {"namespace": "com.sap.rms", "name": "semanticType", "value": "_change_mode"},
            ],
        })
    for field in fields:
        integer = field["encoding"] == "integer"
        column = {
            "name": field["name"],
            "nullable": not field["key"],
            **(
                {"dataType": "DECIMAL", "precision": 20, "scale": 0}
                if integer else {"dataType": "NVARCHAR", "length": field["length"]}
            ),
            "properties": [{
                "namespace": "com.sap.vflow", "name": "vtype-template",
                "value": "decimal" if integer else "string",
            }],
        }
        if field["key"]:
            column["primaryKey"] = True
        columns.append(column)
    return _json_bytes({
        "version": 3, "format": "PARQUET",
        "properties": [
            {"namespace": "com.sap.rms", "name": "loadType", "value": "REPLICATE"},
            {"namespace": "com.sap.rms", "name": "replicationTaskID",
             "value": uuid.uuid5(uuid.NAMESPACE_URL, f"f1-plan-b-v1:{object_name}").hex.upper()},
            {"namespace": "com.sap.rms", "name": "groupDeltaFilesBy", "value": "NONE"},
        ],
        "columns": columns,
    }, pretty=True)


def _dd03nd_rows(objects: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for object_name, spec in sorted(objects.items()):
        rows.extend((
            {
                "STRUCOBJN": object_name,
                "FIELDNAME": "__operation_type",
                "DATATYPE": "NVARCHAR",
                "LENG": 1,
                "DECIMALS": 0,
            },
            {
                "STRUCOBJN": object_name,
                "FIELDNAME": "__sequence_number",
                "DATATYPE": "DECIMAL",
                "LENG": 20,
                "DECIMALS": 0,
            },
            {
                "STRUCOBJN": object_name,
                "FIELDNAME": "__timestamp",
                "DATATYPE": "TIMESTAMP",
                "LENG": 8,
                "DECIMALS": 6,
            },
        ))
        for field in spec["fields"]:
            integer = field["encoding"] == "integer"
            rows.append({
                "STRUCOBJN": object_name,
                "FIELDNAME": field["name"],
                "DATATYPE": "DECIMAL" if integer else "NVARCHAR",
                "LENG": 20 if integer else field["length"],
                "DECIMALS": 0,
            })
    return rows


def _parquet(
    rows: list[dict[str, Any]], fields: list[dict[str, Any]], operation: str, stamp: str,
) -> bytes:
    values = [
        {
            "__operation_type": operation,
            "__sequence_number": None,
            "__timestamp": _utc(stamp),
            **{field["name"]: _encode(row.get(field["name"]), field["encoding"]) for field in fields},
        }
        for row in rows
    ]
    table = pa.Table.from_pylist(values, schema=_schema(fields))
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, compression="snappy", version="2.6", use_dictionary=False)
    return sink.getvalue().to_pybytes()


def _snapshots(
    records: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    credit_documents = {
        row["erpDocumentKey"] for row in records["sap_plan_b/sap_document.jsonl"]
        if row["documentType"] == "customer_credit_memo"
    }
    initial, delta = {}, {}
    for path in SAP_FILES:
        ordered = sorted(records[path], key=_identity)
        initial[path] = [row for row in ordered if row.get("erpDocumentKey") not in credit_documents]
        delta[path] = [row for row in ordered if row.get("erpDocumentKey") in credit_documents]
    return initial, delta


def _build(fixture_path: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    source, records = _load_fixture(fixture_path)
    _validate_relationships(_index_rows(records), source["reconciliation"])
    initial, delta = _snapshots(records)
    files = {}
    objects = {}
    batches = []
    # These are staged demo checkpoints, not a reconstruction of historical source states.
    for label, snapshot, operation, stamp_field in (
        ("initial", initial, "L", "asOf"),
        ("delta", delta, "U", "publishedAt"),
    ):
        batch = {"label": label, "timestamp": source[stamp_field], "objects": {}}
        for path, object_name in OBJECTS.items():
            fields = _fields(records[path])
            folder = f"datasphere/{SOURCE_SYSTEM}/{object_name}"
            if label == "initial":
                objects[object_name] = {
                    "fixturePath": path, "keys": list(KEY_FIELDS),
                    "coverage": "custom-f1-simulation-not-standard-sap-cds",
                    "financialDeletesAllowed": False, "fields": fields,
                }
                for directory in ("", "/initial", "/delta"):
                    files[f"{folder}{directory}/.sap.partfile.metadata"] = _metadata(object_name, fields)
            if label == "delta" and not snapshot[path]:
                continue
            payload = _parquet(snapshot[path], fields, operation, source[stamp_field])
            token = _sha256(payload)
            part = (
                f"part-{token[:33]}.parquet" if label == "initial"
                else f"part-{_utc(source[stamp_field]):%Y%m%d%H%M%S}-{token[:24]}-01.parquet"
            )
            relative_path = f"{folder}/{label}/{part}"
            files[relative_path] = payload
            if label == "initial":
                files[f"{folder}/initial/_SUCCESS"] = b""
            batch["objects"][object_name] = {
                "file": relative_path, "loads": len(snapshot[path]) if operation == "L" else 0,
                "upserts": len(snapshot[path]) if operation == "U" else 0, "deletes": 0,
            }
        batches.append(batch)
    dd03nd_rows = _dd03nd_rows(objects)
    dd03nd_fields = _fields(dd03nd_rows, ("STRUCOBJN", "FIELDNAME"))
    dd03nd_folder = f"datasphere/{SOURCE_SYSTEM}/{DD03ND_NAME}"
    for directory in ("", "/initial", "/delta"):
        files[f"{dd03nd_folder}{directory}/.sap.partfile.metadata"] = _metadata(
            DD03ND_NAME, dd03nd_fields,
        )
    dd03nd_data = _parquet(dd03nd_rows, dd03nd_fields, "L", source["asOf"])
    dd03nd_file = f"{dd03nd_folder}/initial/part-{_sha256(dd03nd_data)[:33]}.parquet"
    files[dd03nd_file] = dd03nd_data
    files[f"{dd03nd_folder}/initial/_SUCCESS"] = b""
    batches[0]["objects"][DD03ND_NAME] = {
        "file": dd03nd_file, "loads": len(dd03nd_rows), "upserts": 0, "deletes": 0,
    }
    files["contract.json"] = _json_bytes({
        "version": 1,
        "objects": objects,
        "auxiliary_objects": {
            DD03ND_NAME: {
                "fixturePath": None,
                "keys": ["STRUCOBJN", "FIELDNAME"],
                "coverage": "synthetic-transport-schema-index-not-SAP-DDIC",
                "fields": dd03nd_fields,
                "mapping": (
                    "Derived from the local Parquet transport schema only: "
                    "NVARCHAR uses maximum encoded character length, DECIMAL uses precision 20 "
                    "and scale 0, TIMESTAMP uses physical width 8 and microsecond precision 6. "
                    "These values are not SAP DDIC datatype mappings."
                ),
            },
        },
        "native_bps_ready": False,
        "scope": "Custom F1 source projections; not an activated native SAP/BPS contract.",
        "sequence": "Null decimal(20,0), as in the pinned public writer; no CDC ordering guarantee.",
        "dd03nd_warning": (
            "The synthetic DD03ND-shaped projection is not sourced from SAP DDIC and "
            "does not establish native BPS compatibility."
        ),
    }, pretty=True)
    files["batches.json"] = _json_bytes(batches, pretty=True)
    files["fixture-manifest.json"] = _json_bytes(source, pretty=True)
    files["THIRD-PARTY-NOTICES.txt"] = Path(__file__).with_name("THIRD-PARTY-NOTICES.txt").read_bytes()
    manifest = {
        "format": FORMAT, "synthetic": True, "sap_plan": "B",
        "native_bps_ready": False, "native_mirroring_ready": False, "network_operations": 0,
        "reference": REFERENCE, "pyarrow_version": pa.__version__,
        "source_dataset_digest_sha256": source["datasetDigestSha256"],
        "publication_key": source["publicationKey"], "namespace": source["namespace"],
        "initial_as_of": source["asOf"], "final_as_of": source["publishedAt"],
        "scenario": "Initial snapshot excludes credit documents/lines/links; delta upserts them.",
        "replay": "Load initial L files, then the U credit batch. X/deletes are prohibited.",
        "publication_warning": "Local staged checkpoints, not historical CDC or a new canonical publication.",
        "financial_reconciliation": source["reconciliation"],
        "files": {
            path: {"sha256": _sha256(data), "size_bytes": len(data)}
            for path, data in sorted(files.items())
        },
    }
    manifest["package_digest_sha256"] = _sha256(_json_bytes(manifest))
    files["manifest.json"] = _json_bytes(manifest, pretty=True)
    return files, manifest


def _replay(package_path: Path) -> dict[str, list[dict[str, Any]]]:
    contract = json.loads((package_path / "contract.json").read_bytes())
    batches = json.loads((package_path / "batches.json").read_bytes())
    object_specs = {**contract["objects"], **contract.get("auxiliary_objects", {})}
    states = {name: {} for name in object_specs}
    for batch in batches:
        for name, info in batch["objects"].items():
            spec = object_specs[name]
            fields = spec["fields"]
            parquet_path = package_path / info["file"]
            table = pq.read_table(parquet_path)
            if not table.schema.equals(_schema(fields), check_metadata=True):
                raise PackageValidationError(f"Parquet schema differs from contract for {name}.")
            parquet_metadata = pq.ParquetFile(parquet_path).metadata
            if any(
                parquet_metadata.row_group(group).column(column).compression != "SNAPPY"
                for group in range(parquet_metadata.num_row_groups)
                for column in range(parquet_metadata.num_columns)
            ):
                raise PackageValidationError(f"Parquet compression must be Snappy for {name}.")
            seen = set()
            for row in table.to_pylist():
                expected_operation = "L" if batch["label"] == "initial" else "U"
                if (
                    row["__operation_type"] != expected_operation
                    or row["__sequence_number"] is not None
                    or row["__timestamp"] != _utc(batch["timestamp"])
                ):
                    raise PackageValidationError(f"Invalid operation/sequence/timestamp for {name}.")
                restored = {}
                for field in fields:
                    value = row[field["name"]]
                    if value is None and not field["required"]:
                        continue
                    if value is not None and field["encoding"] == "integer":
                        value = int(value)
                    elif value is not None and field["encoding"] in {"json", "boolean"}:
                        value = json.loads(value)
                    restored[field["name"]] = value
                identity = (
                    _identity(restored)
                    if spec["fixturePath"] is not None
                    else tuple(restored[key] for key in spec["keys"])
                )
                if any(not isinstance(value, str) or not value for value in identity):
                    raise PackageValidationError(f"Missing source key in {name}.")
                if identity in seen or (expected_operation == "L" and identity in states[name]):
                    raise PackageValidationError(f"Duplicate source key in {name}.")
                seen.add(identity)
                states[name][identity] = restored
    return {
        object_specs[name]["fixturePath"]: list(rows.values())
        for name, rows in states.items()
        if object_specs[name]["fixturePath"] is not None
    }


def validate_package(package_path: Path, fixture_path: Path) -> dict[str, Any]:
    expected, manifest = _build(fixture_path)
    # An authoritative fixture anchor detects rehashed schema, metadata or financial tampering.
    _verify_existing_noop(package_path, expected)
    restored = _replay(package_path)
    _, source_records = _load_fixture(fixture_path)
    if _index_rows(restored) != _index_rows(source_records):
        raise PackageValidationError("Initial/delta replay does not reproduce the source fixture.")
    _validate_relationships(_index_rows(restored), manifest["financial_reconciliation"])
    return {
        "status": "validated", "package_digest_sha256": manifest["package_digest_sha256"],
        "record_count": sum(len(rows) for rows in restored.values()),
        "native_bps_ready": False, "native_mirroring_ready": False,
    }


def generate_package(fixture_path: Path, output_path: Path, *, if_exists: str = "error") -> dict[str, Any]:
    if if_exists not in {"error", "verify-noop"}:
        raise ValueError("if_exists must be error or verify-noop.")
    if _paths_overlap(fixture_path, output_path):
        raise ValueError("Package output must be separate from the source fixture.")
    if output_path.is_symlink():
        raise ValueError("Package output must not be a symlink.")
    files, manifest = _build(fixture_path)
    if output_path.exists():
        if if_exists == "verify-noop":
            validate_package(output_path, fixture_path)
            return {"status": "no-op-verified", "package_digest_sha256": manifest["package_digest_sha256"]}
        raise FileExistsError(f"Output already exists; refusing overwrite: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".sap-stage-", dir=output_path.parent) as staging:
        root = Path(staging) / "package"
        root.mkdir()
        for relative_path, payload in files.items():
            destination = root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(payload)
        report = validate_package(root, fixture_path)
        # Reserve the destination exclusively; never replace a concurrent writer's directory.
        output_path.mkdir()
        try:
            for child in root.iterdir():
                child.rename(output_path / child.name)
        except OSError as exc:
            raise OSError(f"Package publication failed; incomplete output is retained at {output_path}: {exc}") from exc
    return {"status": "generated", "manifest_path": str(output_path / "manifest.json"), **{
        key: value for key, value in report.items() if key != "status"
    }}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or validate local F1 Datasphere-like Parquet packages.")
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("--fixture-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--if-exists", choices=("error", "verify-noop"), default="error")
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            result = generate_package(Path(args.fixture_path), Path(args.output_path), if_exists=args.if_exists)
        else:
            result = validate_package(Path(args.output_path), Path(args.fixture_path))
    except (OSError, ValueError, PackageValidationError, pa.ArrowException) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
