# Getting started with the BC Gov Agent Marketplace

This is a tutorial for getting to a successful first outcome with the marketplace: finding a reviewed extension, checking the evidence, and installing it with explicit confirmation.

## What you need

Before you start, make sure you have:

- a GitHub Copilot environment that supports agent extensions;
- network access to the hosted catalog;
- either APM or a compatible `npx skills` fallback when installing a published package;
- the permission to install or register a candidate in the current workspace.

## Step 1: install the companion workflows

The repository includes two marketplace companion skills for GitHub Copilot:

- `bcgov-find-extension` — searches catalog entries and shows evidence before installation guidance.
- `bcgov-create-extension` — turns an idea or selected files into a draft package and submission workflow.

Use the published marketplace revision. APM is preferred because it records an installer manifest and lockfile.

```bash
apm install \
  bcgov/agent-marketplace/skills/community/bcgov-find-extension#<published-commit-sha> \
  bcgov/agent-marketplace/skills/community/bcgov-create-extension#<published-commit-sha> \
  --target copilot
```

If APM is not available, use the catalog-pinned Skills CLI fallback:

```bash
npx skills@<catalog-installer-version> add \
  https://github.com/bcgov/agent-marketplace/tree/<published-commit-sha> \
  --skill bcgov-find-extension --skill bcgov-create-extension \
  --agent github-copilot -y
```

## Step 2: ask the finder for a result

From a workspace where the companion is installed, ask Copilot something like:

- “Find me a reviewed BC Gov extension for hardening GitHub Actions.”
- “Find a reviewed package for deployment guidance for OpenShift.”

The finder searches the published catalog and presents the exact record, source revision, and evidence path. It does not silently install anything.

## Step 3: inspect the evidence

Before installation, review the record and confirm that:

- the extension is active and reviewed;
- the source repository and revision are correct;
- the file inventory and digest match the package state;
- the capabilities and policy results are consistent with the use case.

This is the point where you decide whether the package is a match for the task.

## Step 4: confirm installation

The marketplace expects an explicit confirmation step before installation guidance is provided.

The preferred route is APM because it records `apm.yml` and `apm.lock.yaml`. If that is not available, the fallback installer may write `skills-lock.json` in the local project.

The important part is not the lockfile format itself. The important part is that installation is tied to a named, reviewed, immutable package revision and a project-local record of what was installed.

## Step 5: use the creator workflow

If you have an idea for a new extension or a workflow that is missing from the catalog, use the creator companion.

Ask Copilot:

> Turn this workflow idea into a BC Gov extension and prepare a draft pull request.

The creator workflow will: 

- identify the task and extension type;
- search for an equivalent in the public catalog;
- scaffold a candidate package in an isolated draft path;
- inspect public output and capabilities;
- present a preview before proceeding;
- create a signed draft pull request only after confirmation.

## Step 6: understand the scope

This repo is a marketplace for agent extensions, and skills are the first public extension type in the catalog. The broader platform and metadata model are designed to support additional extension families as the catalog grows, but the current release is intentionally conservative and published records are validated as a specific package type.

## Completion checklist

A successful first use is when you can do all of the following:

- find a reviewed or candidate extension;
- inspect the evidence and source revision;
- confirm the installation path deliberately;
- understand the difference between reviewed catalog entries and unreviewed candidates;
- know that this repo is broader than skills while still operating within a controlled MVP scope.

That is the baseline workflow for working with the marketplace safely.
