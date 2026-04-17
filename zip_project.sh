#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# CarbonKarma dMRV — Project ZIP Script
# Creates a clean distributable archive of the full backend.
# Usage:  bash zip_project.sh
#         bash zip_project.sh --output /tmp/carbonkarma_v2.zip
# ─────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT="${1:-}"
POSITIONAL_ARG="${2:-}"
ZIP_NAME="carbonkarma_backend_$(date +%Y%m%d_%H%M%S).zip"

# Allow --output flag
if [[ "$OUTPUT" == "--output" && -n "$POSITIONAL_ARG" ]]; then
    ZIP_PATH="$POSITIONAL_ARG"
else
    ZIP_PATH="$SCRIPT_DIR/../$ZIP_NAME"
fi

ZIP_PATH="$(realpath "$ZIP_PATH" 2>/dev/null || echo "$ZIP_PATH")"

echo "──────────────────────────────────────────────────"
echo "  CarbonKarma dMRV — Build Distribution Archive"
echo "  Output: $ZIP_PATH"
echo "──────────────────────────────────────────────────"

cd "$SCRIPT_DIR"

# Directories and files to include
INCLUDE=(
    "app.py"
    "requirements.txt"
    ".env.example"
    "README.md"
    "API_TESTING_GUIDE.md"
    "config/"
    "db/"
    "models/"
    "routes/"
    "services/"
    "utils/"
)

# Patterns to exclude
EXCLUDE=(
    "**/__pycache__/**"
    "**/*.pyc"
    "**/*.pyo"
    "**/.DS_Store"
    "**/Thumbs.db"
    "db/carbonkarma.db"     # exclude live DB — fresh install gets a new one
    "reports/"              # exclude generated reports
    "**/.env"               # never ship real .env
    "**/.venv/**"
    "**/node_modules/**"
)

# Build exclude flags for zip
EXCLUDE_FLAGS=()
for pat in "${EXCLUDE[@]}"; do
    EXCLUDE_FLAGS+=("--exclude=$pat")
done

# Remove existing archive if present
[[ -f "$ZIP_PATH" ]] && rm "$ZIP_PATH"

# Create archive
zip -r "$ZIP_PATH" \
    "${INCLUDE[@]}" \
    "${EXCLUDE_FLAGS[@]}" \
    2>/dev/null

echo ""
echo "✅ Archive created: $ZIP_PATH"
echo "   Size: $(du -sh "$ZIP_PATH" | cut -f1)"
echo ""
echo "── Contents ───────────────────────────────────────"
zip -sf "$ZIP_PATH" | head -60
echo ""
echo "── Quick Start ─────────────────────────────────────"
echo "  1. unzip carbonkarma_backend_*.zip -d carbonkarma"
echo "  2. cd carbonkarma"
echo "  3. cp .env.example .env  && nano .env"
echo "  4. pip install -r requirements.txt"
echo "  5. python app.py"
echo "  6. curl http://localhost:5000/health"
echo "────────────────────────────────────────────────────"
