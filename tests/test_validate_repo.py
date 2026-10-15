from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import validate_repo


class ActionPinningTests(unittest.TestCase):
    def test_detects_floating_action_ref(self) -> None:
        workflow = "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4\n"

        errors = validate_repo.find_unpinned_actions(workflow, "sample.yml")

        self.assertTrue(errors)
        self.assertIn("not pinned to a full commit SHA", errors[0])

    def test_accepts_full_sha_action_ref(self) -> None:
        workflow = (
            "jobs:\n"
            "  test:\n"
            "    steps:\n"
            f"      - uses: actions/checkout@{validate_repo.CHECKOUT_SHA} # v4.2.2\n"
        )

        errors = validate_repo.find_unpinned_actions(workflow, "sample.yml")

        self.assertEqual([], errors)


class RepositoryValidationTests(unittest.TestCase):
    def test_detects_explicit_private_source_marker(self) -> None:
        text = "[INTERNAL SOURCE: synthetic-placeholder]"

        errors = validate_repo.find_private_source_markers(text)

        self.assertEqual(1, len(errors))
        self.assertIn("private-source marker", errors[0])

    def test_current_repository_passes_validation(self) -> None:
        errors = validate_repo.run_checks(ROOT)

        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
