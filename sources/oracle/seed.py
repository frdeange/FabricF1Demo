from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.volume_fixture import ValidationError, validate_dataset


COMMON_COLUMNS = (
    ("SOURCE_SYSTEM", "sourceSystem", "text"),
    ("SOURCE_TENANT", "sourceTenant", "text"),
    ("SOURCE_ENTITY", "sourceEntity", "text"),
    ("SOURCE_KEY", "sourceKey", "text"),
    ("SOURCE_UPDATED_AT_UTC", "sourceUpdatedAt", "timestamp"),
    ("INGESTED_AT_UTC", "ingestedAt", "timestamp"),
    ("PUBLICATION_KEY", "publicationKey", "text"),
    ("SCHEMA_VERSION", "schemaVersion", "text"),
    ("RECORD_STATE", "recordState", "text"),
)

TABLE_SPECS = (
    (
        "oracle/oracle_event.jsonl",
        "F1_EVENT",
        "eventKey",
        (
            ("EVENT_KEY", "eventKey", "text"),
            ("DISPLAY_NAME", "displayName", "text"),
            ("EVENT_START_AT_UTC", "eventStartAt", "timestamp"),
            ("EVENT_END_AT_UTC", "eventEndAt", "timestamp"),
            ("CREATED_AT_UTC", "createdAt", "timestamp"),
            ("BULK_PROFILE", "bulkProfile", "text"),
            ("NAMESPACE", "namespace", "text"),
        ),
    ),
    (
        "oracle/oracle_circuit_zone.jsonl",
        "F1_ZONE",
        "zoneKey",
        (
            ("ZONE_KEY", "zoneKey", "text"),
            ("EVENT_KEY", "eventKey", "text"),
            ("DISPLAY_NAME", "displayName", "text"),
            ("CAPACITY_UNIT", "capacityUnit", "text"),
            ("CAPACITY_PROFILE", "capacityProfile", "text"),
            ("CAPACITY", "capacity", "integer"),
        ),
    ),
    (
        "oracle/oracle_catalog_product.jsonl",
        "F1_PRODUCT",
        "productKey",
        (
            ("PRODUCT_KEY", "productKey", "text"),
            ("EVENT_KEY", "eventKey", "text"),
            ("DISPLAY_NAME", "displayName", "text"),
            ("AVAILABILITY", "availability", "text"),
            ("PRODUCT_CODE", "productCode", "text"),
            ("SALE_FROM_UTC", "saleFrom", "timestamp"),
            ("SALE_TO_UTC", "saleTo", "timestamp"),
            ("ACCESS_FROM_UTC", "accessFrom", "timestamp"),
            ("ACCESS_TO_UTC", "accessTo", "timestamp"),
            ("CAPACITY_PER_UNIT_JSON", "capacityPerUnit", "json"),
        ),
    ),
    (
        "oracle/oracle_price_list_entry.jsonl",
        "F1_PRICE",
        "priceKey",
        (
            ("PRICE_KEY", "priceKey", "text"),
            ("EVENT_KEY", "eventKey", "text"),
            ("PRODUCT_KEY", "productKey", "text"),
            ("AMOUNT_MINOR", "amountMinor", "integer"),
            ("CURRENCY", "currency", "text"),
            ("TAX_TREATMENT", "taxTreatment", "text"),
            ("EFFECTIVE_FROM_UTC", "effectiveFrom", "timestamp"),
            ("EFFECTIVE_TO_UTC", "effectiveTo", "timestamp"),
        ),
    ),
    (
        "oracle/oracle_bundle_component.jsonl",
        "F1_BUNDLE_COMPONENT",
        "bundleComponentKey",
        (
            ("BUNDLE_COMPONENT_KEY", "bundleComponentKey", "text"),
            ("BUNDLE_PRODUCT_KEY", "bundleProductKey", "text"),
            ("COMPONENT_PRODUCT_KEY", "componentProductKey", "text"),
            ("QUANTITY", "quantity", "positive_integer"),
        ),
    ),
)

TEXT_COLUMN_LENGTHS = {
    "EVENT_KEY": 255,
    "ZONE_KEY": 255,
    "PRODUCT_KEY": 255,
    "PRICE_KEY": 255,
    "BUNDLE_COMPONENT_KEY": 255,
    "BUNDLE_PRODUCT_KEY": 255,
    "COMPONENT_PRODUCT_KEY": 255,
    "DISPLAY_NAME": 300,
    "BULK_PROFILE": 100,
    "NAMESPACE": 2000,
    "SOURCE_SYSTEM": 64,
    "SOURCE_TENANT": 128,
    "SOURCE_ENTITY": 128,
    "SOURCE_KEY": 255,
    "PUBLICATION_KEY": 255,
    "SCHEMA_VERSION": 32,
    "RECORD_STATE": 64,
    "CAPACITY_UNIT": 32,
    "CAPACITY_PROFILE": 64,
    "AVAILABILITY": 128,
    "PRODUCT_CODE": 64,
    "CAPACITY_PER_UNIT_JSON": 2000,
    "CURRENCY": 3,
    "TAX_TREATMENT": 32,
}
NUMBER_COLUMN_PRECISIONS = {"CAPACITY": 12, "AMOUNT_MINOR": 18, "QUANTITY": 10}


def _sql_text(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Expected a string value.")
    if not value:
        raise ValueError("Oracle NOT NULL text columns cannot contain empty strings.")
    if len(value.encode("utf-8")) > 4000:
        raise ValueError("Text exceeds Oracle's 4000-byte AL32UTF8 column limit.")
    parts: list[str] = []
    chunk = ""
    for character in value:
        if ord(character) < 32:
            if chunk:
                parts.append("'" + chunk.replace("'", "''") + "'")
                chunk = ""
            parts.append(f"CHR({ord(character)})")
        else:
            chunk += character
            if len(chunk) == 500:
                parts.append("'" + chunk.replace("'", "''") + "'")
                chunk = ""
    if chunk:
        parts.append("'" + chunk.replace("'", "''") + "'")
    return " ||\n        ".join(parts)


def _sql_timestamp(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Expected an RFC 3339 timestamp string.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Expected an RFC 3339 timestamp string.") from error
    if parsed.tzinfo is None:
        raise ValueError("Timestamps must include an explicit UTC offset.")
    utc_value = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return "TIMESTAMP '" + utc_value.strftime("%Y-%m-%d %H:%M:%S.%f") + "'"


def _sql_value(value: Any, value_type: str, column: str) -> str:
    if value_type in {"text", "json"}:
        if value_type == "json":
            value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if not isinstance(value, str):
            raise ValueError("Expected a string value.")
        if len(value) > TEXT_COLUMN_LENGTHS[column]:
            raise ValueError(f"Text exceeds the {TEXT_COLUMN_LENGTHS[column]}-character column limit.")
        return _sql_text(value)
    if value_type in {"integer", "positive_integer"}:
        if type(value) is not int or value < 0 or (value_type == "positive_integer" and value == 0):
            raise ValueError("Expected a nonnegative integer value.")
        if value >= 10 ** NUMBER_COLUMN_PRECISIONS[column]:
            raise ValueError(f"Integer exceeds NUMBER({NUMBER_COLUMN_PRECISIONS[column]}, 0).")
        return str(value)
    if value_type == "timestamp":
        return _sql_timestamp(value)
    raise ValueError(f"Unsupported Oracle seed value type: {value_type}")


def _load_rows(export_root: Path, relative_path: str) -> list[dict[str, Any]]:
    file_path = export_root / Path(relative_path)
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ValidationError(f"Cannot read Oracle fixture file {relative_path}: {error}") from error
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValidationError(
                f"Invalid JSON in {relative_path} at line {line_number}: {error}"
            ) from error
        if not isinstance(row, dict):
            raise ValidationError(f"Expected a JSON object in {relative_path} at line {line_number}.")
        rows.append(row)
    return rows


def _merge_statement(
    table: str,
    key_field: str,
    columns: tuple[tuple[str, str, str], ...],
    row: dict[str, Any],
) -> str:
    key_column = next(column for column, field, _ in columns if field == key_field)
    key_value = row.get(key_field)
    if not isinstance(key_value, str) or not key_value:
        raise ValidationError(f"{table}: missing canonical key {key_column}.")
    if row.get("canonicalKey") != key_value:
        raise ValidationError(f"{table}: canonicalKey must match {key_column}.")

    all_columns = columns + COMMON_COLUMNS
    source_values = []
    for column, field, value_type in all_columns:
        try:
            value = _sql_value(row.get(field), value_type, column)
        except ValueError as error:
            raise ValidationError(f"{table}.{column}: {error}") from error
        source_values.append(f"    {value} AS {column}")
    projection = ",\n".join(source_values)
    updates = [
        f"    {column} = source.{column}"
        for column, _, _ in all_columns
        if column != key_column
    ]
    insert_columns = ", ".join(column for column, _, _ in all_columns)
    insert_values = ", ".join(f"source.{column}" for column, _, _ in all_columns)
    update_clause = ",\n".join(updates)

    return (
        f"MERGE INTO {table} target\n"
        f"USING (SELECT\n{projection}\nFROM DUAL) source\n"
        f"ON (target.{key_column} = source.{key_column})\n"
        "WHEN MATCHED THEN UPDATE SET\n"
        f"{update_clause}\n"
        "WHEN NOT MATCHED THEN INSERT "
        f"({insert_columns}) VALUES ({insert_values});"
    )


def build_seed_sql(export_root: Path) -> tuple[str, dict[str, int]]:
    export_root = export_root.resolve()
    try:
        validate_dataset(export_root)
    except (OSError, ValueError, ValidationError) as error:
        raise ValidationError(f"Oracle seed requires a valid #18 fixture export: {error}") from error

    statements = [
        "WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK",
        "SET DEFINE OFF",
        "SET SQLBLANKLINES ON",
        "ALTER SESSION SET TIME_ZONE = '+00:00';",
        "PROMPT Loading synthetic Oracle catalog fixture",
    ]
    counts: dict[str, int] = {}
    for relative_path, table, key_field, columns in TABLE_SPECS:
        records = _load_rows(export_root, relative_path)
        records.sort(key=lambda row: row.get(key_field, ""))
        counts[table] = len(records)
        for row in records:
            statements.append(_merge_statement(table, key_field, columns, row))
    statements.extend(("COMMIT;", "PROMPT Synthetic Oracle catalog fixture loaded"))
    return "\n\n".join(statements) + "\n", counts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export an idempotent Oracle seed script from #18 fixtures.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    export_parser = subparsers.add_parser("export", help="Validate a fixture and export SQL*Plus-compatible MERGEs.")
    export_parser.add_argument("--fixture-path", required=True, type=Path)
    export_parser.add_argument("--output-path", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        sql, counts = build_seed_sql(args.fixture_path)
        fixture_path = args.fixture_path.resolve()
        output_path = args.output_path.resolve()
        try:
            output_path.relative_to(fixture_path)
        except ValueError:
            pass
        else:
            raise ValueError("Seed output must be outside the fixture directory.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with output_path.open("x", encoding="utf-8", newline="\n") as output:
                output.write(sql)
        except FileExistsError as error:
            raise FileExistsError(f"Refusing to overwrite existing seed output: {output_path}") from error
    except (OSError, ValueError, ValidationError) as error:
        print(f"Oracle seed export failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "exported", "outputPath": str(args.output_path), "rowCounts": counts}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
