#!/usr/bin/env bash
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
set -euo pipefail

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

while (($#)); do
  case "$1" in
    --styles) STYLES="$2"; shift 2 ;;
    --format) FORMAT="$2"; shift 2 ;;
    --charset) CHARSET="$2"; shift 2 ;;
    --cjk-scale) CJK_SCALE="$2"; shift 2 ;;
    --split-web) SPLIT_WEB=(--split); shift ;;
    -h|--help) sed -n '2,17p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
case "$FORMAT" in otf|ttf) ;; *) echo "--format must be otf or ttf" >&2; exit 2 ;; esac
for style in $STYLES; do
  case "$style" in Regular|Bold|Italic|BoldItalic) ;; *) echo "unknown style: $style" >&2; exit 2 ;; esac
done

for tool in curl unzip "$PYTHON"; do
  command -v "$tool" >/dev/null || { echo "missing required tool: $tool" >&2; exit 1; }
done
"$PYTHON" -c 'import fontTools, brotli, uharfbuzz, unicodedata2, pathops' 2>/dev/null \
  || { echo "install python deps first: $PYTHON -m pip install -r requirements.txt" >&2; exit 1; }

step() { printf '\n==> %s\n' "$*"; }

step "fetch pinned sources"
"$ROOT/scripts/fetch-sources.sh"

step "audit glyph-set licences"
"$PYTHON" "$ROOT/scripts/audit-licenses.py"

rm -rf "$BUILD" "$DIST"
mkdir -p "$DIST"

build_style() { # build_style <Regular|Bold|Italic|BoldItalic>
  local style="$1" b="$BUILD/$1" stem="JimMonoTC-$1"
  local display="${style/BoldItalic/Bold Italic}"
  local weight="Regular"; [[ "$style" == Bold* ]] && weight="Bold"
  local cascadia="$CACHE/cascadia/CascadiaCodeNF-$style.ttf"
  local noto="$CACHE/downloads/NotoSansCJKtc-$weight-2.004.otf"
  local noto_arrows="$CACHE/downloads/NotoSansCJKtc-Black-2.004.otf"
  mkdir -p "$b"

  step "[$display] fit cell glyphs, complete the Nerd Font icons"
  "$PYTHON" "$ROOT/scripts/prepare-base.py" "$cascadia" "$b/base.ttf" --nerd-fonts "$CACHE/nerd-fonts"

  step "[$display] arrows from Noto Sans CJK TC Black"
  "$PYTHON" "$ROOT/scripts/add-arrows.py" "$b/base.ttf" "$noto_arrows" "$b/arrows.ttf"

  step "[$display] merge Noto Sans CJK TC $weight (charset: $CHARSET)"
  "$PYTHON" "$ROOT/scripts/merge-cjk.py" "$b/arrows.ttf" "$noto" "$b/merged.$FORMAT" \
    --charset "$CHARSET" --cjk-scale "$CJK_SCALE" --format "$FORMAT"

  step "[$display] finalize names and metrics"
  "$PYTHON" "$ROOT/scripts/finalize.py" "$b/merged.$FORMAT" "$DIST/$stem.$FORMAT" \
    --family "$FAMILY" --style "$display" --version "$FONT_VERSION" \
    --sources "Cascadia Code $CASCADIA_VERSION; Noto Sans CJK 2.004; Nerd Fonts $NERD_FONTS_VERSION"

  step "[$display] WOFF2 for the web"
  "$PYTHON" "$ROOT/scripts/build-web.py" "$DIST/$stem.$FORMAT" --out-dir "$DIST" ${SPLIT_WEB[@]+"${SPLIT_WEB[@]}"}
}

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
  "$PYTHON" "$ROOT/scripts/verify.py" "$DIST/$stem.$FORMAT"
  if ((${#SPLIT_WEB[@]})); then
    "$PYTHON" "$ROOT/scripts/verify.py" --partial --max-bytes 65536 "$DIST"/"$stem".*.woff2
  else
    "$PYTHON" "$ROOT/scripts/verify.py" "$DIST/$stem.woff2"
  fi
done

printf '\nDone:\n'
ls -lh "$DIST"/*."$FORMAT" "$DIST"/*.woff2 "$DIST"/JimMonoTC.css
