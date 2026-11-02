# What this marketplace is

This repository is a BC Gov marketplace for skills, prompts, instructions, and agent definitions. It is designed to help teams discover and inspect agent assets with clear provenance, capability declarations, and review evidence.

The core idea is simple: an extension should not be installed on trust alone. Every published record is tied to a specific source repository, an immutable revision, a file inventory, and a policy result. When something is reviewed, the evidence is attached to that exact package state and not to a later change.

## The bigger picture

The public catalog supports four declarative asset types: skills, prompts,
instructions, and agent definitions. Each has a canonical package format and
uses the same provenance, capability, and review controls. Skills can use the
marketplace installer; the other types have explicit, harness-specific manual
import guidance.

## What the marketplace does

The marketplace helps users do three things:

1. discover reviewed or candidate extensions;
2. inspect the exact source and evidence before installation;
3. install a pinned, immutable skill revision or manually import another asset
   after reviewing its source and target.

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

The public implementation supports four declarative formats under
`skills/`, `prompts/`, `instructions/`, and `agents/`. Package shape and
metadata are validated, but the marketplace does not claim per-package runtime
compatibility or model-quality testing. Authors can declare harnesses where an
asset is not ready; an empty exclusion list is not a test result.

GitHub `bcgov` organization membership is the contributor eligibility proxy.
It is not proof of employment. Readers may browse and retrieve public packages
without being members.

## What is intentionally out of scope

The repository explicitly does not try to support:

- silent automatic execution;
- hidden installation or unreviewed remote code execution;
- review fields set by authors;
- untrusted or unscanned candidate packages being treated as approved.

The marketplace is designed around explicit confirmation, source provenance, and repository-backed review.

## In one sentence

This repository is a GitHub-backed marketplace for four declarative agent
asset types, with trust evidence attached to immutable package revisions.
