#!/bin/bash
# Build script for documentation pages
# Combines header + page content + footer into final HTML files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_DATE=$(date +%Y-%m-%d)

echo "Building documentation pages..."
echo "  Date: $CURRENT_DATE"

# Node.js is required for deterministic page assembly and the search index.
NODE_BIN=""
if command -v node &>/dev/null && node --version &>/dev/null 2>&1; then
    NODE_BIN="node"
elif command -v node.exe &>/dev/null && node.exe --version &>/dev/null 2>&1; then
    NODE_BIN="node.exe"
fi

if [ -n "$NODE_BIN" ]; then
    if [ "$NODE_BIN" = "node.exe" ] && command -v wslpath &>/dev/null; then
        $NODE_BIN "$(wslpath -w "$SCRIPT_DIR/build-pages.js")" "$(wslpath -w "$SCRIPT_DIR")"
    else
        $NODE_BIN "$SCRIPT_DIR/build-pages.js" "$SCRIPT_DIR"
    fi

    echo "Build complete! Generated files:"
    ls -la "$SCRIPT_DIR"/*.html 2>/dev/null || echo "  No HTML files generated"

    echo ""
    echo "Generating search index..."
    if [ "$NODE_BIN" = "node.exe" ] && command -v wslpath &>/dev/null; then
        # node.exe is a Windows binary; convert WSL paths to Windows paths
        $NODE_BIN "$(wslpath -w "$SCRIPT_DIR/generate-search-index.js")" "$(wslpath -w "$SCRIPT_DIR")"
    else
        $NODE_BIN "$SCRIPT_DIR/generate-search-index.js" "$SCRIPT_DIR"
    fi
else
    echo "ERROR: Node.js not found. Page assembly and search indexing require Node.js. Install Node.js (the Pages workflow uses node@24) and re-run docs/build.sh." >&2
    exit 1
fi
