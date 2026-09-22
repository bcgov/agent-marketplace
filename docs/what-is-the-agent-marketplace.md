# What this marketplace is

This repository is a BC Gov marketplace for reviewed agent extensions. It is designed to help teams discover, inspect, and install trusted extension packages with clear provenance and review evidence.

The core idea is simple: an extension should not be installed on trust alone. Every published record is tied to a specific source repository, an immutable revision, a file inventory, and a policy result. When something is reviewed, the evidence is attached to that exact package state and not to a later change.

## The bigger picture

This is not just a skills catalog. At the platform level, the repository is built around the broader idea of an extension marketplace for GitHub Copilot and related agent workflows.

Skills are the first public extension type covered by the current marketplace implementation, but the repository metadata, catalog model, approval flow, and discovery policy are designed to accommodate other extension classes as the catalog matures. In other words, skills are the currently published and validated surface area, not the only extension family the system is prepared to support.

That distinction matters because it keeps the repo honest:

- the public catalog can currently hold reviewed skill packages;
- the underlying model is not limited to a single extension form;
- future catalog entries may include prompts, instructions, or agent-style extensions under the same trust and provenance controls.

## What the marketplace does

The marketplace helps users do three things:

1. discover reviewed or candidate extensions;
2. inspect the exact source and evidence before installation;
3. install a pinned, immutable revision instead of an unnamed or drifting dependency.

It also gives maintainers a controlled path for review, quarantine, publication, and rollback.

## Trust and evidence model

Published and candidate entries are expected to carry the following signals:

- a canonical source repository;
- an immutable revision or commit SHA;
- a package path and file inventory;
- a deterministic package-tree digest;
- declared capabilities or public output;
- a policy or scanner result;
- human review evidence for the exact bytes in question.

This is intentionally stricter than a plain “download a package and run it” flow. The marketplace treats the package as data, validates it, and only then allows the record to appear as a trusted or reviewed option.

## What is currently in scope

The current public implementation in this repo focuses on GitHub Copilot-compatible extension packages under the `skills/` layout, with a clear `SKILL.md` contract and validation path.

That does not mean the marketplace concept is limited to skills in the middle of the architecture. The broader operating model is extension-agnostic, while the published MVP remains intentionally narrow and safe.

## What is intentionally out of scope

The repository explicitly does not try to support:

- silent automatic execution;
- hidden installation or unreviewed remote code execution;
- review fields set by authors;
- untrusted or unscanned candidate packages being treated as approved.

The marketplace is designed around explicit confirmation, source provenance, and repository-backed review.

## In one sentence

This repository is a GitHub-backed marketplace for trusted agent extensions, with skills as the first fully implemented public catalog type and a broader extension model behind the scenes.
