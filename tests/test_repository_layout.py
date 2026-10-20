from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import validate_repo


class ScaffoldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.inventory = {
            "version": 1,
            "documents": [
                {"path": path, "purpose": "Navigation", "issues": [22], "status": "reserved"}
                for path in sorted(validate_repo.SCAFFOLD_DOCUMENTS)
            ],
        }
        for entry in self.inventory["documents"]:
            path = self.root / entry["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Example\n", encoding="utf-8")
        self.write_inventory()

    def write_inventory(self) -> None:
        (self.root / validate_repo.SCAFFOLD_INVENTORY).write_text(
            json.dumps(self.inventory), encoding="utf-8"
        )

    def test_complete_reserved_scaffold_does_not_require_products(self) -> None:
        self.assertEqual([], validate_repo.check_scaffold(self.root))

    def test_missing_inventory_and_malformed_json_are_reported(self) -> None:
        path = self.root / validate_repo.SCAFFOLD_INVENTORY
        path.unlink()
        self.assertIn("cannot read inventory", validate_repo.check_scaffold(self.root)[0])
        path.write_text("{", encoding="utf-8")
        self.assertIn("cannot read inventory", validate_repo.check_scaffold(self.root)[0])

    def test_top_level_schema_and_version_are_checked(self) -> None:
        for invalid in ([], {}, {"version": True, "documents": []},
                        {"version": 2, "documents": []},
                        {"version": 1, "documents": {}}):
            with self.subTest(invalid=invalid):
                self.inventory = invalid
                self.write_inventory()
                self.assertIn("expected version 1", validate_repo.check_scaffold(self.root)[0])

    def test_missing_document_and_removed_inventory_entry_fail(self) -> None:
        (self.root / "README.md").unlink()
        self.assertTrue(any("missing scaffold document: README.md" in error
                            for error in validate_repo.check_scaffold(self.root)))
        self.inventory["documents"] = [
            entry for entry in self.inventory["documents"] if entry["path"] != "README.md"
        ]
        self.write_inventory()
        self.assertTrue(any("missing required document entry: README.md" in error
                            for error in validate_repo.check_scaffold(self.root)))

    def test_duplicate_paths_fail(self) -> None:
        self.inventory["documents"].append(self.inventory["documents"][0].copy())
        self.write_inventory()
        self.assertTrue(any("duplicate document path" in error
                            for error in validate_repo.check_scaffold(self.root)))

    def test_invalid_entry_fields_report_errors_without_crashing(self) -> None:
        for field, value, expected in (
            ("purpose", "", "purpose must"),
            ("issues", [], "issues must"),
            ("issues", [True], "issues must"),
            ("issues", [-1], "issues must"),
            ("status", {}, "status must"),
            ("path", "../outside.md", "safe repository-relative"),
            ("path", "docs\\README.md", "safe repository-relative"),
            ("path", "/README.md", "safe repository-relative"),
            ("path", "C:/README.md", "safe repository-relative"),
            ("path", "docs//README.md", "safe repository-relative"),
        ):
            with self.subTest(field=field, value=value):
                original = self.inventory["documents"][0].copy()
                self.inventory["documents"][0][field] = value
                self.write_inventory()
                self.assertTrue(any(expected in error
                                    for error in validate_repo.check_scaffold(self.root)))
                self.inventory["documents"][0] = original

    def test_missing_entry_fields_fail(self) -> None:
        self.inventory["documents"][0] = {"path": "README.md"}
        self.write_inventory()
        self.assertIn("expected path, purpose", validate_repo.check_scaffold(self.root)[0])

    def test_inventory_checks_actual_navigation(self) -> None:
        (self.root / "README.md").write_text("[Lost](missing.md)\n", encoding="utf-8")
        self.assertTrue(any("missing navigation target" in error
                            for error in validate_repo.check_scaffold(self.root)))


class NavigationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "README.md").write_text(
            "# Target heading\n\n# Target heading\n", encoding="utf-8"
        )
        (self.root / "docs").mkdir()

    def check(self, text: str) -> list[str]:
        (self.root / "docs" / "README.md").write_text(text, encoding="utf-8")
        return validate_repo.check_local_links(self.root, "docs/README.md")

    def test_relative_files_fragments_and_duplicate_headings(self) -> None:
        self.assertEqual([], self.check(
            "[Root](../README.md#target-heading)\n"
            "[Duplicate](../README.md#target-heading-1)\n"
            "[Self](#local)\n\n## Local\n"
        ))

    def test_broken_file_and_fragment_report_source_and_target(self) -> None:
        errors = self.check("[File](lost.md)\n[Anchor](../README.md#lost)\n")
        self.assertEqual(2, len(errors))
        self.assertIn("docs/README.md: missing navigation target: lost.md", errors)
        self.assertIn("docs/README.md: missing heading fragment: ../README.md#lost", errors)

    def test_remote_links_and_future_code_examples_are_not_local_targets(self) -> None:
        self.assertEqual([], self.check(
            "[Web](https://example.invalid/no-network)\n[Mail](mailto:demo@example.invalid)\n"
            "`[Future](unimplemented.md)`\n"
            "```text\n[Future](future.md)\n```\n"
            "~~~text\n[Future](future-too.md)\n~~~\n"
            "Future example: `fabric/workspace/Example.SemanticModel`.\n"
        ))

    def test_percent_encoded_path_and_heading(self) -> None:
        (self.root / "file name.md").write_text("# A heading\n", encoding="utf-8")
        self.assertEqual([], self.check("[Encoded](../file%20name.md#a%2Dheading)"))

    def test_root_escape_and_absolute_links_fail(self) -> None:
        for target in ("../../outside.md", "/README.md", "file:///tmp/a.md"):
            with self.subTest(target=target):
                self.assertTrue(self.check(f"[Unsafe]({target})"))

    def test_fragment_on_non_markdown_target_fails_explicitly(self) -> None:
        (self.root / "example.json").write_text("{}", encoding="utf-8")
        self.assertIn("fragment requires a Markdown target",
                      self.check("[JSON](../example.json#missing)")[0])


if __name__ == "__main__":
    unittest.main()
