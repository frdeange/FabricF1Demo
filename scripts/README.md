# Scripts

[Repository map](../docs/engineering/repository-layout.md)

Implemented: `python -m scripts.validate_repo` checks local repository guardrails.
`scripts/verify_dev_identity.py` implements the manual read-only identity pilot;
do not execute its network path as part of local scaffold validation.
Owners: #8 foundation; #22 scaffold checks.

In a Git checkout, private-reference validation requires Git and checks tracked
and nonignored untracked paths; it does not traverse ignored `.local` or private
reference trees. Force-tracked private reference files still fail. Empty
directories have no Git representation and are not publication evidence.
Git enumeration failures are reported as validation failures, not a successful
filesystem fallback. A source export without `.git` retains filesystem checks.

#18 owns the planned `scripts/volume_fixture.py` generator/validator and its
explicit output-path interface; this revision does not yet supply it.
Keep that module path stable when it lands. Other source adapters and deployment
scripts appear only through their owning packages; no silent success placeholders.
