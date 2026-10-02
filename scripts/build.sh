#!/usr/bin/env bash
# Copyright (C) 2026 Jim Chen <Jim@ChenJ.im>, licensed under GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ==================================================================
#
# Build Jim Mono TC (Regular, Bold, Italic, Bold Italic) from pinned upstream sources.
#
#   Cascadia Code NF ─► prepare-base ─► add-arrows ─► merge-cjk ─► finalize ─► verify
#                     (cell glyphs,    (Noto)        (Noto)                  └─► WOFF2 (build-web)
#                      Nerd icons)
#
# Default output is one OpenType/CFF font (.otf) per style with every East Asian wide code
# point Noto Sans CJK TC has (about 43k, 57.5k glyphs in total, under the 65,535 limit).
# Latin, ligatures, Powerline and Nerd Font symbols are Cascadia Code's (the "NF" build);
# Bold / Bold Italic use Noto Sans CJK TC Bold; Noto has no italic, so the CJK glyphs of
# Italic / Bold Italic are slanted by Cascadia Italic's angle.
#
# Requirements: python3 with the packages of requirements.txt, curl, unzip, git;
# hb-shape optional.
#
# Usage: scripts/build.sh [--styles "Regular Bold Italic BoldItalic"] [--format otf|ttf]
#                         [--charset all|big5-common|big5|FILE] [--cjk-scale N] [--split-web]
#
# Environment:
#   PYTHON        Python interpreter (default: python3)
#   CACHE_DIR     Cache directory (default: <repo root>/.cache)
#   FONT_VERSION  Version stamped into the fonts (default: 0.3.0)
set -euo pipefail

# --- Configuration -----------------------------------------------------------
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
CACHE="${CACHE_DIR:-$ROOT/.cache}"
BUILD="$ROOT/build"
DIST="$ROOT/dist"
# shellcheck source=../sources/versions.env
source "$ROOT/sources/versions.env"

FAMILY="Jim Mono TC"
STYLES="Regular Bold Italic BoldItalic"
FORMAT="otf"
FONT_VERSION="${FONT_VERSION:-0.3.0}"
CHARSET="all"
CJK_SCALE="1.0"
SPLIT_WEB=()

# --- Utility functions -------------------------------------------------------
RED='\033[0;31m'; YELLOW='\033[1;33m'; GRAY='\033[0;90m'; RESET='\033[0m'

info()  { printf '%s%s%s\n' "$GRAY"    "$*" >&2; }
warn()  { printf '%sWARNING: %s%s\n' "$YELLOW" "$*" >&2; }
error() { printf '%sERROR: %s%s\n'    "$RED"    "$*" >&2; }
die()   { error "$*"; exit 1; }

step() { printf '\n%s==> %s%s\n' "$GRAY" "$*" "$RESET"; }

usage() { # usage
  cat <<'EOF'
Usage: scripts/build.sh [OPTIONS]

  --styles "REGULAR..."   Styles to build (default: "Regular Bold Italic BoldItalic")
  --format otf|ttf        Output format (default: otf)
  --charset SPEC          CJK charset: all|big5-common|big5|FILE (default: all)
  --cjk-scale N           Scale factor for merged CJK glyphs (default: 1.0)
  --split-web             Split WOFF2 into unicode-range slices
  -h, --help              Show this help

Environment: PYTHON, CACHE_DIR, FONT_VERSION (see comments at the top of the script).
EOF
}

# --- Parameter handling ------------------------------------------------------
while (($#)); do
  case "$1" in
    --styles) [[ $# -ge 2 ]] || { error "--styles requires a value"; exit 2; }; STYLES="$2"; shift 2 ;;
    --format) [[ $# -ge 2 ]] || { error "--format requires a value"; exit 2; }; FORMAT="$2"; shift 2 ;;
    --charset) [[ $# -ge 2 ]] || { error "--charset requires a value"; exit 2; }; CHARSET="$2"; shift 2 ;;
    --cjk-scale) [[ $# -ge 2 ]] || { error "--cjk-scale requires a value"; exit 2; }; CJK_SCALE="$2"; shift 2 ;;
    --split-web) SPLIT_WEB=(--split); shift ;;
    -h|--help) usage; exit 0 ;;
    *) error "unknown option: $1"; usage >&2; exit 2 ;;
  esac
done
case "$FORMAT" in otf|ttf) ;; *) error "--format must be otf or ttf"; exit 2 ;; esac
for style in $STYLES; do
  case "$style" in Regular|Bold|Italic|BoldItalic) ;; *) error "unknown style: $style"; exit 2 ;; esac
done
[[ "$CJK_SCALE" =~ ^[0-9]+(\.[0-9]+)?$ ]] || die "--cjk-scale must be a positive number, got: $CJK_SCALE"

# Fail fast: validate every dependency before touching build outputs.
for tool in curl unzip "$PYTHON"; do
  command -v "$tool" >/dev/null 2>&1 \
    || die "required tool not installed: $tool"
done
"$PYTHON" -c 'import fontTools, brotli, uharfbuzz, unicodedata2, pathops' 2>/dev/null \
  || die "install python deps first: $PYTHON -m pip install -r requirements.txt"

# --- Content processing functions --------------------------------------------
build_style() { # build_style <Regular|Bold|Italic|BoldItalic>
  local style="$1" b="$BUILD/$1" stem="JimMonoTC-$1"
  local display="${style/BoldItalic/Bold Italic}"
  local weight="Regular"; [[ "$style" == Bold* ]] && weight="Bold"
  local cascadia="$CACHE/cascadia/CascadiaCodeNF-$style.ttf"
  local noto="$CACHE/downloads/NotoSansCJKtc-$weight-2.004.otf"
  local noto_arrows="$CACHE/downloads/NotoSansCJKtc-Black-2.004.otf"
  mkdir -p "$b"

  step "[$display] fit cell glyphs, complete the Nerd Font icons"
  "$PYTHON" "$ROOT/scripts/prepare-base.py" "$cascadia" "$b/base.ttf" --nerd-fonts "$CACHE/nerd-fonts" \
    || die "[$display] prepare-base failed"

  step "[$display] arrows from Noto Sans CJK TC Black"
  "$PYTHON" "$ROOT/scripts/add-arrows.py" "$b/base.ttf" "$noto_arrows" "$b/arrows.ttf" \
    || die "[$display] add-arrows failed"

  step "[$display] merge Noto Sans CJK TC $weight (charset: $CHARSET)"
  "$PYTHON" "$ROOT/scripts/merge-cjk.py" "$b/arrows.ttf" "$noto" "$b/merged.$FORMAT" \
    --charset "$CHARSET" --cjk-scale "$CJK_SCALE" --format "$FORMAT" \
    || die "[$display] merge-cjk failed"

  step "[$display] finalize names and metrics"
  "$PYTHON" "$ROOT/scripts/finalize.py" "$b/merged.$FORMAT" "$DIST/$stem.$FORMAT" \
    --family "$FAMILY" --style "$display" --version "$FONT_VERSION" \
    --sources "Cascadia Code $CASCADIA_VERSION; Noto Sans CJK 2.004; Nerd Fonts $NERD_FONTS_VERSION" \
    || die "[$display] finalize failed"

  step "[$display] WOFF2 for the web"
  "$PYTHON" "$ROOT/scripts/build-web.py" "$DIST/$stem.$FORMAT" --out-dir "$DIST" ${SPLIT_WEB[@]+"${SPLIT_WEB[@]}"} \
    || die "[$display] build-web failed"
}

# --- Main execution ----------------------------------------------------------
step "fetch pinned sources"
"$ROOT/scripts/fetch-sources.sh" || die "fetching sources failed"

step "audit glyph-set licences"
"$PYTHON" "$ROOT/scripts/audit-licenses.py" || die "licence audit failed"

rm -rf "$BUILD" "$DIST"
mkdir -p "$DIST"

for style in $STYLES; do
  build_style "$style"
done

# One stylesheet for every style built.
cat "$DIST"/JimMonoTC-*.css > "$DIST/JimMonoTC.css"

step "licences"
mkdir -p "$DIST/licenses/nerd-fonts"
cp "$ROOT/LICENSE" "$ROOT/licenses/CascadiaCode-LICENSE.txt" "$ROOT/NOTICE.md" "$DIST/licenses/"
for f in "$CACHE"/nerd-fonts/src/glyphs/*/LICEN[CS]E* "$CACHE"/nerd-fonts/src/glyphs/weather-icons/OFL.txt; do
  cp "$f" "$DIST/licenses/nerd-fonts/$(basename "$(dirname "$f")")-$(basename "$f")"
done
mkdir -p "$DIST/licenses/third-party"
cp "$ROOT"/licenses/third-party/* "$DIST/licenses/third-party/"

step "verify"
for style in $STYLES; do
  stem="JimMonoTC-$style"
  "$PYTHON" "$ROOT/scripts/verify.py" "$DIST/$stem.$FORMAT" \
    || die "verification failed for $stem.$FORMAT"
  if ((${#SPLIT_WEB[@]})); then
    "$PYTHON" "$ROOT/scripts/verify.py" --partial --max-bytes 65536 "$DIST"/"$stem".*.woff2 \
      || die "verification failed for $stem WOFF2 slices"
  else
    "$PYTHON" "$ROOT/scripts/verify.py" "$DIST/$stem.woff2" \
      || die "verification failed for $stem.woff2"
  fi
done

printf '\nDone:\n'
ls -lh "$DIST"/*."$FORMAT" "$DIST"/*.woff2 "$DIST"/JimMonoTC.css
