from __future__ import annotations

import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from pathlib import Path

from scripts.volume_fixture import GenerationParameters, generate_dataset
from sources.oracle.seed import (
    NUMBER_COLUMN_PRECISIONS,
    TEXT_COLUMN_LENGTHS,
    ValidationError,
    _sql_text,
    _sql_timestamp,
    _sql_value,
    build_seed_sql,
    main,
)


class OracleSeedTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="oracle-seed-test-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.export_path = self.root / "fixture"
        self.parameters = GenerationParameters(
            self.export_path,
            customer_count=30,
            order_count=600,
        )
        generate_dataset(self.parameters)

    def test_builds_deterministic_upserts_for_oracle_owned_catalog_only(self) -> None:
        sql, counts = build_seed_sql(self.export_path)

        self.assertEqual(
            {
                "F1_EVENT": 1,
                "F1_ZONE": 2,
                "F1_PRODUCT": 4,
                "F1_PRICE": 4,
                "F1_BUNDLE_COMPONENT": 2,
            },
            counts,
        )
        self.assertEqual(sql, build_seed_sql(self.export_path)[0])
        self.assertIn("WHEN MATCHED THEN UPDATE", sql)
        self.assertIn("WHEN NOT MATCHED THEN INSERT", sql)
        self.assertIn("DISPLAY_NAME = source.DISPLAY_NAME", sql)
        self.assertNotIn("target.DISPLAY_NAME =", sql)
        self.assertIn("CAPACITY_PER_UNIT_JSON", sql)
        self.assertIn("AMOUNT_MINOR", sql)
        self.assertIn("COMMIT;", sql)
        self.assertIn("ALTER SESSION SET TIME_ZONE = '+00:00';", sql)
        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn("TRUNCATE TABLE", sql)
        self.assertNotIn("DELETE FROM", sql)
        self.assertNotIn("F1_ORDER", sql)
        self.assertNotIn("F1_RESERVATION", sql)
        self.assertNotIn("SOLD_ALLOCATION", sql)

    def test_seed_export_does_not_modify_the_source_fixture(self) -> None:
        before = {
            path.relative_to(self.export_path): path.read_bytes()
            for path in self.export_path.rglob("*")
            if path.is_file()
        }

        build_seed_sql(self.export_path)

        after = {
            path.relative_to(self.export_path): path.read_bytes()
            for path in self.export_path.rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)

    def test_sql_text_escapes_quotes(self) -> None:
        self.assertEqual("'O''Brien'", _sql_text("O'Brien"))

    def test_text_control_characters_cannot_become_sqlplus_commands(self) -> None:
        self.assertEqual(
            "'first' ||\n        CHR(10) ||\n        '/' ||\n        CHR(13) ||\n        CHR(10)"
            " ||\n        'HOST command' ||\n        CHR(9) ||\n        'last'",
            _sql_text("first\n/\r\nHOST command\tlast"),
        )

    def test_target_character_and_byte_limits_are_enforced(self) -> None:
        self.assertTrue(_sql_value("a" * 2000, "text", "NAMESPACE"))
        self.assertTrue(_sql_value("\u00e9" * 2000, "text", "NAMESPACE"))
        with self.assertRaisesRegex(ValueError, "2000-character"):
            _sql_value("a" * 2001, "text", "NAMESPACE")
        with self.assertRaisesRegex(ValueError, "4000-byte"):
            _sql_value("\u20ac" * 1334, "text", "NAMESPACE")
        with self.assertRaisesRegex(ValueError, "empty strings"):
            _sql_value("", "text", "NAMESPACE")

    def test_target_number_precision_boundaries_are_enforced(self) -> None:
        for column, precision in NUMBER_COLUMN_PRECISIONS.items():
            with self.subTest(column=column):
                self.assertEqual(str(10 ** precision - 1),
                                 _sql_value(10 ** precision - 1, "integer", column))
                with self.assertRaisesRegex(ValueError, "exceeds NUMBER"):
                    _sql_value(10 ** precision, "integer", column)

    def test_seed_target_limits_match_schema_and_timestamps_use_supported_type(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "sources" / "oracle" / "schema" / "001_catalog.sql"
        schema = schema_path.read_text(encoding="utf-8")
        text_columns = {
            name: int(width)
            for name, width in re.findall(r"^\s+(\w+) (?:VARCHAR2|CHAR)\((\d+) CHAR\)", schema, re.MULTILINE)
        }
        number_columns = {
            name: int(precision)
            for name, precision in re.findall(r"^\s+(\w+) NUMBER\((\d+), 0\)", schema, re.MULTILINE)
        }
        self.assertEqual(TEXT_COLUMN_LENGTHS, text_columns)
        self.assertEqual(NUMBER_COLUMN_PRECISIONS, number_columns)
        timestamps = [line for line in schema.splitlines() if "TIMESTAMP(" in line]
        self.assertTrue(timestamps)
        self.assertTrue(all("TIMESTAMP(6) WITH LOCAL TIME ZONE NOT NULL" in line for line in timestamps))

    def test_valid_fixture_with_long_namespace_fails_before_output_creation(self) -> None:
        fixture_path = self.root / "oversize-fixture"
        generate_dataset(replace(self.parameters, output_path=fixture_path, run_version="r" * 2500))
        output = self.root / "oversize.sql"
        errors = io.StringIO()
        with redirect_stderr(errors):
            result = main([
                "export", "--fixture-path", str(fixture_path), "--output-path", str(output),
            ])
        self.assertEqual(1, result)
        self.assertIn("F1_EVENT.NAMESPACE", errors.getvalue())
        self.assertFalse(output.exists())

    def test_long_valid_namespace_keeps_sqlplus_physical_lines_short(self) -> None:
        fixture_path = self.root / "long-fixture"
        generate_dataset(replace(self.parameters, output_path=fixture_path, run_version="r" * 1750))
        sql, counts = build_seed_sql(fixture_path)
        self.assertEqual(13, sum(counts.values()))
        self.assertLess(max(len(line.encode("utf-8")) for line in sql.splitlines()), 2499)
        self.assertIn(" ||\n", sql)
        quoted = _sql_text("'" * 2000)
        self.assertLess(max(len(line.encode("utf-8")) for line in quoted.splitlines()), 2499)

    def test_timestamp_values_are_normalized_to_utc(self) -> None:
        self.assertEqual(
            "TIMESTAMP '2030-06-15 13:00:00.000000'",
            _sql_timestamp("2030-06-15T15:00:00+02:00"),
        )

    def test_cli_exports_outside_fixture_without_overwriting(self) -> None:
        output = self.root / "seed" / "seed.sql"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(
                0,
                main([
                    "export",
                    "--fixture-path", str(self.export_path),
                    "--output-path", str(output),
                ]),
            )
        self.assertIn("MERGE INTO F1_EVENT", output.read_text(encoding="utf-8"))

        previous = output.read_text(encoding="utf-8")
        errors = io.StringIO()
        with redirect_stderr(errors):
            self.assertEqual(
                1,
                main([
                    "export",
                    "--fixture-path", str(self.export_path),
                    "--output-path", str(output),
                ]),
            )
        self.assertEqual(previous, output.read_text(encoding="utf-8"))
        self.assertIn("Refusing to overwrite", errors.getvalue())

    def test_cli_rejects_output_inside_fixture(self) -> None:
        output = self.export_path / "seed.sql"
        errors = io.StringIO()
        with redirect_stderr(errors):
            self.assertEqual(
                1,
                main([
                    "export",
                    "--fixture-path", str(self.export_path),
                    "--output-path", str(output),
                ]),
            )
        self.assertFalse(output.exists())
        self.assertIn("outside the fixture directory", errors.getvalue())

    def test_rejects_fixture_with_mismatched_canonical_key(self) -> None:
        event_path = self.export_path / "oracle" / "oracle_event.jsonl"
        event = json.loads(event_path.read_text(encoding="utf-8"))
        event["canonicalKey"] = "EVT-OTHER"
        event_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

        with self.assertRaisesRegex(ValidationError, "valid #18 fixture export"):
            build_seed_sql(self.export_path)

    def test_seed_does_not_overwrite_existing_generated_output(self) -> None:
        with self.assertRaises(FileExistsError):
            generate_dataset(self.parameters)

        self.assertEqual(5, len(list((self.export_path / "oracle").glob("*.jsonl"))))


if __name__ == "__main__":
    unittest.main()
