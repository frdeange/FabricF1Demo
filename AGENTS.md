# Repository agent guidance

## Language and traceability

- Author repository content in English: code comments when needed, docs, issues, PRs, runbooks, UI copy, and status reports.
- Keep work aligned to the assigned GitHub issue and branch. Do not mix unrelated roadmap items into a package branch.
- Link changes to the package issue they serve, and keep acceptance criteria explicit and testable.

## Safety and disclosure

- Do not copy or summarize private reference folders, internal presentations, credentials, tenant details, customer data, or licensed datasets into this public repository.
- Keep configuration secret-free. Use placeholders and document required approvals instead of inventing credentials or identities.
- Do not provision, deploy, destroy, or mutate cloud resources unless the task explicitly approves the target, identity, budget, region, and rollback path.
- Avoid destructive cleanup switches and automatic orphan deletion in deployment tooling.

## Workflow

- Use [the repository map](docs/engineering/repository-layout.md),
  [contribution guide](CONTRIBUTING.md) and
  [agent playbook](docs/engineering/agent-playbook.md) for placement and handoffs.
- Preserve native artifact formats and active package ownership; documented
  reserved folders are not implemented workloads or deployment approval.

- Run the narrowest relevant checks before handing off. For this foundation slice, run `python -m scripts.validate_repo` and `python -m unittest discover -s tests -p "test_*.py" -v`.
- Keep GitHub Actions on least-privilege permissions. Pin external actions to immutable full commit SHAs with release comments.
- Do not commit, push, or open a PR unless the assignment explicitly authorizes it. A PR must wait for independent review and explicit user approval.
