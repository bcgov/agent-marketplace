# BC Gov Agent Marketplace

The marketplace helps people discover, assess, contribute, and use reusable agent assets with clear provenance and review evidence.

## Language

**Agent asset**:
A reusable piece of agent guidance or configuration published in the marketplace. The supported kinds are skills, instructions, prompts, and agents.

**Extension**:
An agent asset packaged with its marketplace identity, provenance, capabilities, lifecycle, and policy evidence.
_Avoid_: Plugin, tool (unless referring to an executable integration)

**Skill**:
A reusable set of instructions that an agent can discover and apply to a task.
_Avoid_: Prompt, instruction set

**Instruction**:
Persistent guidance that shapes an agent's behavior within a defined scope.
_Avoid_: Skill, prompt

**Prompt**:
A reusable request for one focused interaction or deliverable.
_Avoid_: Skill, instruction

**Agent**:
A defined assistant role with a focused responsibility and explicit operating boundaries.
_Avoid_: Skill, prompt

**Harness**:
An agent client or platform through which a person discovers or uses agent assets.
_Avoid_: Model (a model may be used by a harness but is not the harness)

**Compatibility claim**:
Author-declared information about harness readiness and known exclusions. An absent exclusion is not a marketplace runtime-test result.
_Avoid_: Verified compatibility, certification

**Community**:
The general-purpose marketplace category for extensions that do not belong to a specialty.
_Avoid_: Unreviewed (Community extensions still pass automated checks)

**Specialty**:
A domain-specific marketplace category whose extensions require human review before availability.
_Avoid_: Tag, topic

**External source**:
A third-party marketplace or catalogue that marketplace maintainers have approved for discovery. Its content is not published by this marketplace and is not trusted on that basis.
_Avoid_: Community marketplace, federated marketplace

**Auto-checked**:
The exact extension revision passed automated format and policy checks; no human review is implied.
_Avoid_: Approved, verified safe

**Marketplace reviewed**:
Named reviewers assessed the exact extension revision and package digest.
_Avoid_: Safe, secure, certified

**BC Gov GitHub member**:
A person whose GitHub account belongs to the `bcgov` organization. This is the marketplace's contributor-eligibility proxy, not proof of employment by the Province of British Columbia.
_Avoid_: Verified BC Gov staff

**Manifest**:
The author's declaration of an Extension's marketplace metadata, contacts, access and lifecycle.
_Avoid_: Receipt, runtime configuration

**Catalogue**:
The marketplace's published collection of Extension metadata, lifecycle notices and revision-specific evidence.
_Avoid_: Catalog, package registry

**Stable Extension identity**:
The reserved identity of an Extension determined by its type and name, independent of Specialty ownership.
_Avoid_: Package path, display name

**Tombstone**:
A retained removed Extension record that reserves its identity and explains its withdrawal or replacement.
_Avoid_: Deleted identity

**Snapshot**:
A particular accepted version of the Catalogue whose source and exact bytes remain identifiable independently of the current site.
_Avoid_: Latest source, site build

**Declared access**:
The author's account of the filesystem, network, commands, environment, secret names and data classes an Extension may use.
_Avoid_: Detected access, safety certification

**Recognized deterministic finding**:
An automated observation produced by an explicit marketplace checking rule, with coverage limited to that rule.
_Avoid_: Complete capability analysis

**Policy route**:
The handling an Extension change requires under marketplace eligibility, ownership and lifecycle policy; it does not establish completed human review or runtime safety.
_Avoid_: Review evidence, approval
