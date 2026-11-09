# Research Findings: Evidence Published by Approved External Sources for Individual Extensions

*(bcgov/agent-marketplace issue #23)*

## 1. Summary

I investigated one representative item from each of the four **External sources** currently listed in `config/marketplace.yaml`: `web-design-guidelines` (vercel-labs/agent-skills, via **skills.sh**), `azure-ai-contentsafety-py` (**Microsoft Agent Skills**), `frontend-design`/`docx` (**Anthropic Skills**), and `documentation-writer` (**Awesome Copilot**). The most significant finding is that **skills.sh operates a cross-source, machine-readable, named-vendor security-audit API** (`ath`/"Gen", Socket, Snyk) that returns results keyed only by `source` repo + skill-name slug — **not by commit SHA or content hash** — and the same API returns data for items published through the *other three* sources too (since skills.sh indexes their repos), even though those sources' own catalog pages (`microsoft.github.io/skills`, GitHub repo pages) do not themselves surface any such audit. I found a live divergent result: Anthropic's own `docx` skill shows Socket = **critical risk, 2 alerts** while Snyk says "low" and "ath"/Gen says "safe" for the same item — illustrating that even where audits exist, they are per-provider, not reconciled, and not bound to an installable content digest. **Awesome Copilot** is the only source with a documented, per-PR automated risk scanner (`pr-risk-scan.yml` / `eng/pr-risk-scan.mjs`) that runs against the literal diff of the item being contributed, plus a formal external-plugin intake requiring an **immutable commit SHA/ref**, but its scan artifacts are ephemeral (1-day CI retention) and not republished per item afterward. **Microsoft Agent Skills** and **Anthropic Skills** have no item-level security audit of their own; both rely on generic repo-level processes (Microsoft: `SECURITY.md` pointing to Microsoft's general coordinated-disclosure process; Anthropic: no `SECURITY.md`/`CONTRIBUTING.md` found at all, and the repo is explicitly disclaimed as "demonstration and educational purposes only").

---

## 2. skills.sh (Agent Skills Directory — vercel-labs/skills + vercel-labs/agent-skills)

**Representative item**: `web-design-guidelines` from `vercel-labs/agent-skills`, listed on the catalog at `https://www.skills.sh/vercel-labs/agent-skills/web-design-guidelines`, and referenced as the canonical install example in the CLI's own README.

### Revision/digest pinning
- Default install (`npx skills add vercel-labs/agent-skills`) resolves the repo's default branch (`main`) — a mutable ref. `docs/commands.md` shows sources can optionally be pinned via a `tree/<branch-or-tag>/...` URL or (for Azure Repos) `?version=GBmain`, but the default GitHub shorthand form (`owner/repo`) is **not** pinned to a commit. (`vercel-labs/skills:docs/commands.md`, README quick-start)
- On install, the CLI writes `skills-lock.json` with a `computedHash` field: a **SHA-256 hash of the actual on-disk file contents of the skill folder**, used only to detect drift on `skills update`/`skills check` — it is a content digest, not a git commit SHA. (`vercel-labs/skills:src/local-lock.ts:30-46`, confirmed in this repo's own `skills-lock.json`). The companion global lock uses a **GitHub tree SHA** (`skillFolderHash`) fetched via the Trees API, again a content-tree digest rather than a commit SHA pin for future installs. (`vercel-labs/skills:AGENTS.md` "Update Checking System" section)
- **Conclusion**: skills.sh/CLI detects *content drift after install* via a digest, but does **not** pin installs to an immutable commit by default; a repo maintainer force-pushing/rewriting `main` after your install would not be caught unless you later run `skills check`.

### Item-level audit vs. source-level review vs. popularity
- **(a) Item-level security audit — EXISTS, confirmed live.** `vercel-labs/skills:src/telemetry.ts:70-110` defines `fetchAuditData()`, which calls `https://www.skills.sh/tele/audit?source=<owner/repo>&skills=<slug>` and returns a `PartnerAudit` record per skill with fields `risk`, `alerts`, `score`, `analyzedAt`. I queried this live endpoint directly (GET only, no install/execution performed):
  ```
  GET https://www.skills.sh/tele/audit?source=vercel-labs/agent-skills&skills=web-design-guidelines
  → {"web-design-guidelines":{
       "ath":   {"risk":"safe","analyzedAt":"2026-09-15T09:11:58.047Z"},
       "socket":{"risk":"safe","alerts":0,"score":90,"analyzedAt":"2026-03-18T16:47:53.805Z"},
       "snyk":  {"risk":"low","analyzedAt":"2026-09-15T09:11:42.193108+00:00"}}}
  ```
  - Three named providers are shown at install time in a "Security Risk Assessments" CLI table with columns "Gen" (key `ath` in the API — **provider identity behind "ath"/"Gen" is not documented in any primary source I found**, so I cannot confirm who runs it), "Socket" (industry-known Socket.dev supply-chain scanner), and "Snyk" (industry-known Snyk.io vendor). (`vercel-labs/skills:src/add.ts:124-199`)
  - **Not bound to exact install revision**: the audit lookup key is only `source` (owner/repo string) + skill slug — there is no commit SHA, tag, or content-hash parameter in the request, and the response carries only `analyzedAt` (when the provider last scanned), not which commit/tree it scanned. If the skill's content changes after `analyzedAt` without a new audit run, nothing in the CLI or API invalidates the stale "safe"/"low" result, and the `computedHash` content-digest mechanism (above) is never cross-checked against audit data. (`vercel-labs/skills:src/add.ts:2079-2100, 2397-2416`)
  - **Explicitly advisory, not a gate**: audit fetch failures are silently swallowed ("security info is advisory only") and never block installation. (`vercel-labs/skills:src/add.ts:2415-2416`)
  - **Cross-source reach**: I confirmed the same `/tele/audit` endpoint returns results for items from the *other three* approved sources too, since skills.sh indexes their repos independently of this project's marketplace.yaml:
    ```
    GET ...?source=microsoft/skills&skills=azure-ai-contentsafety-py → ath:safe, socket:safe(0 alerts), snyk:low
    GET ...?source=github/awesome-copilot&skills=documentation-writer → ath:safe, socket:safe(0 alerts), snyk:low
    GET ...?source=anthropics/skills&skills=docx → ath:safe, socket:"risk":"critical","alerts":2, snyk:low
    ```
    The `docx` result is a live, real divergence: Socket flags a **critical, 2-alert** finding on the exact skill Anthropic itself ships and documents as powering "Claude's document capabilities," while Snyk and "ath" simultaneously report low/safe. **No report link or finding detail accompanies any of these results** — only a categorical risk label, alert count, and timestamp; the only pointer given is a generic `https://skills.sh/<source>` page, which (per my fetch of the `web-design-guidelines` catalog page) does **not** display this audit table at all.
- **(b) Source-level review process — thin/absent.** `vercel-labs/skills` (the CLI repo) has **no SECURITY.md, no CONTRIBUTING.md, no issue template** (confirmed via GitHub's community-profile API: `"contributing": null, "issue_template": null`, health 50%). `vercel-labs/agent-skills` (the content repo) likewise has none (health 37%, same nulls). There is no CODEOWNERS or documented PR-approval policy in either repo.
- **(c) Popularity signals — present, clearly separated from security.** The `skills.sh` catalog ("Skills Leaderboard") and individual pages display **install counts** ("863.9K", "3.7M total", etc.) prominently; these are usage/download counts, explicitly not security signals, and are visually distinct from the (CLI-only, not web-shown) audit table.

### Incident-removal process
- No documented delisting/incident-removal mechanism found in either repo. GitHub's generic "Report content" feature is enabled (`"content_reports_enabled": true`) on `vercel-labs/skills`, which is a platform-wide abuse mechanism, not a project-specific security incident process.

### Human/security intake
- No CONTRIBUTING.md/CODEOWNERS in either repo. Skills are discovered automatically from whatever directory structure exists in a target repo (`vercel-labs/skills:docs/creating-skills.md`); there is no submission/review workflow for an individual skill to be "listed" beyond existing in a public GitHub repo that skills.sh's crawler indexes.

### Machine-readable interface
- `GET https://www.skills.sh/tele/audit?source=<owner/repo>&skills=<slug1,slug2>` returns JSON audit data (undocumented but discoverable from source and directly queryable — demonstrated above).
- `skills add <repo> --list` / `npx skills find <query>` are CLI-only, not an HTTP API for third parties.
- No RSS/Atom feed found.

### Gaps/uncertainties
- Identity/methodology of the "ath" ("Gen") audit provider is **not documented anywhere I could find** — it's an unexplained key/label.
- I could not find any UI on `www.skills.sh` web pages that surfaces the audit table (it appears only in the CLI's terminal output and the JSON install summary) — the "Details:" link the CLI prints (`https://skills.sh/<source>`) does **not**, on the page I fetched, show audit results.
- No official API documentation exists for `/tele/audit`; everything here was reverse-engineered from TypeScript source and confirmed by live querying.

---

## 3. Microsoft Agent Skills (microsoft/skills)

**Representative item**: `azure-ai-contentsafety-py`, listed in the "Skill Catalog" table of `microsoft/skills:README.md` and browsable at `https://microsoft.github.io/skills/`.

### Revision/digest pinning
- `README.md` quick start: `npx skills add microsoft/skills` — same skills.sh CLI as above, same caveat: resolves default branch `main`, not pinned to a commit unless the user manually specifies a `tree/<ref>` URL. (`microsoft/skills:README.md` "Quick Start" / manual-install section)
- The skill itself is a **symlink**: `.github/skills/azure-ai-contentsafety-py` → `../plugins/azure-sdk-python/skills/azure-ai-contentsafety-py` (confirmed via GitHub Contents API, `type: "symlink"`), i.e., content is synced in from an upstream plugin source and is itself subject to that upstream sync's own (undocumented, from what I could find) revision discipline.
- No digest/hash file equivalent to skills.sh's `skills-lock.json` found at the repo level for consumers who `git clone` manually.

### Item-level audit vs. source-level review vs. popularity
- **(a) Item-level security audit — NOT found.** The repo runs two CI workflows badged in the README — "Evals & Tests" (`test-harness.yml`) and "Copilot SDK Tests" (`skill-evaluation.yml`) — but both are **quality/functional evaluation harnesses** (pass/fail scenario testing of whether the skill produces good output), explicitly distinguished in the workflow itself as "smoke test using mock responses" vs. a nightly "real Copilot SDK" run; neither is a security scan, and their result artifacts are uploaded with GitHub Actions default retention (not surfaced per-skill on the public site). (`microsoft/skills:.github/workflows/test-harness.yml`, `.github/workflows/skill-evaluation.yml`)
  - As shown in §2, the *same skill content* is independently audited by skills.sh's provider trio when queried via `source=microsoft/skills` — but this is an artifact of skills.sh's own crawling, not something `microsoft/skills` or `microsoft.github.io/skills` publishes, links to, or references anywhere I found.
- **(b) Source-level contribution/review process — exists, team/individual-based, not security-specific.** `.github/CODEOWNERS` assigns a default owner (`@thegovind`) for everything, with path-specific owners for certain plugins/skills (e.g., `.github/skills/entra-agent-id/ @ArLucaID @rbinrais @thegovind`) and flags `.github/workflows/` and `.github/scripts/` as "security-sensitive," implying required review by the maintainer for CI/automation changes — but this is ordinary PR-review ownership, not a documented security-audit step for skill *content*. (`microsoft/skills:.github/CODEOWNERS`) GitHub's community-profile API shows **no CONTRIBUTING.md, no issue template, no pull-request template** (`"contributing": null, "issue_template": null`, health 62%).
- **(c) Popularity signals** — the Skill Explorer (`https://microsoft.github.io/skills/`) lists "Showing 174 skills" with category tags but, unlike skills.sh, I did not find install-count/star numbers surfaced per-item on this particular page.

### Incident-removal process
- `SECURITY.md` exists and is Microsoft's **standard organization-wide boilerplate**: "Please do not report security vulnerabilities through public GitHub issues... review the latest guidance for Microsoft repositories at https://aka.ms/SECURITY.md." This is a generic Microsoft-org vulnerability-reporting pointer, not a skill-specific delisting/incident process. (`microsoft/skills:SECURITY.md`)
- No skill-specific removal/delisting mechanism documented.

### Human/security intake
- CODEOWNERS-based review (above) is the only documented gate; no CONTRIBUTING.md was found via the GitHub community-profile API or by direct path probing of the repo root and `docs/` tree (`docs/` only contains website build assets, not a written contribution guide).

### Machine-readable interface
- `https://microsoft.github.io/skills/llms-full.txt` / `llms.txt` exist (confirmed in root listing) but — **important gap** — when I fetched `https://microsoft.github.io/skills/llms.txt`, its content was **generic Microsoft Foundry product documentation** (links to `learn.microsoft.com/.../azure/ai-foundry/...`), not a machine-readable index of the skills catalog itself. This appears to be a naming collision/mismatch between the skills site and Foundry docs content, not a skill-level machine-readable index.
- No dedicated JSON skill index was found at a guessable path; the skill catalog table in `README.md` is the closest machine-parseable listing (a Markdown table), not a formal API/feed.

### Gaps/uncertainties
- Could not verify whether `microsoft.github.io/skills/` client-side app fetches a JSON index from an endpoint I didn't guess correctly; I did not find one via root-listing or page inspection in the time available.
- Could not determine the review/intake process (if any) for the upstream `plugins/azure-sdk-python` source that `azure-ai-contentsafety-py` is symlinked from — out of scope of what I could verify from `microsoft/skills` alone.

---

## 4. Anthropic Skills (anthropics/skills)

**Representative items**: `frontend-design` (used as a cross-link example from skills.sh's own page for `web-design-guidelines`) and `docx` (one of the production skills Anthropic states power Claude's own document capabilities).

### Revision/digest pinning
- Primary install paths documented in `README.md`:
  - Claude Code plugin marketplace: `/plugin marketplace add anthropics/skills`, then `/plugin install document-skills@anthropic-agent-skills`. The plugin manifest `.claude-plugin/marketplace.json` declares each plugin's `source` as `"./"` (the marketplace repo root) with no `ref`/`sha` field. (`anthropics/skills:.claude-plugin/marketplace.json`)
  - Per Anthropic's own Claude Code docs on plugin marketplaces (`code.claude.com/docs/en/plugin-marketplaces`), a git-hosted marketplace is registered by repository, and I found **no documented mechanism in that doc page for pinning a marketplace install to an immutable commit/tag** — the described flow tracks whatever the marketplace source currently contains. This is the opposite of Awesome Copilot's explicit immutable-SHA requirement (see §5).
  - `npx skills add anthropics/skills` via skills.sh — same mutable-branch-by-default caveat as §2/§3.
- **No commit-SHA or digest pinning mechanism documented in the `anthropics/skills` repo itself.**

### Item-level audit vs. source-level review vs. popularity
- **(a) Item-level security audit — NOT found inside this repo.** No CI workflows, no security-scan tooling, and no per-skill metadata field for audit status exist in `anthropics/skills` (repo root contains only `.claude-plugin/`, `.gitignore`, `README.md`, `THIRD_PARTY_NOTICES.md`, `skills/`, `spec/`, `template/` — confirmed via GitHub Contents API). `THIRD_PARTY_NOTICES.md` is a third-party **license** attribution file (e.g., for `imageio`, BSD-licensed), unrelated to security auditing.
  - As shown in §2, skills.sh's external audit API *does* return results for this repo's skills when queried directly (e.g., `docx` → Socket "critical", 2 alerts) — but this is produced and surfaced entirely by the separate skills.sh source, not by `anthropics/skills` or `github.com/anthropics/skills` itself, and is not linked from anywhere in the Anthropic repo.
- **(b) Source-level contribution/review process — essentially absent.** GitHub's community-profile API returns health 25% with **every field null** (`contributing: null, issue_template: null, pull_request_template: null, code_of_conduct: null, license: null`[repo-level detection — note individual skills like `frontend-design` do carry their own `LICENSE.txt`]). The README's only quality statement is a **disclaimer**, not a review process: *"These skills are provided for demonstration and educational purposes only... Always test skills thoroughly in your own environment before relying on them for critical tasks."* (`anthropics/skills:README.md`, "Disclaimer" section)
- **(c) Popularity signals** — the repo embeds a skills.sh install-count badge (`[![skills.sh](https://skills.sh/b/anthropics/skills)]`) at the top of its README, i.e., it inherits skills.sh's popularity display but shows no popularity data of its own on GitHub.

### Incident-removal process
- **No SECURITY.md found** in `anthropics/skills` (confirmed via community-profile API and direct path probing). No documented vulnerability-reporting or delisting process exists in this repository. (Anthropic's broader organizational security-disclosure process, if any, is not referenced from this repo and was out of scope to verify as a "primary source" tied to this specific catalog.)

### Human/security intake
- **No CONTRIBUTING.md.** The README explains the SKILL.md format for "Creating a Basic Skill" but documents no submission, review, or approval workflow for getting a skill *into* this repository — it reads as primarily Anthropic's own curated/first-party content rather than an open external-contribution pipeline.

### Machine-readable interface
- None found: no JSON index, API, or feed for the catalog. The GitHub repo file tree (`skills/<name>/SKILL.md` with YAML frontmatter) is structured/parseable but is not an advertised "catalog API" — it's just the source layout.

### Gaps/uncertainties
- I could not verify Anthropic's organization-wide security-disclosure process (e.g., a HackerOne program) because nothing in `anthropics/skills` links to one; absence-of-evidence here is explicitly about *this repository*, not a claim that Anthropic has no security process anywhere.
- Could not confirm whether `/plugin install` in Claude Code records an installed commit/tag locally (analogous to skills.sh's lock file) — this would require inspecting Claude Code's own install-state format, which is outside this repo and not something I could access as a primary source within scope.

---

## 5. Awesome Copilot (github/awesome-copilot)

**Representative item**: `documentation-writer` skill (`skills/documentation-writer/SKILL.md`) — notably, this is the exact skill already installed in this very `ai-marketplace` repo per its own `skills-lock.json` (`"documentation-writer": {"source": "github/awesome-copilot", ...}`), giving a direct real-world cross-reference.

### Revision/digest pinning
- Direct/native skills (like `documentation-writer`, contributed as PRs into `skills/`) are installed from whatever commit is current on `main` at install time via `npx skills add github/awesome-copilot` or `copilot plugin install <name>@awesome-copilot` — same mutable-default caveat as the other skills.sh-indexed sources (§2).
- **For external plugins specifically** (third-party repos registered into `plugins/external.json`), the intake process is materially stricter: the GitHub Issue Form `.github/ISSUE_TEMPLATE/external-plugin.yml` **requires** the submitter provide an immutable **ref and/or a full 40-character commit SHA** ("The ref and/or sha I provided is immutable (release tag and/or full 40-character commit SHA), not a branch" — a required checklist item), and the automated quality-gate pipeline (`eng/external-plugin-quality-gates.mjs`) literally `git fetch --depth=1 origin <that exact sha/ref>` and `git checkout --detach FETCH_HEAD` before running any checks — i.e., **the review is bound to the exact pinned revision the submitter declared**. (`github/awesome-copilot:.github/ISSUE_TEMPLATE/external-plugin.yml`; `eng/external-plugin-quality-gates.mjs:107-135`) This is the only one of the four sources where I found an explicit, enforced, documented commit-pinning requirement tied to a review step.
- `eng/external-plugin-validation.mjs` further defines a `publicSubmission` policy requiring `requireImmutableLocator: true` for public submissions (vs. a looser `marketplace` policy for first-party entries that only warns if missing).

### Item-level audit vs. source-level review vs. popularity
- **(a) Item-level security audit:**
  - **"PR Risk Scan — Gate"** (`.github/workflows/pr-risk-scan.yml`, logic in `eng/pr-risk-scan.mjs`) runs on every PR touching `skills/**`, `agents/**`, `workflows/**`, `plugins/**`, `hooks/**`, `instructions/**` and statically scans **the literal diff of the changed item** for risk patterns: guardrail-bypass language ("ignore previous instructions", "bypass safety"), remote-shell-pipe execution (`curl ... | sh`), auto-yes package execution (`npx -y`), dynamic package execution, and unpinned dependency versions. Each finding carries a `rule_id`, `severity` (high/medium/info), file/line, and a suggested fix. (`eng/pr-risk-scan.mjs:70-130`)
    - This **is** genuinely item-level (scoped to the exact files in the diff) and automated, but: it is explicitly labeled a **"soft-gate"** ("This is a soft-gate report... inspect the workflow logs for diagnostics"), it is a custom in-house regex scanner (not a named third-party security vendor), and its output is uploaded as a GitHub Actions artifact with **`retention-days: 1`** — i.e., **the report is not durably published or linkable per item after that window**, and there is no evidence it is republished to the public website (I grepped `eng/generate-website-data.mjs` for any reference to "scan"/"gate"/"vally"/"lint" and found **none** — confirming the website does not surface these results).
  - **"Vally Lint — PR Gate"** (`.github/workflows/skill-check.yml`) runs `npx @microsoft/vally-cli lint <skill_dir>` on changed skill directories — a structural/content linter for `SKILL.md` (frontmatter validity, formatting), not a security scanner per se, also only run at PR time with no persisted public report.
  - For external plugins, `eng/external-plugin-quality-gates.mjs` runs the vally linter plus `plugin.json` schema validation plus a smoke test **against the cloned, pinned commit** — the closest thing to a genuinely revision-bound item-level check among all four sources, though again it is an in-house pipeline, not a named external security-audit vendor, and I found no evidence the resulting pass/fail is published as a durable, linkable report (vs. transient PR-comment output via `external-plugin-pr-quality-gates.yml`).
  - As shown in §2, skills.sh's external `/tele/audit` API also returns results for `documentation-writer` (ath:safe, socket:safe/0 alerts, snyk:low) — again, this is produced by a *different* approved source (skills.sh), not by `github/awesome-copilot` itself.
- **(b) Source-level contribution/review process — the strongest of the four sources.** `CONTRIBUTING.md` documents explicit accept/reject criteria, including an explicit **security-relevant exclusion list**: "Compromise Security: Instructions designed to bypass security policies, exploit vulnerabilities, or weaken system security," "Enable Malicious Activities," "Exploit Weaknesses," plus a specific rule that public external plugins **must** go through the review workflow rather than a direct PR to `plugins/external.json`. (`github/awesome-copilot:CONTRIBUTING.md`, "What We Don't Accept") Review routing is formalized in `docs/maintainers/review-routing.md` with named reviewer-team pools per content path (`CODEOWNERS`: `/skills/` → `@github/awesome-copilot-content-reviewers`, `/plugins/` → `@github/awesome-copilot-plugin-reviewers`), SLA timers (`sla.first_review_business_days`, default 2 business days) and automated escalation. This is a genuine, documented **human-review** process — but it is a review *of the contribution* (does it meet repo policy, pass lint/scan gates), not a named, independent, per-item security audit report.
- **(c) Popularity signals** — `.all-contributorsrc`/contributor badges exist at the repo level (contributor count), but I did not find per-skill install/star counts surfaced on the GitHub repo pages themselves (the public website `awesome-copilot.github.com` may show usage metrics per item; I was unable to load a working item-detail URL for `documentation-writer` to confirm — see Gaps below).

### Incident-removal process
- `SECURITY.md` is **GitHub's standard organization-wide boilerplate**: do not report vulnerabilities via public issues; email `opensource-security@github.com`; references GitHub's bug-bounty scope/safe-harbor policy. (`github/awesome-copilot:SECURITY.md`) This is a generic GitHub-org vulnerability-reporting channel, not an awesome-copilot-specific "flag this skill" or delisting mechanism.
- No skill-specific issue template for "report a problematic skill/instruction" was found (only `external-plugin.yml` exists under `.github/ISSUE_TEMPLATE/`); a generic blank-issue path presumably exists via GitHub defaults but I found no dedicated template.
- Workflow names suggest an ongoing moderation/lifecycle apparatus — `resource-staleness-report.yml`, `duplicate-resource-detector.yml`, `review-escalation.yml` — but I did not deep-dive their logic beyond confirming their existence; I cannot confirm whether any of these constitute a "post-incident removal" path versus pure staleness/duplicate-content housekeeping.

### Human/security intake
- `CONTRIBUTING.md` (full process for Instructions/Agents/Skills/Canvas/Plugins/Hooks/Workflows), `CODEOWNERS` (team-based ownership per content path), `pull_request_template.md` (exists per community-profile API), and `AGENTS.md` (AI-agent contribution guidance) together form the most complete documented intake process of the four sources.

### Machine-readable interface
- `https://awesome-copilot.github.com/llms.txt` is a real, working, structured machine-readable index (confirmed by fetch) listing agents/instructions/skills/learning-hub content with per-item descriptions and URLs — the README explicitly advertises this: *"Using this collection in an AI agent? A machine-readable `llms.txt` is available with structured listings of all agents, instructions, and skills."* (`github/awesome-copilot:README.md`, "Learning Hub" section) I confirmed `documentation-writer` appears in it (2 matches via grep).
- I could not load a working per-item detail page at a guessed URL (`awesome-copilot.github.com/skills/documentation-writer` → 404); the correct item-detail URL pattern was not confirmed.

### Gaps/uncertainties
- I did not confirm the exact live item-detail URL pattern on `awesome-copilot.github.com`, so I cannot confirm/deny whether popularity metrics or any audit badge are shown there per item — flagged as unverified.
- I did not deep-read `resource-staleness-report.yml`, `duplicate-resource-detector.yml`, or `review-escalation.yml` logic in full; their role in any "incident removal" scenario is inferred from naming only, not confirmed from their full source.
- `pr-risk-scan.yml` and `skill-check.yml` artifacts' extremely short retention (1 day; vally results retention unconfirmed but likely similarly short) means that **by the time an Extension is reviewed days/weeks after merge, no durable per-item scan report exists to point to** — this is an explicit, important gap distinct from the *existence* of the scan itself.

---

## 6. Cross-Source Comparison Table

| Source | (a) Item-level security audit exists? | Tied to exact install revision? | (b) Source-level contribution/review process? | Incident-removal process documented? | Machine-readable interface |
|---|---|---|---|---|---|
| **skills.sh** (vercel-labs/skills) | **Yes** — live `ath`/Socket/Snyk audit API, confirmed by direct query | **No** — keyed by repo+skill-name only, no SHA/digest param; `analyzedAt` timestamp but no content binding | **No** — no CONTRIBUTING.md/SECURITY.md/CODEOWNERS in either `vercel-labs/skills` or `vercel-labs/agent-skills` (community-profile health 50%/37%) | **No** project-specific process; only generic GitHub "report content" flag enabled | **Yes** (undocumented) — `/tele/audit?source=&skills=` JSON endpoint |
| **Microsoft Agent Skills** (microsoft/skills) | **No** — only quality/eval CI (`test-harness.yml`, `skill-evaluation.yml`), not security; audited only incidentally via the *separate* skills.sh index | N/A (no item-level audit of its own) | **Partial** — CODEOWNERS with per-path/per-plugin owners; no CONTRIBUTING.md/issue template (health 62%) | Generic Microsoft-org `SECURITY.md` pointing to `aka.ms/SECURITY.md`; no skill-specific delisting process | **Partial/misleading** — `llms.txt`/`llms-full.txt` exist but actual content fetched was unrelated Foundry product docs, not a skill index |
| **Anthropic Skills** (anthropics/skills) | **No** — nothing in-repo; audited only incidentally via the *separate* skills.sh index (e.g., `docx` shows Socket "critical") | N/A | **No** — community-profile health 25%, all fields null (no CONTRIBUTING, no CODEOWNERS); README carries an explicit "demonstration only" disclaimer instead | **No SECURITY.md found**; no documented vulnerability-reporting or removal process in this repo | **No** — no JSON/API/feed found |
| **Awesome Copilot** (github/awesome-copilot) | **Yes, but soft-gate & ephemeral** — `pr-risk-scan.yml`/`eng/pr-risk-scan.mjs` (regex-based, in-house, PR-diff-scoped) + `vally` lint; 1-day artifact retention, not republished per item; also incidentally covered by skills.sh's separate audit for native skills | **Yes, for external plugins only** — intake issue template requires an immutable commit SHA/ref, and `external-plugin-quality-gates.mjs` clones and checks exactly that pinned commit. Native `skills/` contributions are not pinned at install time (mutable `main`) | **Yes — strongest of the four** — `CONTRIBUTING.md` with explicit security-exclusion criteria, `CODEOWNERS` with named reviewer teams per path, documented SLA/escalation in `docs/maintainers/review-routing.md`, PR template | Generic GitHub-org `SECURITY.md` (`opensource-security@github.com`); no awesome-copilot-specific delisting issue template found, though staleness/duplicate-detector workflows exist (role in incident response unconfirmed) | **Yes** — working `llms.txt` structured index confirmed live, includes `documentation-writer` |

**Popularity/stars/downloads (c)** exist as a visible, non-security signal on skills.sh (install counts, prominently displayed per item) and are embedded via badge in `anthropics/skills`' README; I could not confirm equivalent per-item popularity display on `microsoft.github.io/skills` or `awesome-copilot.github.com` item pages from what I accessed.

---

## 7. Full Citation List

| URL / Path | What it supports |
|---|---|
| `/Users/lkraak/Repos/ai-marketplace/GLOSSARY.md` | Terminology used throughout (Catalogue, External source, Extension, Manifest) |
| `/Users/lkraak/Repos/ai-marketplace/skills-lock.json` | Confirms this repo already installs `documentation-writer` from `github/awesome-copilot`, with a `computedHash` content-digest field |
| `https://raw.githubusercontent.com/vercel-labs/skills/main/README.md` | CLI install flow, telemetry/security-audit disable flags |
| `https://raw.githubusercontent.com/vercel-labs/skills/main/docs/creating-skills.md` | Skill discovery rules, plugin manifest discovery |
| `https://raw.githubusercontent.com/vercel-labs/skills/main/docs/commands.md` | Install source formats (branch/tag/tree URL pinning options) |
| `https://raw.githubusercontent.com/vercel-labs/skills/main/docs/troubleshooting.md` | Telemetry/security-audit opt-out env vars |
| `https://raw.githubusercontent.com/vercel-labs/skills/main/AGENTS.md` | Update-checking system, GitHub Trees API tree-SHA mechanism |
| `https://raw.githubusercontent.com/vercel-labs/skills/main/src/local-lock.ts` | `computedHash` = SHA-256 of on-disk skill folder content, not a commit SHA |
| `https://raw.githubusercontent.com/vercel-labs/skills/main/src/telemetry.ts` | `PartnerAudit`/`fetchAuditData()` definitions, `AUDIT_URL` endpoint |
| `https://raw.githubusercontent.com/vercel-labs/skills/main/src/add.ts` (lines ~120-200, 655-680, 2075-2100, 2395-2420) | Security Risk Assessment table rendering (ath/Socket/Snyk), advisory-only handling, audit keyed by repo+skill name not SHA |
| `https://www.skills.sh/` and `https://www.skills.sh/vercel-labs/agent-skills` and `.../web-design-guidelines` | Catalog pages; install counts (popularity); confirms no audit table shown on item page |
| `https://www.skills.sh/tele/audit?source=vercel-labs/agent-skills&skills=web-design-guidelines` | Live audit API query (ath/socket/snyk = safe/safe/low) |
| `https://www.skills.sh/tele/audit?source=microsoft/skills&skills=azure-ai-contentsafety-py` | Live cross-source audit query (safe/safe/low) |
| `https://www.skills.sh/tele/audit?source=github/awesome-copilot&skills=documentation-writer` | Live cross-source audit query (safe/safe/low) |
| `https://www.skills.sh/tele/audit?source=anthropics/skills&skills=docx` | Live cross-source audit query — **Socket: critical, 2 alerts**, divergent from Snyk (low) and ath (safe) |
| `https://api.github.com/repos/vercel-labs/skills/community/profile` | Health 50%; contributing/issue_template/pull_request_template all null |
| `https://api.github.com/repos/vercel-labs/agent-skills/community/profile` | Health 37%; same nulls |
| `https://raw.githubusercontent.com/microsoft/skills/main/README.md` | Install flow, CI badges, skill catalog table |
| `https://microsoft.github.io/skills/` | Skill Explorer catalog page (174 skills) |
| `https://microsoft.github.io/skills/llms.txt` | **Mismatch found**: content is generic Microsoft Foundry docs, not a skill index |
| `https://raw.githubusercontent.com/microsoft/skills/main/SECURITY.md` | Generic Microsoft-org vulnerability disclosure boilerplate |
| `https://raw.githubusercontent.com/microsoft/skills/main/.github/workflows/test-harness.yml` | Quality/eval smoke-test CI, explicitly not security |
| `https://raw.githubusercontent.com/microsoft/skills/main/.github/workflows/skill-evaluation.yml` | Nightly real-SDK quality evaluation, explicitly not security |
| `https://raw.githubusercontent.com/microsoft/skills/main/.github/CODEOWNERS` | Ownership model, per-skill/plugin owners, "security-sensitive" CI paths |
| `https://api.github.com/repos/microsoft/skills/community/profile` | Health 62%; contributing/issue_template null; CODE_OF_CONDUCT present (microsoft/.github org default) |
| `https://api.github.com/repos/microsoft/skills/contents/.github/skills/azure-ai-contentsafety-py` | Confirms symlink to `plugins/azure-sdk-python/skills/...` |
| `https://raw.githubusercontent.com/anthropics/skills/main/README.md` | Install flows (Claude Code plugin marketplace, Claude.ai, API); explicit "demonstration and educational purposes only" disclaimer |
| `https://raw.githubusercontent.com/anthropics/skills/main/skills/frontend-design/SKILL.md` | Representative item content; per-skill `LICENSE.txt` reference |
| `https://raw.githubusercontent.com/anthropics/skills/main/.claude-plugin/marketplace.json` | Plugin manifest; `source: "./"` with no ref/sha pin |
| `https://api.github.com/repos/anthropics/skills/community/profile` | Health 25%; all community-health fields null |
| `https://api.github.com/repos/anthropics/skills/contents` and `.../skills` and `.../spec` | Repo structure confirmation; no SECURITY.md/CONTRIBUTING.md present |
| `https://code.claude.com/docs/en/plugin-marketplaces` | Claude Code marketplace mechanics; no documented commit-pinning for marketplace installs |
| `https://raw.githubusercontent.com/github/awesome-copilot/main/README.md` | Install flow, `llms.txt` machine-readable index claim, links to CONTRIBUTING/SECURITY/CODE_OF_CONDUCT |
| `https://raw.githubusercontent.com/github/awesome-copilot/main/CONTRIBUTING.md` | Accept/reject criteria including explicit security-related exclusions; external-plugin review-workflow requirement |
| `https://raw.githubusercontent.com/github/awesome-copilot/main/SECURITY.md` | Generic GitHub-org vulnerability disclosure (opensource-security@github.com) |
| `https://raw.githubusercontent.com/github/awesome-copilot/main/CODEOWNERS` | Team-based ownership per content path |
| `https://raw.githubusercontent.com/github/awesome-copilot/main/docs/maintainers/review-routing.md` | Documented reviewer pools, SLAs, escalation policy |
| `https://raw.githubusercontent.com/github/awesome-copilot/main/.github/workflows/pr-risk-scan.yml` | PR-diff-scoped static risk scan gate; 1-day artifact retention; "soft-gate" labeling |
| `https://raw.githubusercontent.com/github/awesome-copilot/main/eng/pr-risk-scan.mjs` | Scanner rule definitions (guardrail-bypass language, remote-shell-pipe, auto-yes exec, unpinned versions) |
| `https://raw.githubusercontent.com/github/awesome-copilot/main/.github/workflows/skill-check.yml` | `@microsoft/vally-cli lint` PR gate for changed skills/agents |
| `https://raw.githubusercontent.com/github/awesome-copilot/main/.github/workflows/validate-skills.yml` | `npm run skill:validate` structural validation |
| `https://raw.githubusercontent.com/github/awesome-copilot/main/.github/ISSUE_TEMPLATE/external-plugin.yml` | Immutable-ref/SHA requirement for external plugin intake |
| `https://raw.githubusercontent.com/github/awesome-copilot/main/eng/external-plugin-quality-gates.mjs` | Clones/checks out the exact submitted SHA/ref before running gates |
| `https://raw.githubusercontent.com/github/awesome-copilot/main/eng/external-plugin-validation.mjs` | `publicSubmission` policy requiring immutable locator |
| `https://raw.githubusercontent.com/github/awesome-copilot/main/skills/documentation-writer/SKILL.md` | Representative item content (matches this repo's installed copy) |
| `https://awesome-copilot.github.com/llms.txt` | Confirmed live, structured machine-readable index; contains `documentation-writer` |
| `https://api.github.com/repos/github/awesome-copilot/community/profile` | Health 87%; contributing/pull_request_template/code_of_conduct all present |
| `https://awesome-copilot.github.com/skills/documentation-writer` | **Dead/unconfirmed link** — returned HTTP 404; correct item-detail URL pattern not determined |
| `https://api.github.com/repos/vercel-labs/skills/contents/.github` and sub-paths | Confirms no CONTRIBUTING.md/SECURITY.md present |

### Explicit dead/inaccessible links encountered
- `https://github.com/vercel-labs/skills/blob/main/CONTRIBUTING.md` → 404 (does not exist)
- `https://awesome-copilot.github.com/skills/documentation-writer` → 404 (item-detail URL pattern unconfirmed)
- `https://microsoft.github.io/skills/llms.txt` → 200 but content is unrelated Foundry docs, not a skill index (misleading rather than dead, flagged explicitly above)