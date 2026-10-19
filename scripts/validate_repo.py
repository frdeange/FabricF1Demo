from __future__ import annotations

import re
import sys
from pathlib import Path

ACTION_REF_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"[A-Za-z]:\\")
PRIVATE_SOURCE_MARKER_RE = re.compile(
    r"\[(?:private|internal)\s+(?:source|reference)(?:\s+material)?\s*:",
    re.IGNORECASE,
)

CHECKOUT_SHA = "11bd71901bbe5b1630ceea73d27597364c9af683"
SETUP_PYTHON_SHA = "a26af69be951a213d495a4c3e4e4022e16d87065"
INTERNAL_SIBLING_NAME = "FilesAndReferences"

REQUIRED_FILES = [
    "README.md",
    "AGENTS.md",
    "EXECUTION-PLAN.md",
    ".github/workflows/ci.yml",
    ".github/ISSUE_TEMPLATE/package-work.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "docs/deployment-ownership-support-matrix.md",
]

PORTABLE_FOUNDATION_FILES = [
    "AGENTS.md",
    "EXECUTION-PLAN.md",
    ".github/workflows/ci.yml",
    ".github/ISSUE_TEMPLATE/package-work.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "docs/deployment-ownership-support-matrix.md",
]

PLAN_INVARIANTS = [
    "The plan is approved by the user.",
    "frdeange/FabricF1Demo",
    "issue [#8]",
    "8-ci-cd-foundation",
    "records a separately approved four-resource Terraform deployment",
    "Infrastructure deployment does not qualify workloads or unattended deployment.",
    "F2 workload fitness remain unqualified.",
    "Terraform uses one external local state",
    "English is the default language",
]

STALE_NO_DEPLOYMENT_CLAIMS = [
    "No cloud resources have been deployed.",
    "No Fabric or Azure resources have been deployed.",
    "No deployment has been qualified",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_repo_text(root: Path, relative_path: str) -> str:
    return (root / Path(relative_path)).read_text(encoding="utf-8")


def iter_repo_paths(root: Path):
    for path in root.rglob("*"):
        relative_path = path.relative_to(root)
        if relative_path.parts and relative_path.parts[0] == ".git":
            continue
        yield relative_path, path


def check_required_files(root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_FILES:
        if not (root / Path(relative_path)).is_file():
            errors.append(f"Missing required file: {relative_path}")
    return errors


def check_plan_invariants(root: Path) -> list[str]:
    plan = read_repo_text(root, "EXECUTION-PLAN.md")
    return [
        f"EXECUTION-PLAN.md is missing invariant: {phrase}"
        for phrase in PLAN_INVARIANTS
        if phrase not in plan
    ]


def check_stale_deployment_claims(root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path in (
        "README.md",
        "EXECUTION-PLAN.md",
        "docs/deployment-ownership-support-matrix.md",
    ):
        text = read_repo_text(root, relative_path)
        for phrase in STALE_NO_DEPLOYMENT_CLAIMS:
            if phrase.casefold() in text.casefold():
                errors.append(f"{relative_path} contains stale deployment claim: {phrase}")
    return errors


def find_unpinned_actions(workflow_text: str, workflow_name: str = "workflow") -> list[str]:
    errors: list[str] = []
    for match in ACTION_REF_RE.finditer(workflow_text):
        spec = match.group(1)
        if spec.startswith("./") or spec.startswith(".\\"):
            continue
        if "@" not in spec:
            errors.append(f"{workflow_name}: action reference has no ref: {spec}")
            continue
        action, ref = spec.rsplit("@", 1)
        if not FULL_SHA_RE.fullmatch(ref):
            errors.append(f"{workflow_name}: {action} is not pinned to a full commit SHA: {ref}")
    return errors


def check_workflow(root: Path) -> list[str]:
    workflow = read_repo_text(root, ".github/workflows/ci.yml")
    errors = find_unpinned_actions(workflow, ".github/workflows/ci.yml")

    required_fragments = [
        "permissions:\n  contents: read",
        "cancel-in-progress: false",
        f"actions/checkout@{CHECKOUT_SHA} # v4.2.2",
        f"actions/setup-python@{SETUP_PYTHON_SHA} # v5.6.0",
        "python -m scripts.validate_repo",
        'python -m unittest discover -s tests -p "test_*.py" -v',
    ]
    for fragment in required_fragments:
        if fragment not in workflow:
            errors.append(f".github/workflows/ci.yml is missing required fragment: {fragment}")

    forbidden_fragments = [
        "id-token: write",
        "secrets.",
        "pull_request_target",
        "azure/login",
        "fabric-cicd",
        "rayfin",
    ]
    lowered = workflow.lower()
    for fragment in forbidden_fragments:
        if fragment.lower() in lowered:
            errors.append(f".github/workflows/ci.yml contains forbidden deploy/auth fragment: {fragment}")

    return errors


def check_internal_sibling_not_copied(root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path, _ in iter_repo_paths(root):
        if any(part.casefold() == INTERNAL_SIBLING_NAME.casefold() for part in relative_path.parts):
            errors.append(f"Internal sibling path must not be committed: {relative_path}")
    return errors


def check_portable_foundation_text(root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path in PORTABLE_FOUNDATION_FILES:
        text = read_repo_text(root, relative_path)
        if WINDOWS_ABSOLUTE_PATH_RE.search(text):
            errors.append(f"{relative_path} contains a machine-absolute Windows path")
        if INTERNAL_SIBLING_NAME in text:
            errors.append(f"{relative_path} names the private sibling folder")
        if PRIVATE_SOURCE_MARKER_RE.search(text):
            errors.append(f"{relative_path} contains an explicit private-source marker")
    return errors


def find_private_source_markers(text: str) -> list[str]:
    return [
        "text contains an explicit private-source marker"
        for _ in PRIVATE_SOURCE_MARKER_RE.finditer(text)
    ]


def check_deployment_matrix(root: Path) -> list[str]:
    matrix = read_repo_text(root, "docs/deployment-ownership-support-matrix.md")
    required_phrases = [
        "Cloud deployment workflows are intentionally unimplemented",
        "Issue #8 must remain open",
        "unattended deployment pilot",
        "BLOCKED",
        "approved unattended deployment identity and permissions",
        "protected state, coordination and recovery",
        "Terraform uses one external local state",
        "Rayfin 1.36.2 deployment pipeline excludes functions/secrets",
        "One writer per artifact and destination",
        "fabric-cicd is suitable for supported Fabric item definitions",
    ]
    return [
        f"docs/deployment-ownership-support-matrix.md is missing: {phrase}"
        for phrase in required_phrases
        if phrase not in matrix
    ]


def run_checks(root: Path | None = None) -> list[str]:
    root = root or repo_root()
    errors: list[str] = []
    errors.extend(check_required_files(root))
    if errors:
        return errors
    errors.extend(check_plan_invariants(root))
    errors.extend(check_stale_deployment_claims(root))
    errors.extend(check_workflow(root))
    errors.extend(check_internal_sibling_not_copied(root))
    errors.extend(check_portable_foundation_text(root))
    errors.extend(check_deployment_matrix(root))
    return errors


def main() -> int:
    errors = run_checks()
    if errors:
        print("Repository validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
