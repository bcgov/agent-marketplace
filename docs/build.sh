#!/bin/bash
# Build generated outputs locally or in an explicitly isolated directory.
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$TASK_ROOT"
uv run python scripts/build_site.py --output "${1:-$TASK_ROOT/docs}"
