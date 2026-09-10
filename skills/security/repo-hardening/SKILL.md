---
name: repo-hardening
description: Baseline GitHub repository hardening for branch protection, review gates, secret hygiene, and deterministic validation in BC Gov projects.
owner: bcgov
tags: [security, github, branch-protection, secrets, review]
---

# Repo Hardening

## Use When
- A repository needs a baseline security review before it is shared more widely.
- A team needs a quick checklist for branch protection, secret handling, and required review gates.
- A project needs a repeatable security hygiene recipe for GitHub and CI.

## Don't Use When
- You need a full platform security architecture review.
- You are authoring application-level threat models or production runtime controls.
- You need to bypass repository or security policy for production approvals.

## Workflow
1. Confirm the repository has protected default branches and required review checks.
2. Check that secret scanning and push protection are enabled for the default branch.
3. Review required actions, workflow permissions, and any external automation that can write to the repo.
4. Confirm that CI validation is deterministic and not based on unreviewed custom scripts with broad execution.
5. Record the final hardening state and any exceptions in a reviewable document or issue.

## Rules
- Keep the hardening recipe grounded in GitHub-native controls and reviewed automation.
- Never claim a repo is secure because it merely contains a policy file.
- Prefer explicit branch protection, review requirements, and secret-detection settings over undocumented custom flows.
- Treat any repository secret as an operational risk that must be rotated and scoped.
- Require human review for semantic security decisions and policy exceptions.

## Examples
- "Enable required reviews and status checks before merge" → confirm branch protection and required checks.
- "Scan for hardcoded secrets in the repo" → review GitHub secret scanning and push protection results.
- "Set up CI validation for marketplace and policy checks" → route validation through deterministic local checks.

## Edge Cases
- When the repo has no default branch protection, add the required check and review gate before publishing a release.
- When a workflow relies on PATs, rotate and scope them to the minimum permissions needed.
- When a repository is not yet production-ready, keep the hardening notes as a tracked backlog item rather than a blanket approval.

## References
- [GitHub repository security overview](https://docs.github.com/en/code-security)
- [BC Gov Agent Marketplace security rules](../../../SECURITY.md)
