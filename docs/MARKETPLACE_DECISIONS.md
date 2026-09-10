# Marketplace MVP decisions

Status: approved implementation baseline

| Decision | Outcome | Owner |
| --- | --- | --- |
| Creation companion name | `bcgov-create-extension`; no deploy companion | Marketplace maintainers |
| Approved discovery sources | Agent Skills Directory, Microsoft Agent Skills, Anthropic Skills, and Awesome Copilot; candidates must resolve to canonical HTTPS GitHub repositories and full commit SHAs | Marketplace maintainers |
| Blocking policy | Structural, source-integrity, secret, hidden-Unicode, unsupported-type, execution, and undeclared-capability findings block without override. Deterministic instruction findings require separate acknowledgement and human review. | Marketplace and security maintainers |
| Registration identity | GitHub records the authenticated issue actor; the marketplace collects no additional requester identity | Marketplace maintainers |
| Review ownership | Repository CODEOWNERS plus package maintainers review the exact head revision; `@mishraomp` and `@DerekRoberts` own marketplace controls | Repository owners |
| Hosted-content license | Apache-2.0 | Repository owners |
| MVP version model | Full Git commit SHA plus package-tree SHA-256 digest | Marketplace maintainers |
| Supported hosts | Local VS Code desktop workspaces. Remote extension hosts require explicit destination confirmation and are not part of the launch claim. | Product owner |

Changes to decisions 1 through 3 require marketplace-owner approval and corresponding policy, companion, fixture, and documentation updates.
