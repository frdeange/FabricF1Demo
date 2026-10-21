from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


@unittest.skipUnless(shutil.which("git"), "Git is required for ignore-scope tests")
class GitValidationScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        subprocess.run(
            ["git", "-C", str(self.root), "init", "--quiet"], check=True,
            capture_output=True,
        )
        (self.root / ".gitignore").write_text(
            ".local/\nFilesAndReferences/\n", encoding="utf-8"
        )
        for name in (".local", "FilesAndReferences"):
            (self.root / name).mkdir()
            (self.root / name / "synthetic.txt").write_text(
                "synthetic test content only", encoding="utf-8"
            )

    def test_ignored_private_directories_are_outside_validation_scope(self) -> None:
        paths = {str(relative) for relative, _ in validate_repo.iter_repo_paths(self.root)}
        self.assertEqual({".gitignore"}, paths)
        self.assertEqual([], validate_repo.check_internal_sibling_not_copied(self.root))

    def test_force_tracked_private_reference_still_fails(self) -> None:
        subprocess.run(
            ["git", "-C", str(self.root), "add", "--force", "--",
             "FilesAndReferences/synthetic.txt"], check=True, capture_output=True,
        )
        errors = validate_repo.check_internal_sibling_not_copied(self.root)
        self.assertEqual(1, len(errors))
        self.assertIn("Internal sibling path must not be committed", errors[0])

    def test_nonignored_private_reference_still_fails(self) -> None:
        (self.root / ".gitignore").write_text(".local/\n", encoding="utf-8")
        self.assertEqual(
            1, len(validate_repo.check_internal_sibling_not_copied(self.root))
        )

    def test_source_export_without_git_retains_filesystem_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "FilesAndReferences").mkdir()
            self.assertTrue(validate_repo.check_internal_sibling_not_copied(root))

    def test_git_enumeration_failure_is_a_validation_error(self) -> None:
        for failure in (
            FileNotFoundError("Git executable not found"),
            subprocess.CalledProcessError(128, ["git", "ls-files"]),
        ):
            with self.subTest(failure=failure), mock.patch(
                "scripts.validate_repo.subprocess.run", side_effect=failure
            ):
                errors = validate_repo.check_internal_sibling_not_copied(self.root)
                self.assertEqual(1, len(errors))
                self.assertIn("Cannot enumerate repository paths", errors[0])


if __name__ == "__main__":
    unittest.main()
