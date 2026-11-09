# Workflow review reference

This is an illustrative permission boundary, not a complete CI workflow:

```yaml
name: Pull request validation
on: pull_request
permissions: {}
jobs:
  validate:
    runs-on: ubuntu-24.04
    permissions:
      contents: read
    steps:
      - run: echo "Add reviewed checkout and project validation steps here"
```

Choose reviewed action revisions and actual project commands before use. An
outside contributor may need run approval. Do not add a job that fails solely
because the PR originates from a fork. Privileged publication/merge/deployment
belongs to separately authorized trusted code with exact-revision checks.

- [GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use): least privilege, untrusted checkout and immutable action pinning.
- [Fork workflow runs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/approve-runs-from-forks): repository approval behavior.
- [Script injections](https://docs.github.com/en/actions/concepts/security/script-injections): untrusted expression input handling.

Full commit SHA pinning fixes the selected action source. Movable major tags,
including first-party tags, do not provide that guarantee. Check runner and
action support against current documentation when preparing a real change.
