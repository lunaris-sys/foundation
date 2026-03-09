#!/usr/bin/env bash
# build.sh - Convert README.md to PDF via LaTeX
#
# Usage:
#   ./build.sh                    # full build (renders Mermaid diagrams)
#   ./build.sh --skip-mermaid     # skip diagram rendering (faster)
#   ./build.sh --tex-only         # produce .tex without compiling PDF
#   ./build.sh --clean            # remove all build artifacts
#
# Output:
#   dist/documentation.pdf
#   dist/documentation.tex        (keep around for debugging)
#
# Requirements:
#   pandoc        - apt install pandoc
#   xelatex       - apt install texlive-xetex texlive-fonts-extra
#   python3       - apt install python3
#   mmdc          - npm install -g @mermaid-js/mermaid-cli  (optional)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_MD="${SCRIPT_DIR}/README.md"
TEMPLATE="${SCRIPT_DIR}/template.tex"
BUILD_DIR="${SCRIPT_DIR}/.build_tmp"
DIST_DIR="${SCRIPT_DIR}/dist"
DIAGRAM_DIR="${BUILD_DIR}/diagrams"

DOC_TITLE="Design & Architecture Documentation"
DOC_SUBTITLE="System Blueprint"
DOC_AUTHOR="Tim"
DOC_DATE="$(date '+%B %Y')"

SKIP_MERMAID=false
TEX_ONLY=false
CLEAN=false

for arg in "$@"; do
  case $arg in
    --skip-mermaid) SKIP_MERMAID=true ;;
    --tex-only)     TEX_ONLY=true ;;
    --clean)        CLEAN=true ;;
    --help)
      echo "Usage: ./build.sh [--skip-mermaid] [--tex-only] [--clean]"
      exit 0 ;;
  esac
done

if $CLEAN; then
  echo "Cleaning build artifacts..."
  rm -rf "${BUILD_DIR}" "${DIST_DIR}"
  echo "Done."
  exit 0
fi

# ── Dependency checks ─────────────────────────────────────────────────────────
check_dep() {
  command -v "$1" &>/dev/null || { echo "ERROR: '$1' not found. $2"; exit 1; }
}
check_dep pandoc  "sudo apt install pandoc"
check_dep xelatex "sudo apt install texlive-xetex texlive-fonts-extra"
check_dep python3 "sudo apt install python3"

if ! $SKIP_MERMAID && ! command -v mmdc &>/dev/null; then
  echo "WARNING: mmdc not found, falling back to --skip-mermaid"
  echo "         Install: npm install -g @mermaid-js/mermaid-cli"
  SKIP_MERMAID=true
fi

mkdir -p "${BUILD_DIR}" "${DIST_DIR}" "${DIAGRAM_DIR}"

echo "━━━ Building documentation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Input:  ${INPUT_MD}"
echo "  Output: ${DIST_DIR}/documentation.pdf"
echo ""

# ── Step 1: Normalize ─────────────────────────────────────────────────────────
echo "▶ 1/4  Normalizing markdown..."
python3 "${SCRIPT_DIR}/normalize_md.py" \
  "${INPUT_MD}" -o "${BUILD_DIR}/normalized.md"

# ── Step 2: Pre-process ───────────────────────────────────────────────────────
echo "▶ 2/4  Pre-processing for LaTeX..."
MERMAID_FLAG=""
$SKIP_MERMAID && MERMAID_FLAG="--skip-mermaid"

python3 "${SCRIPT_DIR}/preprocess_for_latex.py" \
  "${BUILD_DIR}/normalized.md" \
  "${BUILD_DIR}/preprocessed.md" \
  --diagram-dir "${DIAGRAM_DIR}" \
  $MERMAID_FLAG

# ── Step 3: Pandoc ────────────────────────────────────────────────────────────
echo "▶ 3/4  Running pandoc..."
pandoc \
  "${BUILD_DIR}/preprocessed.md" \
  "${SCRIPT_DIR}/metadata.yaml" \
  --from  "markdown+raw_tex+fenced_code_blocks+backtick_code_blocks" \
  --to    latex \
  --template "${TEMPLATE}" \
  --output "${DIST_DIR}/documentation.tex" \
  --standalone \
  --table-of-contents \
  --toc-depth=2 \
  --number-sections \
  --highlight-style breezedark \
  --resource-path "${BUILD_DIR}" \
  --metadata title="${DOC_TITLE}" \
  --metadata subtitle="${DOC_SUBTITLE}" \
  --metadata author="${DOC_AUTHOR}" \
  --metadata date="${DOC_DATE}" \
  2>&1 | { grep -v "^$" || true; }

echo "  Written: ${DIST_DIR}/documentation.tex"

$TEX_ONLY && { echo ""; echo "━━━ Done (--tex-only) ━━━━━━━━━━━━━━━━━━"; exit 0; }

# ── Step 4: Compile PDF ───────────────────────────────────────────────────────
echo "▶ 4/4  Compiling PDF (2 passes)..."

# Copy diagrams next to tex file for \includegraphics to find them
if [ -d "${DIAGRAM_DIR}" ] && [ -n "$(ls -A "${DIAGRAM_DIR}" 2>/dev/null)" ]; then
  cp -r "${DIAGRAM_DIR}" "${DIST_DIR}/diagrams"
fi

xelatex_pass() {
  local pass=$1
  echo "    Pass ${pass}/2..."
  # Run from DIST_DIR so relative paths like diagrams/foo.png resolve correctly
  (cd "${DIST_DIR}" && xelatex \
    -interaction=nonstopmode \
    documentation.tex) \
    > "${BUILD_DIR}/xelatex_pass${pass}.log" 2>&1 || true

  if ! grep -q "Output written on" "${BUILD_DIR}/xelatex_pass${pass}.log"; then
    echo ""
    echo "ERROR: xelatex produced no output on pass ${pass}."
    echo "Last 30 lines of log:"
    tail -30 "${BUILD_DIR}/xelatex_pass${pass}.log"
    exit 1
  fi

  # Show any actual errors (not just warnings)
  local errors
  errors=$(grep "^!" "${BUILD_DIR}/xelatex_pass${pass}.log" | sort -u | wc -l)
  if [ "$errors" -gt 0 ]; then
    echo "    Note: ${errors} LaTeX error(s) in log (PDF still produced)"
    echo "    See: ${BUILD_DIR}/xelatex_pass${pass}.log"
  fi
}

xelatex_pass 1
xelatex_pass 2

# Clean up aux files (keep .tex and .pdf)
for ext in aux log out toc; do
  rm -f "${DIST_DIR}/documentation.${ext}"
done

echo ""
echo "━━━ Done ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
SIZE=$(du -h "${DIST_DIR}/documentation.pdf" 2>/dev/null | cut -f1)
echo "  PDF:  ${DIST_DIR}/documentation.pdf  (${SIZE})"
