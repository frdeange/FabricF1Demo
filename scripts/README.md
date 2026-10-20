# Scripts

[Repository map](../docs/engineering/repository-layout.md)

Implemented: `python -m scripts.validate_repo` checks local repository guardrails.
`scripts/verify_dev_identity.py` implements the manual read-only identity pilot;
do not execute its network path as part of local scaffold validation.
Owners: #8 foundation; #22 scaffold checks.

#18 owns the planned `scripts/volume_fixture.py` generator/validator and its
explicit output-path interface; this revision does not yet supply it.
Keep that module path stable when it lands. Other source adapters and deployment
scripts appear only through their owning packages; no silent success placeholders.
