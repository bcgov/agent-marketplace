# Security policy

## Report privately

Do not open a public issue for a suspected vulnerability, exposed credential, malicious instruction, or marketplace bypass.

Use [GitHub private vulnerability reporting](https://github.com/bcgov/agent-marketplace/security/advisories/new). Include the affected package ID, immutable revision, package-tree digest, evidence, and any known installations. Do not include live secrets; revoke them first and provide only a redacted identifier.

Marketplace maintainers acknowledge critical reports within one business day. They may quarantine an entry immediately while evidence is assessed. Publication, quarantine, and removal decisions remain human actions bound to an exact revision and digest.

## Scope

Reports may cover the marketplace generator and scanner, companion skills, generated catalog, installation and receipt behavior, CI controls, or hosted and federated Agent Skill packages. Hooks, MCP servers, custom agents, and organization-wide distribution are outside the marketplace MVP.

## Public follow-up

After remediation, maintainers publish non-sensitive removal or update guidance and link it from the affected catalog record or issue. Installation receipts remain local and are not centrally collected as analytics.
