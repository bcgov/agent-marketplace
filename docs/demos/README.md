# Community onboarding demos

These demos are documentation-first and run from a clean checkout. They use
the generated catalog, static GUI, companion skills, and deterministic
marketplace scanner already used by the repository. Demo submissions are
copied into a temporary canonical package path and treated as data; no fixture
script or package lifecycle hook is executed.

## Prerequisites

- Python 3.12+, `uv`, and Node.js;
- a checkout with dependencies available through `make setup`;
- a browser for the GUI demos;
- access to the public repository and GitHub issues for request/submission
  paths.

Run `make setup` once, then use the runbooks below. Each runbook names its
expected evidence and reset boundary. No demo changes the published package
inventory or checked-in generated projections.

## Runbooks

| Journey | Runbook |
| --- | --- |
| Browse and install a security extension | [browse-and-install.md](browse-and-install.md) |
| Find an extension with Copilot | [find-with-copilot.md](find-with-copilot.md) |
| Create an extension | [create-an-extension.md](create-an-extension.md) |
| Analyze benign and blocked submissions | [analyze-submissions.md](analyze-submissions.md) |
| Browse as a non-technical user | [non-technical-gui.md](non-technical-gui.md) |
| Explain trust and digests | [trust-and-digest.md](trust-and-digest.md) |
| Follow the no-match path | [no-match.md](no-match.md) |

## Deferred by design

These demos do not claim support for executable agents, hooks, MCP servers,
automatic execution, private marketplace infrastructure, centralized install
telemetry, or silent one-click installation. They show guided confirmation,
immutable source evidence, deterministic policy results, and human review
boundaries instead.
