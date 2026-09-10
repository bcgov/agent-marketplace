.PHONY: setup validate validate-one marketplace generate test docs serve demo-analyze format lint verify

# One-time (or after pulling new deps): install the Python tooling declared in
# pyproject.toml into a uv-managed virtualenv. Running `uv run` also does this
# lazily, but `make setup` is the explicit version that pre-warms the env.
setup:
	uv sync

# Validate every skill profile against the spec.
validate:
	uv run python scripts/validate_skill.py --all

# Validate a single skill profile. Usage: make validate-one SKILL=skills/azure-networking/SKILL.md
validate-one:
	@test -n "$(SKILL)" || (echo 'Usage: make validate-one SKILL=skills/<name>/SKILL.md' >&2; exit 2)
	uv run python scripts/validate_skill.py $(SKILL)

# Validate metadata, package policy, and checked-in generated projections.
marketplace:
	uv run python scripts/marketplace.py validate

# Regenerate machine-readable and escaped website catalog projections.
generate:
	uv run python scripts/marketplace.py generate

# Run the validator unit tests.
test:
	uv run pytest -q

# Build the static site and client-side search index.
docs:
	bash docs/build.sh

# Preview the built site. The catalog page fetches assets/catalog.json and the
# search index, which browsers refuse to load from file:// URLs, so the site
# has to be served over HTTP to browse it. Run `make docs` first.
# Usage: make serve [PORT=8000]
PORT ?= 8000
serve:
	@echo "Serving docs/ at http://localhost:$(PORT)/ (Ctrl+C to stop)"
	@cd docs && uv run python -m http.server $(PORT)

# Run a safe submission-analysis demo. Usage: make demo-analyze FIXTURE=benign-submission
demo-analyze:
	@test -n "$(FIXTURE)" || (echo 'Usage: make demo-analyze FIXTURE=benign-submission|blocked-submission' >&2; exit 2)
	uv run python scripts/demo.py analyze-fixture $(FIXTURE)

# Auto-format all Python to the repo style (2-space indent, double quotes).
format:
	uv run ruff format .

# Lint all Python: style, imports, docstrings, and bug-prone patterns. Also
# lints the GitHub Actions workflow YAML (2-space indent enforced; see
# .yamllint at the repo root).
lint:
	uv run ruff check .
	uv run yamllint .github/workflows

# One launch gate: formatting, lint, tests, portable and marketplace
# validation, generated catalog drift, Getting Started contracts, and docs.
verify:
	uv run ruff format --check .
	uv run ruff check .
	uv run yamllint .github/workflows
	uv run pytest -q
	uv run python scripts/validate_skill.py --all
	uv run python scripts/marketplace.py validate
	bash docs/build.sh
