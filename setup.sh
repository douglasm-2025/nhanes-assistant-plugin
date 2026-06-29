#!/usr/bin/env bash
# nhanes-assistant-plugin/setup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/nhanes_server"
VENV_DIR="$SERVER_DIR/venv"
TEMPLATES_DIR="$SERVER_DIR/templates"
TEMPLATE_PATH="$TEMPLATES_DIR/manuscript_template.docx"

echo "=== NHANES Plugin Setup ==="
echo "Plugin dir: $SCRIPT_DIR"

# ── Copy STROBE-nut checklist from project root if not present ──
if [ ! -f "$SCRIPT_DIR/STROBE-nut_checklist.docx" ]; then
  PARENT="$(dirname "$SCRIPT_DIR")"
  if [ -f "$PARENT/STROBE-nut_checklist.docx" ]; then
    cp "$PARENT/STROBE-nut_checklist.docx" "$SCRIPT_DIR/"
    echo "Copied STROBE-nut_checklist.docx from project root."
  else
    echo "WARNING: STROBE-nut_checklist.docx not found. config://strobe_nut will be empty."
  fi
fi

# ── Python venv ──
echo ""
echo "--- Python setup ---"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$SERVER_DIR/requirements.txt" --quiet
echo "Python packages installed."

# ── R check ──
echo ""
echo "--- R setup ---"
if ! command -v Rscript &>/dev/null; then
  echo "ERROR: Rscript not found. Install R from https://cran.r-project.org/ and re-run."
  exit 1
fi
Rscript --version

# ── macOS font-library guard ──
# flextable → gdtools needs freetype/fontconfig/harfbuzz/fribidi, and
# fontconfig.pc pulls in -lintl (gettext's keg-only libintl). Without
# gettext on the linker path, gdtools fails with "ld: library 'intl' not
# found". Install the libs via Homebrew and expose them for the R build.
if [[ "$(uname)" == "Darwin" ]] && command -v brew &>/dev/null; then
  echo "macOS detected — ensuring font system libraries via Homebrew..."
  brew list pkg-config &>/dev/null || brew install pkg-config
  for lib in freetype fontconfig harfbuzz fribidi gettext; do
    brew list "$lib" &>/dev/null || brew install "$lib"
  done
  BREW_PREFIX="$(brew --prefix)"
  export PKG_CONFIG_PATH="$BREW_PREFIX/lib/pkgconfig:$BREW_PREFIX/opt/freetype/lib/pkgconfig:$BREW_PREFIX/opt/fontconfig/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
  export LIBRARY_PATH="$BREW_PREFIX/opt/gettext/lib:$BREW_PREFIX/lib:${LIBRARY_PATH:-}"
fi

# ── R packages ──
echo "Installing R packages (5-10 min on first run)..."
Rscript --vanilla - <<'REOF'
pkgs <- c(
  "tidyverse", "survey", "srvyr", "nhanesA", "arrow",
  "svglite", "gt", "gtsummary", "ggtext",
  "officer", "flextable", "ragg",
  "ggthemes", "cowplot", "patchwork",
  "jsonlite", "png"
)
installed <- rownames(installed.packages())
to_install <- pkgs[!pkgs %in% installed]
if (length(to_install) > 0) {
  cat(sprintf("Installing %d packages: %s\n", length(to_install),
              paste(to_install, collapse=", ")))
  install.packages(to_install, repos="https://cran.rstudio.com/", quiet=TRUE)
}
missing <- pkgs[!sapply(pkgs, requireNamespace, quietly=TRUE)]
if (length(missing) > 0) {
  cat("WARNING: failed to install:", paste(missing, collapse=", "), "\n")
} else {
  cat("All R packages verified OK.\n")
}
REOF

# ── Word template ──
echo ""
echo "--- Generating Word template ---"
mkdir -p "$TEMPLATES_DIR"
TEMPLATE_PATH="$TEMPLATE_PATH" Rscript --vanilla "$SERVER_DIR/r_helpers/generate_template.R"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Start MCP server:"
echo "  $VENV_DIR/bin/python $SERVER_DIR/server.py"
echo ""
echo "Claude Code integration: see docs/mcp-setup.md"
