# Contributing

Start with the [repository map](docs/engineering/repository-layout.md),
[agent guidance](AGENTS.md) and the package issue linked to your work.
The scaffold is tracked in [#22](https://github.com/frdeange/FabricF1Demo/issues/22).
Repository content is English and public-safe.

## Workflow

Use GitHub Flow: a focused issue and branch from `main`, Conventional Commits,
and a reviewed PR targeting `main`. Preserve unrelated work and coordinate changes
to shared paths with their active package owner. Do not move a package's files
merely to conform to a proposed future layout.

Complete implementation and validation, obtain independent actual-diff review,
resolve findings and verify fixes, then present the diff and evidence to the user.
Explicit user approval of that result is required before opening any PR, including
a draft. Plan approval is not PR approval. Commit/push also require authorization.
Never merge without an explicit request.

## Local checks

Run from the repository root with Python 3.12 (the CI baseline):

```text
python -m scripts.validate_repo
python -m unittest discover -s tests -p "test_*.py" -v
git diff --check
```

CI runs the first two commands without cloud credentials. Package-specific checks
are additional requirements, not replacements. Use temporary directories in tests.

## Safety and placement

Use the map's naming and ownership rules. Keep source and generated output
separate. Bulk output belongs outside Git; optional local `generated` and
`artifacts` directories are ignored. Do not commit secrets, tenant bindings,
Terraform state, private references or unapproved licensed data.

Cloud operations need separate explicit target, identity, budget, region and
rollback approval. A directory or README is not proof of a qualified deployment.
Use the existing [issue form](.github/ISSUE_TEMPLATE/package-work.yml) and
[PR template](.github/PULL_REQUEST_TEMPLATE.md); retain their evidence and gates.
