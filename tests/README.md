# Tests

[Repository map](../docs/engineering/repository-layout.md)

Implemented credential-free stdlib tests owned by their associated package
(contracts #5, CI/identity #8, scaffold #22). Run:

```text
python -m unittest discover -s tests -p "test_*.py" -v
```

Use self-cleaning temporary directories, not persistent generated data under
the checkout. Preserve #18's active fixture tests when they land.
Later cloud/journey tests require explicit qualified environments; local passing
tests do not establish deployment, authorization or live-race readiness.
