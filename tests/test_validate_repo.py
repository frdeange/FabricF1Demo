from __future__ import annotations

import sys
import tempfile
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
    def test_revised_readiness_invariants_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "EXECUTION-PLAN.md").write_text(
                "\n".join(validate_repo.PLAN_INVARIANTS), encoding="utf-8"
            )

            self.assertEqual([], validate_repo.check_plan_invariants(root))

    def test_missing_deployment_or_qualification_invariant_fails(self) -> None:
        phrases = (
            "records a separately approved four-resource Terraform deployment",
            "Infrastructure deployment does not qualify workloads or unattended deployment.",
            "F2 workload fitness remain unqualified.",
            "Terraform uses one external local state",
        )
        for missing in phrases:
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "EXECUTION-PLAN.md").write_text(
                    "\n".join(
                        phrase
                        for phrase in validate_repo.PLAN_INVARIANTS
                        if phrase != missing
                    ),
                    encoding="utf-8",
                )

                self.assertEqual(
                    [f"EXECUTION-PLAN.md is missing invariant: {missing}"],
                    validate_repo.check_plan_invariants(root),
                )

    def test_stale_deployment_claims_fail_in_readiness_documents(self) -> None:
        documents = (
            "README.md",
            "EXECUTION-PLAN.md",
            "docs/deployment-ownership-support-matrix.md",
            "docs/dev-identity-pilot.md",
        )
        for document in documents:
            for claim in validate_repo.STALE_NO_DEPLOYMENT_CLAIMS:
                with self.subTest(document=document, claim=claim):
                    with tempfile.TemporaryDirectory() as directory:
                        root = Path(directory)
                        for relative_path in documents:
                            path = root / relative_path
                            path.parent.mkdir(parents=True, exist_ok=True)
                            path.write_text(
                                claim.lower() if relative_path == document else "",
                                encoding="utf-8",
                            )

                        self.assertEqual(
                            [f"{document} contains stale deployment claim: {claim}"],
                            validate_repo.check_stale_deployment_claims(root),
                        )

    def test_revised_documents_have_no_stale_claims(self) -> None:
        self.assertEqual([], validate_repo.check_stale_deployment_claims(ROOT))

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
