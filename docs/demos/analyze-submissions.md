# Analyze benign and blocked submissions

Run the isolated fixture helper:

```bash
make demo-analyze FIXTURE=benign-submission
make demo-analyze FIXTURE=blocked-submission
```

The benign result should contain a package-tree digest, file inventory,
`classification: needs-review`, and `scan.outcome: passed`. The blocked result
should contain `classification: blocked` and a `blocked-extension-type`
finding for `package.json`.

Both runs use a temporary `skills/community/demo-submission` path and remove
it automatically. The scanner reads bytes and metadata only; it never runs
the fixture's `preinstall` text or any other contributed content. A maintainer
can use the same workflow on a draft submission with:

```bash
uv run python scripts/marketplace.py analyze skills/community/<name>
```

Blocking findings prevent catalog publication. Passing the mechanical scan
still requires human marketplace and domain review.
