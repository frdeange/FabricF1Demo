# GitHub automation and templates

[Repository map](../docs/engineering/repository-layout.md)

Implemented: [package issue form](ISSUE_TEMPLATE/package-work.yml),
[PR template](PULL_REQUEST_TEMPLATE.md), [validation CI](workflows/ci.yml) and
[manual read-only DEV identity pilot](workflows/verify-dev-identity.yml).
CI requires no cloud credentials; the trusted-main identity pilot uses its
separate approved environment/OIDC configuration and does not deploy.

Owner: CI foundation #8, readiness #3, scaffold #22. Future provisioning,
deployment, preview, promotion, seeding and verification workflows are planned,
not implemented by these files. Create them only with real qualified capability,
pinned action SHAs, least privilege and explicit target/identity/rollback gates.
No shared label, Environment or branch-protection changes are included here.
